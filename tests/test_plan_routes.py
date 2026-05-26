from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_plan_today_requires_auth(seeded_client: AsyncClient):
    resp = await seeded_client.get("/plan/today")
    assert resp.status_code in (401, 403)


@pytest.mark.asyncio
async def test_plan_today_returns_shape(seeded_client: AsyncClient, seeded_auth_headers: dict):
    resp = await seeded_client.get("/plan/today", headers=seeded_auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert "date" in body
    assert isinstance(body["workouts"], list)
    # Brief is populated for the seeded fixture (today falls inside the plan).
    assert body["coach_brief"] is not None


@pytest.mark.asyncio
async def test_plan_today_populates_coach_brief(
    seeded_client: AsyncClient, seeded_auth_headers: dict
):
    response = await seeded_client.get(
        "/plan/today",
        headers=seeded_auth_headers,
    )
    assert response.status_code == 200
    body = response.json()
    # Brief should be populated (non-None) for the seeded fixture
    assert body["coach_brief"] is not None
    assert isinstance(body["coach_brief"], str)
    assert len(body["coach_brief"]) > 0
    assert len(body["coach_brief"]) <= 280


@pytest.mark.asyncio
async def test_plan_week_returns_7_days(seeded_client: AsyncClient, seeded_auth_headers: dict):
    resp = await seeded_client.get(
        "/plan/week", params={"date": "2026-10-19"}, headers=seeded_auth_headers
    )
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["days"]) == 7
    total_workouts = sum(len(d["workouts"]) for d in body["days"])
    assert total_workouts == 7


@pytest.mark.asyncio
async def test_plan_week_includes_actual_for_done_workouts(
    seeded_client: AsyncClient, seeded_auth_headers: dict, seeded_db,
):
    """When a planned workout has a matched CompletedWorkout via Reconciliation,
    /plan/week must include an `actual` payload (distance_mi, duration_s, started_at)
    so the WorkoutCard can display actuals instead of the original planned values.

    Before this fix: Week tab kept showing planned distance even after the
    workout was logged completed, while Program dashboard showed the actual.
    """
    from datetime import date as date_cls

    from sqlalchemy import select

    from app.models.workout import PlannedWorkout, WorkoutStatus, WorkoutType

    # Pick a planned easy run, log it completed at a deliberately different
    # distance than the plan to prove the actual is what comes back.
    workout = (
        await seeded_db.execute(
            select(PlannedWorkout)
            .where(PlannedWorkout.type == WorkoutType.easy)
            .where(PlannedWorkout.status == WorkoutStatus.planned)
            .order_by(PlannedWorkout.scheduled_date)
            .limit(1)
        )
    ).scalar_one()
    wid = str(workout.id)
    scheduled = workout.scheduled_date

    # Log completion with distance != planned, so we can tell apart in the assertion
    response = await seeded_client.post(
        f"/workouts/{wid}/log-completed",
        json={"distance_mi": 3.4, "duration_min": 32, "avg_pace_str": "9:25"},
        headers=seeded_auth_headers,
    )
    assert response.status_code == 200, response.text

    # Now GET /plan/week for the scheduled week
    monday = scheduled - __import__("datetime").timedelta(days=scheduled.weekday())
    resp = await seeded_client.get(
        "/plan/week",
        params={"date": monday.isoformat()},
        headers=seeded_auth_headers,
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    # Find the done workout in the response
    done_workouts = [
        w
        for d in body["days"]
        for w in d["workouts"]
        if w["id"] == wid
    ]
    assert len(done_workouts) == 1, f"Expected to find the logged workout, got {done_workouts}"
    w_out = done_workouts[0]
    assert w_out["status"] == "done"
    # The new field: actual payload populated from Reconciliation → CompletedWorkout
    assert "actual" in w_out, "PlannedWorkoutOut should include `actual` field"
    actual = w_out["actual"]
    assert actual is not None, "Done workouts should have non-null actual data"
    # distance_mi rounded from 3.4mi → ~5471m → back to ~3.4mi
    assert "distance_mi" in actual
    assert abs(float(actual["distance_mi"]) - 3.4) < 0.05
    assert actual["duration_s"] == 32 * 60
    # Planned-but-not-done workouts must have actual=None
    planned_workouts = [
        w
        for d in body["days"]
        for w in d["workouts"]
        if w["status"] == "planned"
    ]
    assert len(planned_workouts) > 0
    for pw in planned_workouts:
        assert pw.get("actual") is None, f"Planned workout {pw['id']} should have actual=None"
    _ = date_cls  # silence unused import — kept for clarity in body


@pytest.mark.asyncio
async def test_plan_current_returns_shape(seeded_client: AsyncClient, seeded_auth_headers: dict):
    resp = await seeded_client.get("/plan/current", headers=seeded_auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert "plan_name" in body
    assert "active_cycle" in body
