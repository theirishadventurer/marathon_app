from __future__ import annotations

import pytest
from sqlalchemy import select


@pytest.mark.asyncio
async def test_log_completed_happy_path_running(
    client,
    seeded_auth_headers,
    seeded_db,
):
    """Happy path: log a 5mi/50min easy run; verify CompletedWorkout +
    Reconciliation created and planned status flips to done."""
    from app.models.workout import (
        PlannedWorkout,
        WorkoutStatus,
        WorkoutType,
    )

    workout = (
        await seeded_db.execute(
            select(PlannedWorkout)
            .where(PlannedWorkout.type == WorkoutType.easy)
            .where(PlannedWorkout.status == WorkoutStatus.planned)
            .limit(1)
        )
    ).scalar_one()
    wid = str(workout.id)

    response = await client.post(
        f"/workouts/{wid}/log-completed",
        json={
            "distance_mi": 5.0,
            "duration_min": 50,
            "avg_pace_str": "10:45",
            "avg_hr": 142,
            "notes": "Felt good",
        },
        headers=seeded_auth_headers,
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert "planned" in body
    assert "completed" in body
    assert "reconciliation" in body
    assert body["planned"]["status"] == "done"
    assert body["completed"]["distance_m"] is not None
    # 5mi == 8046.72m
    assert abs(float(body["completed"]["distance_m"]) - 8046.72) < 1.0
    assert body["completed"]["duration_s"] == 3000  # 50 * 60
    # avg_pace 10:45/mi == 645 s/mi == 645/1.609344 ≈ 401 s/km
    assert abs(body["completed"]["avg_pace_s_per_km"] - 401) <= 1
    assert body["reconciliation"]["match_confidence"] is not None
    assert body["reconciliation"]["deviation_notes_md"] == "Felt good"


@pytest.mark.asyncio
async def test_log_completed_409_for_done(
    client,
    seeded_auth_headers,
    seeded_db,
):
    from app.models.workout import PlannedWorkout, WorkoutStatus

    workout = (await seeded_db.execute(select(PlannedWorkout).limit(1))).scalar_one()
    workout.status = WorkoutStatus.done
    await seeded_db.commit()
    response = await client.post(
        f"/workouts/{workout.id}/log-completed",
        json={"duration_min": 30},
        headers=seeded_auth_headers,
    )
    assert response.status_code == 409


@pytest.mark.asyncio
async def test_log_completed_409_for_skipped(
    client,
    seeded_auth_headers,
    seeded_db,
):
    from app.models.workout import PlannedWorkout, WorkoutStatus

    workout = (await seeded_db.execute(select(PlannedWorkout).limit(1))).scalar_one()
    workout.status = WorkoutStatus.skipped
    await seeded_db.commit()
    response = await client.post(
        f"/workouts/{workout.id}/log-completed",
        json={"duration_min": 30},
        headers=seeded_auth_headers,
    )
    assert response.status_code == 409


@pytest.mark.asyncio
async def test_log_completed_404_for_nonexistent(client, seeded_auth_headers):
    response = await client.post(
        "/workouts/00000000-0000-0000-0000-000000000000/log-completed",
        json={"duration_min": 30},
        headers=seeded_auth_headers,
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_log_completed_400_invalid_pace_format(
    client,
    seeded_auth_headers,
    seeded_db,
):
    from app.models.workout import PlannedWorkout, WorkoutStatus, WorkoutType

    workout = (
        await seeded_db.execute(
            select(PlannedWorkout)
            .where(PlannedWorkout.type == WorkoutType.easy)
            .where(PlannedWorkout.status == WorkoutStatus.planned)
            .limit(1)
        )
    ).scalar_one()
    response = await client.post(
        f"/workouts/{workout.id}/log-completed",
        json={"duration_min": 30, "distance_mi": 3.0, "avg_pace_str": "10.45"},  # wrong delim
        headers=seeded_auth_headers,
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_log_completed_strength_no_distance(
    client,
    seeded_auth_headers,
    seeded_db,
):
    """Strength workouts don't require distance; just duration."""
    from app.models.workout import PlannedWorkout, WorkoutStatus, WorkoutType

    workout = (
        await seeded_db.execute(
            select(PlannedWorkout)
            .where(PlannedWorkout.type == WorkoutType.strength_a)
            .where(PlannedWorkout.status == WorkoutStatus.planned)
            .limit(1)
        )
    ).scalar_one()
    response = await client.post(
        f"/workouts/{workout.id}/log-completed",
        json={"duration_min": 45},
        headers=seeded_auth_headers,
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["completed"]["distance_m"] is None
    assert body["completed"]["avg_pace_s_per_km"] is None


@pytest.mark.asyncio
async def test_log_completed_busts_plan_cache(
    client,
    seeded_auth_headers,
    seeded_db,
):
    """After log-completed, /plan/full reflects the new done status."""
    from app.models.workout import PlannedWorkout, WorkoutStatus, WorkoutType

    workout = (
        await seeded_db.execute(
            select(PlannedWorkout)
            .where(PlannedWorkout.type == WorkoutType.easy)
            .where(PlannedWorkout.status == WorkoutStatus.planned)
            .limit(1)
        )
    ).scalar_one()
    wid = str(workout.id)

    # Prime cache
    r1 = await client.get("/plan/full", headers=seeded_auth_headers)
    assert r1.status_code == 200

    # Log completion
    r2 = await client.post(
        f"/workouts/{wid}/log-completed",
        json={"duration_min": 50, "distance_mi": 5.0},
        headers=seeded_auth_headers,
    )
    assert r2.status_code == 200

    # Cache busted: /plan/full now reflects the new state
    r3 = await client.get("/plan/full", headers=seeded_auth_headers)
    assert r3.status_code == 200
