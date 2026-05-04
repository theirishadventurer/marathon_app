import uuid
from datetime import date
from decimal import Decimal
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.lib.workout_family import family_for_planned
from app.models.plan import Cycle, Plan
from app.models.workout import PlannedWorkout, WorkoutStatus, WorkoutType


async def _seed_workout(db, athlete_id, workout_date=date(2026, 6, 1)):
    """Helper: create plan -> cycle -> planned workout."""
    plan = Plan(
        athlete_id=athlete_id, name="Test Plan",
        start_date=date(2026, 4, 13), end_date=date(2027, 4, 11),
        philosophy_md="Durability over peak fitness.",
    )
    db.add(plan)
    await db.flush()
    cycle = Cycle(
        plan_id=plan.id, name="Phase 1: MCM", sequence=1,
        race_name="Marine Corps Marathon", race_date=date(2026, 10, 25),
        start_date=date(2026, 4, 13), end_date=date(2026, 10, 25),
    )
    db.add(cycle)
    await db.flush()
    pw = PlannedWorkout(
        cycle_id=cycle.id, scheduled_date=workout_date, original_date=workout_date,
        week_number=8, type=WorkoutType.tempo, family=family_for_planned(WorkoutType.tempo),
        distance_mi=Decimal("6.0"), duration_min=60,
        title="Tempo Run - 6mi", description_md="6mi w/ 3 x 10min tempo",
        intent_md="Tempo volume",
    )
    db.add(pw)
    await db.commit()
    await db.refresh(pw)
    return pw


@pytest.mark.asyncio
async def test_skip_workout(client, db, athlete, auth_headers):
    pw = await _seed_workout(db, athlete.id)
    resp = await client.patch(f"/workouts/{pw.id}/skip", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["ok"] is True
    await db.refresh(pw)
    assert pw.status == WorkoutStatus.skipped


@pytest.mark.asyncio
async def test_skip_workout_not_found(client, athlete, auth_headers):
    fake_id = uuid.uuid4()
    resp = await client.patch(f"/workouts/{fake_id}/skip", headers=auth_headers)
    assert resp.status_code == 404


MOCK_PROPOSAL = {
    "proposal_id": "00000000-0000-0000-0000-000000000001",
    "summary": "Moving tempo to Thursday stacks with strength.",
    "options": [
        {"id": "option_a", "label": "Swap strength B", "tradeoff": "Keeps spacing", "edits": [], "rationale": "Better separation."},
        {"id": "option_b", "label": "Lighten Thursday", "tradeoff": "Less volume", "edits": [], "rationale": "Reduce load."},
    ],
}


@pytest.mark.asyncio
async def test_move_workout(client, db, athlete, auth_headers):
    pw = await _seed_workout(db, athlete.id, date(2026, 6, 3))
    with patch("app.routes.workouts.propose_rebalance", new_callable=AsyncMock, return_value=MOCK_PROPOSAL):
        resp = await client.patch(
            f"/workouts/{pw.id}/move",
            json={"new_date": "2026-06-04"},
            headers=auth_headers,
        )
    assert resp.status_code == 200
    data = resp.json()
    assert "proposal_id" in data
    assert data["summary"] == MOCK_PROPOSAL["summary"]
    assert len(data["options"]) == 2


@pytest.mark.asyncio
async def test_move_workout_not_found(client, athlete, auth_headers):
    fake_id = uuid.uuid4()
    resp = await client.patch(
        f"/workouts/{fake_id}/move",
        json={"new_date": "2026-06-04"},
        headers=auth_headers,
    )
    assert resp.status_code == 404
