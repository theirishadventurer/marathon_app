import uuid
from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import select

from app.auth import hash_password
from app.lib.workout_family import family_for_planned
from app.models.agent import AgentKind, AgentMessage, MessageRole
from app.models.athlete import Athlete
from app.models.plan import Cycle, Plan
from app.models.workout import PlannedWorkout, WorkoutStatus, WorkoutType
from app.services.proposal_apply import ProposalNotFound, apply_proposal


async def _seed_workout(db, athlete_id, workout_date=date(2026, 6, 1)) -> PlannedWorkout:
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
        name="Phase 1",
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
        description_md="6mi w/ tempo",
        intent_md="Tempo volume",
    )
    db.add(pw)
    await db.commit()
    await db.refresh(pw)
    return pw


async def _make_chat_proposal(db, athlete_id, workout_id, *, new_value="2026-06-02") -> str:
    """A chat-style proposal: no new_date; option_a edits move the given workout."""
    pid = str(uuid.uuid4())
    msg = AgentMessage(
        athlete_id=athlete_id,
        agent=AgentKind.user_chat,
        role=MessageRole.assistant,
        content_md="proposal",
        related_workout_id=workout_id,
        proposal_state_json={
            "proposal_id": pid,
            "summary": "s",
            "options": [
                {
                    "id": "option_a",
                    "label": "l",
                    "tradeoff": "t",
                    "rationale": "r",
                    "edits": [
                        {
                            "workout_id": str(workout_id),
                            "field": "scheduled_date",
                            "new_value": new_value,
                        }
                    ],
                }
            ],
            "state": "pending",
            "created_by": "user_chat",
        },
    )
    db.add(msg)
    await db.commit()
    return pid


async def test_apply_option_moves_owned_workout(db, athlete):
    pw = await _seed_workout(db, athlete.id, date(2026, 6, 3))
    pid = await _make_chat_proposal(db, athlete.id, pw.id)
    await apply_proposal(db, athlete.id, uuid.UUID(pid), "option_a")
    refreshed = (
        await db.execute(select(PlannedWorkout).where(PlannedWorkout.id == pw.id))
    ).scalar_one()
    assert refreshed.status == WorkoutStatus.moved
    assert refreshed.scheduled_date.isoformat() == "2026-06-02"


async def test_apply_rejects_foreign_workout_id(db, athlete):
    # Proposal references a workout owned by a DIFFERENT athlete (LLM-emitted bad ID).
    other = Athlete(
        id=uuid.uuid4(),
        name="Other Runner",
        email="other@marathon.dev",
        password_hash=hash_password("otherpass"),
    )
    db.add(other)
    await db.commit()
    foreign = await _seed_workout(db, other.id, date(2026, 6, 5))

    pid = await _make_chat_proposal(db, athlete.id, foreign.id)
    with pytest.raises(Exception) as exc:
        await apply_proposal(db, athlete.id, uuid.UUID(pid), "option_a")
    assert "not found or not owned" in str(exc.value).lower()

    refreshed = (
        await db.execute(select(PlannedWorkout).where(PlannedWorkout.id == foreign.id))
    ).scalar_one()
    assert refreshed.status != WorkoutStatus.moved


async def test_cancel_marks_discarded(db, athlete):
    pw = await _seed_workout(db, athlete.id, date(2026, 6, 3))
    pid = await _make_chat_proposal(db, athlete.id, pw.id)
    await apply_proposal(db, athlete.id, uuid.UUID(pid), "cancel")
    msg = (
        await db.execute(
            select(AgentMessage).where(
                AgentMessage.proposal_state_json["proposal_id"].as_string() == pid
            )
        )
    ).scalar_one()
    assert msg.proposal_state_json["state"] == "discarded"


async def test_unknown_proposal_raises_not_found(db, athlete):
    with pytest.raises(ProposalNotFound):
        await apply_proposal(db, athlete.id, uuid.uuid4(), "option_a")
