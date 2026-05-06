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


@pytest.mark.asyncio
async def test_patch_workout_changes_type_and_snapshots(client, athlete_token, seeded_db):
    # Pick the first planned strength workout
    result = await seeded_db.execute(
        select(PlannedWorkout).where(PlannedWorkout.type == "strength_a").limit(1)
    )
    workout = result.scalar_one()
    wid = str(workout.id)

    response = await client.patch(
        f"/workouts/{wid}",
        json={"type": "easy", "distance_mi": 5.0, "duration_min": 50, "title": "Easy run"},
        headers={"Authorization": f"Bearer {athlete_token}"},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["type"] == "easy"
    assert body["family"] == "running"
    assert body["distance_mi"] == "5.0"
    assert body["duration_min"] == 50
    assert body["title"] == "Easy run"
    snap = body["original_snapshot"]
    assert snap is not None
    assert snap["type"] == "strength_a"
    assert snap["family"] == "strength"


@pytest.mark.asyncio
async def test_patch_workout_404_for_nonexistent(client, athlete_token):
    response = await client.patch(
        "/workouts/00000000-0000-0000-0000-000000000000",
        json={"type": "easy"},
        headers={"Authorization": f"Bearer {athlete_token}"},
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_patch_workout_409_for_done(client, athlete_token, seeded_db):
    result = await seeded_db.execute(select(PlannedWorkout).limit(1))
    workout = result.scalar_one()
    workout.status = "done"
    await seeded_db.commit()
    response = await client.patch(
        f"/workouts/{workout.id}",
        json={"type": "easy"},
        headers={"Authorization": f"Bearer {athlete_token}"},
    )
    assert response.status_code == 409


@pytest.mark.asyncio
async def test_patch_workout_snapshot_preserved_on_second_edit(client, athlete_token, seeded_db):
    result = await seeded_db.execute(
        select(PlannedWorkout).where(PlannedWorkout.type == "strength_a").limit(1)
    )
    workout = result.scalar_one()
    wid = str(workout.id)

    # First edit: strength_a -> easy
    r1 = await client.patch(
        f"/workouts/{wid}",
        json={"type": "easy", "distance_mi": 5},
        headers={"Authorization": f"Bearer {athlete_token}"},
    )
    snap1 = r1.json()["original_snapshot"]

    # Second edit: easy -> tempo
    r2 = await client.patch(
        f"/workouts/{wid}",
        json={"type": "tempo"},
        headers={"Authorization": f"Bearer {athlete_token}"},
    )
    snap2 = r2.json()["original_snapshot"]

    # Snapshot must NOT have been overwritten — still strength_a
    assert snap1 == snap2
    assert snap2["type"] == "strength_a"
