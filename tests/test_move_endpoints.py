import datetime
import uuid
from datetime import date
from decimal import Decimal
from unittest.mock import AsyncMock, patch

import pytest

from app.lib.workout_family import family_for_planned
from app.models.agent import AgentKind, AgentMessage, MessageRole
from app.models.plan import Cycle, Plan
from app.models.workout import PlannedWorkout, WorkoutStatus, WorkoutType


async def _seed_workout(db, athlete_id, workout_date=date(2026, 6, 1)):
    """Helper: create plan -> cycle -> planned workout."""
    plan = Plan(
        athlete_id=athlete_id,
        name="Test Plan",
        start_date=date(2026, 4, 13),
        end_date=date(2027, 4, 11),
        philosophy_md="Durability over peak fitness.",
    )
    db.add(plan)
    await db.flush()
    cycle = Cycle(
        plan_id=plan.id,
        name="Phase 1: MCM",
        sequence=1,
        race_name="Marine Corps Marathon",
        race_date=date(2026, 10, 25),
        start_date=date(2026, 4, 13),
        end_date=date(2026, 10, 25),
    )
    db.add(cycle)
    await db.flush()
    pw = PlannedWorkout(
        cycle_id=cycle.id,
        scheduled_date=workout_date,
        original_date=workout_date,
        week_number=8,
        type=WorkoutType.tempo,
        family=family_for_planned(WorkoutType.tempo),
        distance_mi=Decimal("6.0"),
        duration_min=60,
        title="Tempo Run - 6mi",
        description_md="6mi w/ 3 x 10min tempo",
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
        {
            "id": "option_a",
            "label": "Swap strength B",
            "tradeoff": "Keeps spacing",
            "edits": [],
            "rationale": "Better separation.",
        },
        {
            "id": "option_b",
            "label": "Lighten Thursday",
            "tradeoff": "Less volume",
            "edits": [],
            "rationale": "Reduce load.",
        },
    ],
}


@pytest.mark.asyncio
async def test_move_workout(client, db, athlete, auth_headers):
    pw = await _seed_workout(db, athlete.id, date(2026, 6, 3))
    with patch(
        "app.routes.workouts.propose_rebalance", new_callable=AsyncMock, return_value=MOCK_PROPOSAL
    ):
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


# ---------------------------------------------------------------------------
# apply-move helpers & tests
# ---------------------------------------------------------------------------


async def _create_proposal(db, athlete_id, workout, option_edits=None):
    """Create a proposal agent_message for testing."""
    proposal_id = uuid.uuid4()
    new_date = workout.scheduled_date + datetime.timedelta(days=1)
    msg = AgentMessage(
        athlete_id=athlete_id,
        agent=AgentKind.plan_adapter,
        role=MessageRole.assistant,
        content_md="Test proposal",
        related_workout_id=workout.id,
        proposal_state_json={
            "proposal_id": str(proposal_id),
            "original_date": workout.scheduled_date.isoformat(),
            "new_date": new_date.isoformat(),
            "options": [
                {
                    "id": "option_a",
                    "label": "Option A",
                    "tradeoff": "Tradeoff A",
                    "edits": option_edits or [],
                    "rationale": "Rationale A",
                },
                {
                    "id": "option_b",
                    "label": "Option B",
                    "tradeoff": "Tradeoff B",
                    "edits": [],
                    "rationale": "Rationale B",
                },
            ],
            "state": "pending",
        },
    )
    db.add(msg)
    await db.commit()
    return proposal_id


@pytest.mark.asyncio
async def test_apply_move_just_move(client, db, athlete, auth_headers):
    pw = await _seed_workout(db, athlete.id, date(2026, 6, 3))
    proposal_id = await _create_proposal(db, athlete.id, pw)

    resp = await client.post(
        f"/workouts/{pw.id}/apply-move",
        json={"proposal_id": str(proposal_id), "choice": "just_move"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["ok"] is True

    await db.refresh(pw)
    assert pw.scheduled_date == date(2026, 6, 4)
    assert pw.status == WorkoutStatus.moved
    assert pw.original_date == date(2026, 6, 3)


@pytest.mark.asyncio
async def test_apply_move_cancel(client, db, athlete, auth_headers):
    pw = await _seed_workout(db, athlete.id, date(2026, 6, 3))
    proposal_id = await _create_proposal(db, athlete.id, pw)

    resp = await client.post(
        f"/workouts/{pw.id}/apply-move",
        json={"proposal_id": str(proposal_id), "choice": "cancel"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["ok"] is True

    await db.refresh(pw)
    assert pw.scheduled_date == date(2026, 6, 3)
    assert pw.status == WorkoutStatus.planned


@pytest.mark.asyncio
async def test_apply_move_option_a_with_edits(client, db, athlete, auth_headers):
    pw1 = await _seed_workout(db, athlete.id, date(2026, 6, 3))
    pw2 = await _seed_workout(db, athlete.id, date(2026, 6, 5))

    option_edits = [
        {
            "workout_id": str(pw2.id),
            "field": "scheduled_date",
            "new_value": "2026-06-06",
        },
    ]
    proposal_id = await _create_proposal(db, athlete.id, pw1, option_edits=option_edits)

    resp = await client.post(
        f"/workouts/{pw1.id}/apply-move",
        json={"proposal_id": str(proposal_id), "choice": "option_a"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["ok"] is True

    await db.refresh(pw1)
    assert pw1.scheduled_date == date(2026, 6, 4)
    assert pw1.status == WorkoutStatus.moved

    await db.refresh(pw2)
    assert pw2.scheduled_date == date(2026, 6, 6)
    assert pw2.status == WorkoutStatus.moved


@pytest.mark.asyncio
async def test_apply_move_invalid_proposal(client, db, athlete, auth_headers):
    pw = await _seed_workout(db, athlete.id, date(2026, 6, 3))
    fake_proposal_id = uuid.uuid4()

    resp = await client.post(
        f"/workouts/{pw.id}/apply-move",
        json={"proposal_id": str(fake_proposal_id), "choice": "just_move"},
        headers=auth_headers,
    )
    assert resp.status_code == 404
