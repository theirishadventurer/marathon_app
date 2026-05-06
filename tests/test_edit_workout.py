import pytest
from sqlalchemy import select

from app.models.workout import PlannedWorkout


@pytest.mark.asyncio
async def test_planned_workout_has_original_snapshot_column(seeded_db):
    """The planned_workouts table must have an original_snapshot_json column,
    nullable, defaulting to None on insert."""
    result = await seeded_db.execute(select(PlannedWorkout).limit(1))
    workout = result.scalar_one()
    assert hasattr(workout, "original_snapshot_json")
    assert workout.original_snapshot_json is None
