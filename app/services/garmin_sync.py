from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from pathlib import Path

from garminconnect import Garmin, GarminConnectAuthenticationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.lib.workout_family import family_for_garmin_activity_type
from app.models.garmin import GarminAuthState
from app.models.metrics import DailyMetric
from app.models.workout import CompletedWorkout

logger = logging.getLogger(__name__)

BASE_TOKEN_DIR = Path("./data/garmin_tokens")


class GarminLoginFailed(Exception):
    """Raised when Garmin login fails. Covers wrong-creds, rate-limit (429),
    network errors, and the silent-fail mode where garminconnect returns
    without setting client.garth (typical for HTTP 429 from datacenter IPs)."""


@dataclass
class SyncReport:
    synced_activities: int = 0
    synced_metrics: int = 0
    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "synced_activities": self.synced_activities,
            "synced_metrics": self.synced_metrics,
            "errors": self.errors,
        }


class GarminSyncService:
    def __init__(self, db: AsyncSession, athlete_id: str) -> None:
        self.db = db
        self.athlete_id = athlete_id
        self.token_dir = BASE_TOKEN_DIR / athlete_id
        self.client: Garmin | None = None

    # ------------------------------------------------------------------
    # Auth
    # ------------------------------------------------------------------

    async def reauth(self, email: str, password: str) -> None:
        """Authenticate with Garmin and persist tokens.

        Raises:
            GarminLoginFailed: wrong creds, 429 rate limit (common from
                datacenter IPs like Railway), network error, or the silent
                failure mode where ``client.login()`` returns without
                setting ``client.garth`` (observed on 429 in garminconnect
                0.2.x). The route handler converts this to a 502 with a
                user-readable message.
        """
        self.token_dir.mkdir(parents=True, exist_ok=True)
        token_path = self.token_dir / "tokens.json"

        client = Garmin(email=email, password=password)
        try:
            await asyncio.to_thread(client.login)
        except GarminConnectAuthenticationError as e:
            raise GarminLoginFailed(f"Garmin rejected credentials: {e}") from e
        except Exception as e:
            raise GarminLoginFailed(f"Garmin login error: {e}") from e

        # garminconnect silently returns without raising on HTTP 429
        # (datacenter IP rate limit). Detect by checking the .garth session.
        garth = getattr(client, "garth", None)
        if garth is None:
            raise GarminLoginFailed(
                "Garmin login appeared to succeed but no session was "
                "established (likely HTTP 429 — Garmin rate-limited the "
                "server IP). Datacenter IPs are frequently throttled. "
                "Long-term fix: Strava integration on backlog."
            )

        # Persist tokens
        tokens = await asyncio.to_thread(garth.dumps)
        token_path.write_text(tokens)

        self.client = client

        # Upsert GarminAuthState
        result = await self.db.execute(
            select(GarminAuthState).where(GarminAuthState.athlete_id == self.athlete_id)
        )
        state = result.scalar_one_or_none()
        if state is None:
            state = GarminAuthState(
                athlete_id=self.athlete_id,
                token_dir_path=str(self.token_dir),
                needs_reauth=False,
            )
            self.db.add(state)
        else:
            state.needs_reauth = False
            state.last_error = None
            state.last_error_at = None
            state.token_dir_path = str(self.token_dir)

        await self.db.commit()

    async def _get_client(self) -> Garmin | None:
        """Load a Garmin client from saved tokens, or return None."""
        if self.client is not None:
            return self.client

        token_path = self.token_dir / "tokens.json"
        if not token_path.exists():
            return None

        try:
            tokens = token_path.read_text()
            client = Garmin()
            await asyncio.to_thread(client.garth.loads, tokens)
            await asyncio.to_thread(client.login)
            self.client = client
            return client
        except GarminConnectAuthenticationError as exc:
            await self._mark_needs_reauth(str(exc))
            return None

    # ------------------------------------------------------------------
    # Sync activities
    # ------------------------------------------------------------------

    async def sync_activities(self, since_date: date) -> list[CompletedWorkout]:
        client = await self._get_client()
        if client is None:
            return []

        try:
            activities = await asyncio.to_thread(
                client.get_activities_by_date,
                since_date.isoformat(),
                date.today().isoformat(),
            )
        except GarminConnectAuthenticationError as exc:
            await self._mark_needs_reauth(str(exc))
            return []

        if not activities:
            return []

        # Get already-synced garmin_activity_ids
        garmin_ids = [a["activityId"] for a in activities]
        result = await self.db.execute(
            select(CompletedWorkout.garmin_activity_id).where(
                CompletedWorkout.garmin_activity_id.in_(garmin_ids)
            )
        )
        existing_ids = {row[0] for row in result.all()}

        new_workouts: list[CompletedWorkout] = []
        for act in activities:
            gid = act["activityId"]
            if gid in existing_ids:
                continue

            activity_type = act.get("activityType", {}).get("typeKey", "other")
            started = act.get("startTimeLocal") or act.get("startTimeGMT", "")

            workout = CompletedWorkout(
                athlete_id=self.athlete_id,
                garmin_activity_id=gid,
                activity_date=date.fromisoformat(started[:10]) if started else since_date,
                started_at=datetime.fromisoformat(started) if started else datetime.now(UTC),
                activity_type=activity_type,
                family=family_for_garmin_activity_type(activity_type),
                duration_s=int(act.get("duration", 0)),
                distance_m=Decimal(str(act["distance"])) if act.get("distance") else None,
                avg_hr=act.get("averageHR"),
                max_hr=act.get("maxHR"),
                avg_pace_s_per_km=None,
                elevation_gain_m=(
                    Decimal(str(act["elevationGain"])) if act.get("elevationGain") else None
                ),
                calories=act.get("calories"),
                raw_summary_json=act,
            )
            self.db.add(workout)
            new_workouts.append(workout)

        if new_workouts:
            await self.db.flush()

        return new_workouts

    # ------------------------------------------------------------------
    # Sync daily metrics
    # ------------------------------------------------------------------

    async def sync_daily_metrics(self, since_date: date) -> list[DailyMetric]:
        client = await self._get_client()
        if client is None:
            return []

        try:
            stats = await asyncio.to_thread(client.get_daily_stats, since_date.isoformat())
        except GarminConnectAuthenticationError as exc:
            await self._mark_needs_reauth(str(exc))
            return []
        except Exception as exc:
            logger.warning("Failed to fetch daily stats: %s", exc)
            return []

        if not stats:
            return []

        # Normalise: some API versions return a list, others a single dict
        if isinstance(stats, dict):
            stats = [stats]

        # Existing dates for this athlete
        result = await self.db.execute(
            select(DailyMetric.metric_date).where(
                DailyMetric.athlete_id == self.athlete_id,
                DailyMetric.metric_date >= since_date,
            )
        )
        existing_dates = {row[0] for row in result.all()}

        new_metrics: list[DailyMetric] = []
        for day in stats:
            cal_date_str = day.get("calendarDate")
            if not cal_date_str:
                continue
            metric_date = date.fromisoformat(cal_date_str)
            if metric_date in existing_dates:
                continue

            metric = DailyMetric(
                athlete_id=self.athlete_id,
                metric_date=metric_date,
                sleep_score=day.get("sleepScore"),
                sleep_duration_s=day.get("sleepDurationSeconds"),
                hrv_overnight_ms=(
                    Decimal(str(day["hrvOvernight"])) if day.get("hrvOvernight") else None
                ),
                resting_hr=day.get("restingHeartRate"),
                body_battery_high=day.get("bodyBatteryHighestValue"),
                body_battery_low=day.get("bodyBatteryLowestValue"),
                training_readiness=day.get("trainingReadiness"),
                training_status=day.get("trainingStatus"),
                raw_json=day,
            )
            self.db.add(metric)
            new_metrics.append(metric)

        if new_metrics:
            await self.db.flush()

        return new_metrics

    # ------------------------------------------------------------------
    # Sync all
    # ------------------------------------------------------------------

    async def sync_all(self, days_back: int = 7) -> SyncReport:
        report = SyncReport()
        since = date.today() - timedelta(days=days_back)

        try:
            activities = await self.sync_activities(since)
            report.synced_activities = len(activities)
        except Exception as exc:
            logger.exception("sync_activities error")
            report.errors.append(f"activities: {exc}")

        try:
            metrics = await self.sync_daily_metrics(since)
            report.synced_metrics = len(metrics)
        except Exception as exc:
            logger.exception("sync_daily_metrics error")
            report.errors.append(f"metrics: {exc}")

        # Update last_successful_sync
        result = await self.db.execute(
            select(GarminAuthState).where(GarminAuthState.athlete_id == self.athlete_id)
        )
        state = result.scalar_one_or_none()
        if state is not None:
            state.last_successful_sync = datetime.now(UTC)

        await self.db.commit()
        return report

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    async def _mark_needs_reauth(self, error: str) -> None:
        result = await self.db.execute(
            select(GarminAuthState).where(GarminAuthState.athlete_id == self.athlete_id)
        )
        state = result.scalar_one_or_none()
        if state is not None:
            state.needs_reauth = True
            state.last_error = error
            state.last_error_at = datetime.now(UTC)
            await self.db.commit()
