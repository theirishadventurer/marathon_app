from datetime import date

import pytest
from sqlalchemy import select

from app.models.workout import PlannedWorkout, WorkoutType
from app.schemas.edit import EditWorkoutRequest, RescheduleOriginalRequest
from app.schemas.plan import PlannedWorkoutOut


@pytest.mark.asyncio
async def test_planned_workout_has_original_snapshot_column(seeded_db):
    """The planned_workouts table must have an original_snapshot_json column,
    nullable, defaulting to None on insert."""
    result = await seeded_db.execute(select(PlannedWorkout).limit(1))
    workout = result.scalar_one()
    assert hasattr(workout, "original_snapshot_json")
    assert workout.original_snapshot_json is None


def test_planned_workout_out_has_original_snapshot_field():
    fields = PlannedWorkoutOut.model_fields
    assert "original_snapshot" in fields
    annot = fields["original_snapshot"].annotation
    assert "None" in str(annot) or annot is type(None) or "Optional" in str(annot)


def test_edit_request_accepts_partial_fields():
    req = EditWorkoutRequest(type=WorkoutType.easy)
    assert req.type == WorkoutType.easy
    assert req.distance_mi is None
    assert req.duration_min is None
    assert req.title is None


def test_edit_request_rejects_negative_distance():
    with pytest.raises(ValueError):
        EditWorkoutRequest(distance_mi=-1)


def test_reschedule_request_round_trips_date():
    req = RescheduleOriginalRequest(new_date=date(2026, 5, 8))
    assert req.new_date == date(2026, 5, 8)
