"""Integration tests for POST /plan/start-date (reseed-mode endpoint)."""

from __future__ import annotations

from datetime import date, timedelta

import pytest
from sqlalchemy import select


def _today_str() -> str:
    return date.today().isoformat()


def _today() -> date:
    return date.today()


def _future(days: int = 1) -> date:
    return date.today() + timedelta(days=days)


def _future_str(days: int = 1) -> str:
    return _future(days).isoformat()


@pytest.mark.asyncio
async def test_start_date_dry_run_returns_impact_no_writes(
    seeded_client, seeded_auth_headers, seeded_db
):
    from app.models.workout import PlannedWorkout
    from app.seed.plan_parser import parse_plan

    rows_before = (await seeded_db.execute(select(PlannedWorkout))).scalars().all()
    n_before = len(rows_before)

    new_start = _today()
    new_start_str = new_start.isoformat()

    # Compute expected new_cycle1_weeks dynamically from the parser (same logic
    # as the service) so this assertion stays meaningful as real time advances.
    parsed = parse_plan("PLAN.md", cycle_one_start_date=new_start)
    new_c1 = parsed["cycles"][0]
    expected_weeks = len(sorted({w["week_number"] for w in new_c1["workouts"]}))

    response = await seeded_client.post(
        "/plan/start-date?dry_run=true",
        json={"new_start_date": new_start_str},
        headers=seeded_auth_headers,
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["dry_run"] is True
    assert "impact" in body
    assert body["impact"]["new_cycle1_start"] == new_start_str
    assert body["impact"]["new_cycle1_weeks"] == expected_weeks
    assert body["plan"] is None

    rows_after = (await seeded_db.execute(select(PlannedWorkout))).scalars().all()
    assert len(rows_after) == n_before


@pytest.mark.asyncio
async def test_start_date_apply_reseeds(seeded_client, seeded_auth_headers, seeded_db):
    from app.models.plan import Cycle, Plan
    from app.models.workout import PlannedWorkout

    new_start = _today()
    new_start_str = new_start.isoformat()

    response = await seeded_client.post(
        "/plan/start-date",
        json={"new_start_date": new_start_str},
        headers=seeded_auth_headers,
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["dry_run"] is False
    assert body["plan"] is not None
    assert body["plan"]["plan_name"]

    cycle1 = (
        await seeded_db.execute(select(Cycle).join(Plan).where(Cycle.sequence == 1).limit(1))
    ).scalar_one()
    assert cycle1.start_date.isoformat() == new_start_str

    has_new = (
        (
            await seeded_db.execute(
                select(PlannedWorkout).where(
                    PlannedWorkout.cycle_id == cycle1.id,
                    PlannedWorkout.scheduled_date == new_start,
                )
            )
        )
        .scalars()
        .first()
    )
    assert has_new is not None


@pytest.mark.asyncio
async def test_start_date_400_on_past_date(seeded_client, seeded_auth_headers):
    response = await seeded_client.post(
        "/plan/start-date",
        json={"new_start_date": "2020-01-01"},
        headers=seeded_auth_headers,
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_start_date_writes_plan_history(seeded_client, seeded_auth_headers, seeded_db):
    from app.models.plan_history import PlanHistory

    new_start = _today()
    new_start_str = new_start.isoformat()

    response = await seeded_client.post(
        "/plan/start-date",
        json={"new_start_date": new_start_str},
        headers=seeded_auth_headers,
    )
    assert response.status_code == 200, response.text

    history = (
        (
            await seeded_db.execute(
                select(PlanHistory).where(PlanHistory.action == "start_date_reseed")
            )
        )
        .scalars()
        .all()
    )
    assert len(history) >= 1
    payload = history[0].payload_json
    assert payload["new_start"] == new_start_str


@pytest.mark.asyncio
async def test_start_date_requires_auth(seeded_client):
    response = await seeded_client.post(
        "/plan/start-date",
        json={"new_start_date": _today_str()},
    )
    assert response.status_code in (401, 403)


@pytest.mark.asyncio
async def test_start_date_dry_run_false_explicit(seeded_client, seeded_auth_headers, seeded_db):
    """dry_run=false (explicit) still applies the reseed."""
    from app.models.plan import Plan

    new_start = _today()
    new_start_str = new_start.isoformat()

    response = await seeded_client.post(
        "/plan/start-date?dry_run=false",
        json={"new_start_date": new_start_str},
        headers=seeded_auth_headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["dry_run"] is False

    plan = (await seeded_db.execute(select(Plan))).scalar_one()
    assert plan.start_date == new_start


@pytest.mark.asyncio
async def test_start_date_invalidates_plan_cache(seeded_client, seeded_auth_headers):
    """After a successful reseed, GET /plan/current should reflect the new start date."""
    new_start = _today()
    new_start_str = new_start.isoformat()

    response = await seeded_client.post(
        "/plan/start-date",
        json={"new_start_date": new_start_str},
        headers=seeded_auth_headers,
    )
    assert response.status_code == 200

    current = await seeded_client.get("/plan/current", headers=seeded_auth_headers)
    assert current.status_code == 200
    body = current.json()
    if body["active_cycle"] is not None and body["active_cycle"]["sequence"] == 1:
        assert body["active_cycle"]["start_date"] == new_start_str
