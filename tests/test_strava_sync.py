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
