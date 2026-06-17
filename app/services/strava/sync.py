from __future__ import annotations

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


def _parse_started_at(raw: str) -> datetime:
    # Strava ISO8601, may end in 'Z'
    return datetime.fromisoformat(raw.replace("Z", "+00:00"))


def map_activity(athlete_id: uuid.UUID, act: dict[str, Any]) -> CompletedWorkout:
    started_at = _parse_started_at(act["start_date_local"]).replace(tzinfo=None)
    sport = act.get("sport_type") or act.get("type") or "Run"

    avg_speed = act.get("average_speed") or 0
    avg_pace = round(1000 / avg_speed) if avg_speed and avg_speed > 0 else None

    has_hr = act.get("has_heartrate")
    avg_hr = round(act["average_heartrate"]) if has_hr and act.get("average_heartrate") else None
    max_hr = round(act["max_heartrate"]) if has_hr and act.get("max_heartrate") else None

    def _num(key: str) -> Decimal | None:
        v = act.get(key)
        return Decimal(str(v)) if v is not None else None

    return CompletedWorkout(
        athlete_id=athlete_id,
        strava_activity_id=int(act["id"]),
        source="strava",
        activity_date=started_at.date(),
        started_at=started_at,
        activity_type=str(sport),
        family=family_for_strava_sport_type(str(sport)),
        duration_s=int(act.get("moving_time", 0)),
        distance_m=_num("distance"),
        avg_hr=avg_hr,
        max_hr=max_hr,
        avg_pace_s_per_km=avg_pace,
        elevation_gain_m=_num("total_elevation_gain"),
        calories=int(act["calories"]) if act.get("calories") is not None else None,
        avg_cadence=_num("average_cadence"),
        avg_watts=_num("average_watts"),
        relative_effort=int(act["suffer_score"]) if act.get("suffer_score") is not None else None,
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
            resp = await client.refresh_token(
                client_id=settings.strava_client_id,
                client_secret=settings.strava_client_secret,
                refresh_token=state.refresh_token,
            )
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

        activities: list[dict] = []
        page = 1
        while True:
            batch = await client.get_activities(
                access_token=access, after_epoch=after_epoch, page=page, per_page=100
            )
            if not batch:
                break
            activities.extend(batch)
            if len(batch) < 100:
                break
            page += 1

        if not activities:
            state.last_successful_sync = datetime.now(UTC)
            await self.db.commit()
            return report

        ids = [int(a["id"]) for a in activities]
        existing = {
            row[0]
            for row in (
                await self.db.execute(
                    select(CompletedWorkout.strava_activity_id).where(
                        CompletedWorkout.strava_activity_id.in_(ids)
                    )
                )
            ).all()
        }

        for act in activities:
            if int(act["id"]) in existing:
                continue
            self.db.add(map_activity(self.athlete_id, act))
            report.synced_activities += 1

        state.last_successful_sync = datetime.now(UTC)
        await self.db.commit()
        return report
