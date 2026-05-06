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
