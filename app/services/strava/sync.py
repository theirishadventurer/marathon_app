from __future__ import annotations

import contextlib
import uuid
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.lib.workout_family import family_for_strava_sport_type
from app.models.strava import StravaAuthState
from app.models.workout import CompletedWorkout
from app.services.strava import oauth
from app.services.strava.client import get_strava_client

# Column limits (used for clamping to avoid overflow)
_MAX_SMALLINT = 32767
_MAX_CADENCE = Decimal("9999.9")
_MAX_WATTS = Decimal("99999.9")
_MAX_DISTANCE = Decimal("999999.99")  # Numeric(8,2)

# Minimum plausible speed to compute pace (0.3 m/s ≈ 55 min/km — basically stationary)
_MIN_SPEED_FOR_PACE = 0.3


class StravaSyncError(Exception):
    """Raised when the Strava sync cannot proceed (e.g. token refresh failure)."""


def _parse_started_at(raw: str) -> datetime:
    # Strava ISO8601, may end in 'Z'
    return datetime.fromisoformat(raw.replace("Z", "+00:00"))


def map_activity(athlete_id: uuid.UUID, act: dict[str, Any]) -> CompletedWorkout:
    started_at = _parse_started_at(act["start_date_local"]).replace(tzinfo=None)
    sport = act.get("sport_type") or act.get("type") or "Run"

    avg_speed = act.get("average_speed") or 0
    if avg_speed and avg_speed > _MIN_SPEED_FOR_PACE:
        raw_pace = round(1000 / avg_speed)
        avg_pace: int | None = raw_pace if raw_pace <= _MAX_SMALLINT else None
    else:
        avg_pace = None

    has_hr = act.get("has_heartrate")
    raw_avg_hr = (
        round(act["average_heartrate"]) if has_hr and act.get("average_heartrate") else None
    )
    avg_hr = raw_avg_hr if raw_avg_hr is None or raw_avg_hr <= _MAX_SMALLINT else None
    raw_max_hr = round(act["max_heartrate"]) if has_hr and act.get("max_heartrate") else None
    max_hr = raw_max_hr if raw_max_hr is None or raw_max_hr <= _MAX_SMALLINT else None

    def _num(key: str) -> Decimal | None:
        v = act.get(key)
        return Decimal(str(v)) if v is not None else None

    raw_cadence = _num("average_cadence")
    avg_cadence = raw_cadence if raw_cadence is None or raw_cadence <= _MAX_CADENCE else None

    raw_watts = _num("average_watts")
    avg_watts = raw_watts if raw_watts is None or raw_watts <= _MAX_WATTS else None

    raw_effort = int(act["suffer_score"]) if act.get("suffer_score") is not None else None
    relative_effort = raw_effort if raw_effort is None or raw_effort <= _MAX_SMALLINT else None

    raw_distance = _num("distance")
    distance_m = raw_distance if raw_distance is None or raw_distance <= _MAX_DISTANCE else None

    raw_calories = int(act["calories"]) if act.get("calories") is not None else None
    calories = raw_calories if raw_calories is None or raw_calories <= _MAX_SMALLINT else None

    return CompletedWorkout(
        athlete_id=athlete_id,
        strava_activity_id=int(act["id"]),
        source="strava",
        activity_date=started_at.date(),
        started_at=started_at,
        activity_type=str(sport),
        family=family_for_strava_sport_type(str(sport)),
        duration_s=int(act.get("moving_time", 0)),
        distance_m=distance_m,
        avg_hr=avg_hr,
        max_hr=max_hr,
        avg_pace_s_per_km=avg_pace,
        elevation_gain_m=_num("total_elevation_gain"),
        calories=calories,
        avg_cadence=avg_cadence,
        avg_watts=avg_watts,
        relative_effort=relative_effort,
        raw_summary_json=act,
    )


@dataclass
class StravaSyncReport:
    synced_activities: int = 0
    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {"synced_activities": self.synced_activities, "errors": self.errors}


class StravaSyncService:
    def __init__(self, db: AsyncSession, athlete_id: uuid.UUID) -> None:
        self.db = db
        self.athlete_id = athlete_id

    async def _state(self) -> StravaAuthState | None:
        return (
            await self.db.execute(
                select(StravaAuthState).where(StravaAuthState.athlete_id == self.athlete_id)
            )
        ).scalar_one_or_none()

    async def _ensure_fresh(self, state: StravaAuthState, client) -> str:
        """Return a valid access token, refreshing inline if near expiry."""
        if oauth.needs_refresh(state.expires_at, datetime.now(UTC)):
            try:
                resp = await client.refresh_token(
                    client_id=settings.strava_client_id,
                    client_secret=settings.strava_client_secret,
                    refresh_token=state.refresh_token,
                )
            except Exception as e:  # noqa: BLE001
                state.last_error = str(e)[:500]
                state.last_error_at = datetime.now(UTC)
                await self.db.commit()
                raise StravaSyncError(f"Token refresh failed: {e}") from e
            tokens = oauth.tokens_from_response(
                {**resp, "athlete": {"id": state.athlete_strava_id}}
            )
            state.access_token = tokens.access_token
            state.refresh_token = tokens.refresh_token
            state.expires_at = tokens.expires_at
            await self.db.commit()
        return state.access_token

    async def sync(self, since: date | None = None) -> StravaSyncReport:
        report = StravaSyncReport()
        state = await self._state()
        if state is None:
            return report  # not connected

        client = get_strava_client()
        access = await self._ensure_fresh(state, client)

        after_dt = state.last_successful_sync or (
            datetime.combine(since, datetime.min.time(), tzinfo=UTC)
            if since
            else datetime.now(UTC) - timedelta(days=30)
        )
        after_epoch = int(after_dt.timestamp())

        # H1/H2: seen set persists across pages; commit after each page.
        seen: set[int] = set()
        committed_any_page = False
        page = 1
        while True:
            batch = await client.get_activities(
                access_token=access, after_epoch=after_epoch, page=page, per_page=100
            )
            if not batch:
                break

            # Collect parseable ids for this page to check existing DB rows
            page_ids = []
            for a in batch:
                with contextlib.suppress(KeyError, TypeError, ValueError):
                    page_ids.append(int(a["id"]))

            if page_ids:
                existing = {
                    row[0]
                    for row in (
                        await self.db.execute(
                            select(CompletedWorkout.strava_activity_id).where(
                                CompletedWorkout.strava_activity_id.in_(page_ids)
                            )
                        )
                    ).all()
                }
                # Seed seen with DB-existing ids so H1 dedup works across pages too
                seen.update(existing)

            for act in batch:
                try:
                    act_id = int(act["id"])
                except (KeyError, TypeError, ValueError) as e:
                    report.errors.append(f"Activity missing id: {e}")
                    continue

                # H1: skip duplicates (both within-batch and already-in-DB)
                if act_id in seen:
                    continue

                try:
                    cw = map_activity(self.athlete_id, act)  # C1: may raise
                except Exception as e:  # noqa: BLE001
                    report.errors.append(f"Activity {act_id} skipped: {e}")
                    continue

                self.db.add(cw)
                seen.add(act_id)
                report.synced_activities += 1

            # H2: commit this page's rows before fetching next; advance sync cursor
            state.last_successful_sync = datetime.now(UTC)
            await self.db.commit()
            committed_any_page = True

            if len(batch) < 100:
                break
            page += 1

        # No non-empty page was fetched: still advance the sync cursor
        if not committed_any_page:
            state.last_successful_sync = datetime.now(UTC)
            await self.db.commit()

        return report
