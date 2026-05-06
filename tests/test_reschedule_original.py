import datetime
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy import select

from app.models.workout import PlannedWorkout, WorkoutStatus, WorkoutType


@pytest.mark.asyncio
async def test_reschedule_original_creates_row_and_returns_proposal(
    client, athlete_token, seeded_db
):
    # First, edit a strength workout into a run so a snapshot exists.
    result = await seeded_db.execute(
        select(PlannedWorkout).where(PlannedWorkout.type == "strength_a").limit(1)
    )
    edited = result.scalar_one()
    wid = str(edited.id)

    await client.patch(
        f"/workouts/{wid}",
        json={"type": "easy", "distance_mi": 5},
        headers={"Authorization": f"Bearer {athlete_token}"},
    )

    fake_proposal = {
        "proposal_id": "11111111-1111-1111-1111-111111111111",
        "summary": "fake",
        "options": [],
        "created_by": "reschedule_original",
    }

    with patch(
        "app.routes.workouts.propose_rebalance",
        AsyncMock(return_value=fake_proposal),
    ):
        response = await client.post(
            f"/workouts/{wid}/reschedule-original",
            json={"new_date": (edited.scheduled_date + datetime.timedelta(days=2)).isoformat()},
            headers={"Authorization": f"Bearer {athlete_token}"},
        )

    assert response.status_code == 200, response.text
    body = response.json()
    new_id = body["new_workout_id"]
    assert body["proposal"]["summary"] == "fake"

    # New row exists with snapshot type
    new_row = (
        await seeded_db.execute(select(PlannedWorkout).where(PlannedWorkout.id == new_id))
    ).scalar_one()
    assert new_row.type == WorkoutType.strength_a
    assert new_row.status == WorkoutStatus.planned


@pytest.mark.asyncio
async def test_reschedule_original_400_when_no_snapshot(client, athlete_token, seeded_db):
    result = await seeded_db.execute(select(PlannedWorkout).limit(1))
    workout = result.scalar_one()
    response = await client.post(
        f"/workouts/{workout.id}/reschedule-original",
        json={"new_date": workout.scheduled_date.isoformat()},
        headers={"Authorization": f"Bearer {athlete_token}"},
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_reschedule_original_400_when_outside_cycle(client, athlete_token, seeded_db):
    result = await seeded_db.execute(
        select(PlannedWorkout).where(PlannedWorkout.type == "strength_a").limit(1)
    )
    workout = result.scalar_one()
    wid = str(workout.id)

    await client.patch(
        f"/workouts/{wid}",
        json={"type": "easy"},
        headers={"Authorization": f"Bearer {athlete_token}"},
    )

    response = await client.post(
        f"/workouts/{wid}/reschedule-original",
        json={"new_date": "2099-01-01"},
        headers={"Authorization": f"Bearer {athlete_token}"},
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_cancel_apply_move_deletes_reschedule_created_row(client, athlete_token, seeded_db):
    # Edit a strength workout to seed a snapshot
    result = await seeded_db.execute(
        select(PlannedWorkout).where(PlannedWorkout.type == "strength_a").limit(1)
    )
    edited = result.scalar_one()
    wid = str(edited.id)

    await client.patch(
        f"/workouts/{wid}",
        json={"type": "easy"},
        headers={"Authorization": f"Bearer {athlete_token}"},
    )

    fake_proposal = {
        "proposal_id": "22222222-2222-2222-2222-222222222222",
        "summary": "x",
        "options": [],
        "created_by": "reschedule_original",
    }
    with patch(
        "app.routes.workouts.propose_rebalance",
        AsyncMock(return_value=fake_proposal),
    ):
        r = await client.post(
            f"/workouts/{wid}/reschedule-original",
            json={"new_date": (edited.scheduled_date + datetime.timedelta(days=2)).isoformat()},
            headers={"Authorization": f"Bearer {athlete_token}"},
        )
    new_id = r.json()["new_workout_id"]

    # Now cancel apply-move on the new row
    cancel = await client.post(
        f"/workouts/{new_id}/apply-move",
        json={"proposal_id": "22222222-2222-2222-2222-222222222222", "choice": "cancel"},
        headers={"Authorization": f"Bearer {athlete_token}"},
    )
    assert cancel.status_code == 200

    # Row must be gone
    gone = (
        await seeded_db.execute(select(PlannedWorkout).where(PlannedWorkout.id == new_id))
    ).scalar_one_or_none()
    assert gone is None
