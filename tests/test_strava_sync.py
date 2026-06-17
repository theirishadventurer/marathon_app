import uuid
from datetime import date, datetime
from decimal import Decimal

from app.models.workout import CompletedWorkout, WorkoutFamily


async def test_completed_workout_accepts_strava_columns(db, athlete):
    cw = CompletedWorkout(
        athlete_id=athlete.id,
        strava_activity_id=123456789,
        source="strava",
        activity_date=date(2026, 6, 15),
        started_at=datetime(2026, 6, 15, 7, 0, 0),
        activity_type="Run",
        family=WorkoutFamily.running,
        duration_s=1800,
        distance_m=Decimal("5000.00"),
        avg_cadence=Decimal("172.0"),
        avg_watts=Decimal("260.0"),
        relative_effort=42,
        raw_summary_json={"id": 123456789},
    )
    db.add(cw)
    await db.flush()
    assert cw.strava_activity_id == 123456789
    assert cw.source == "strava"
    assert cw.relative_effort == 42


from app.services.strava.client import StravaClient, get_strava_client


def test_get_strava_client_returns_client():
    c = get_strava_client()
    assert isinstance(c, StravaClient)


from app.services.strava.sync import map_activity

SAMPLE = {
    "id": 111222333,
    "sport_type": "Run",
    "type": "Run",
    "distance": 5012.3,
    "moving_time": 1500,
    "elapsed_time": 1560,
    "total_elevation_gain": 42.0,
    "start_date_local": "2026-06-15T07:00:00Z",
    "average_speed": 3.34,
    "has_heartrate": True,
    "average_heartrate": 152.4,
    "max_heartrate": 171.0,
    "average_cadence": 86.0,
    "average_watts": 255.0,
    "suffer_score": 58,
    "calories": 410,
}


def test_map_activity_basic():
    athlete_id = uuid.uuid4()
    cw = map_activity(athlete_id, SAMPLE)
    assert cw.strava_activity_id == 111222333
    assert cw.source == "strava"
    assert cw.family == WorkoutFamily.running
    assert cw.duration_s == 1500
    assert float(cw.distance_m) == 5012.3
    assert cw.avg_hr == 152  # rounded
    assert cw.max_hr == 171
    assert cw.relative_effort == 58
    assert cw.activity_date.isoformat() == "2026-06-15"
    assert cw.avg_pace_s_per_km == round(1000 / 3.34)


def test_map_activity_zero_speed_pace_none():
    athlete_id = uuid.uuid4()
    act = {**SAMPLE, "average_speed": 0, "has_heartrate": False}
    cw = map_activity(athlete_id, act)
    assert cw.avg_pace_s_per_km is None
    assert cw.avg_hr is None


from datetime import UTC, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from sqlalchemy import func, select

from app.models.reconciliation import Reconciliation
from app.models.strava import StravaAuthState
from app.services.strava import sync as sync_mod


async def _connect(db, athlete):
    db.add(
        StravaAuthState(
            athlete_id=athlete.id,
            access_token="acc",
            refresh_token="ref",
            expires_at=datetime.now(UTC) + timedelta(hours=5),
            athlete_strava_id=1,
            scope="activity:read_all",
        )
    )
    await db.commit()


async def test_sync_ingests_and_dedups_without_reconcile(db, athlete):
    await _connect(db, athlete)
    fake = MagicMock()
    fake.get_activities = AsyncMock(side_effect=[[SAMPLE], []])  # one page then empty

    with patch.object(sync_mod, "get_strava_client", return_value=fake):
        svc = sync_mod.StravaSyncService(db, athlete.id)
        report = await svc.sync()

    assert report.synced_activities == 1
    count = (
        await db.execute(
            select(func.count()).select_from(CompletedWorkout).where(
                CompletedWorkout.athlete_id == athlete.id
            )
        )
    ).scalar_one()
    assert count == 1
    recon_count = (
        await db.execute(select(func.count()).select_from(Reconciliation))
    ).scalar_one()
    assert recon_count == 0  # ingest-only: no reconciliation, nothing marked done

    fake.get_activities = AsyncMock(side_effect=[[SAMPLE], []])
    with patch.object(sync_mod, "get_strava_client", return_value=fake):
        report2 = await sync_mod.StravaSyncService(db, athlete.id).sync()
    assert report2.synced_activities == 0  # dedup
