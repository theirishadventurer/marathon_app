from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy import select

from app.lib.workout_family import family_for_planned
from app.models.agent import AgentMessage
from app.models.plan import Cycle, Plan
from app.models.workout import PlannedWorkout, WorkoutType


async def _seed_week(db, athlete_id):
    """Seed a full week of workouts."""
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

    workouts = []
    week = [
        (0, WorkoutType.easy, Decimal("4"), 35),
        (1, WorkoutType.strength_a, None, 60),
        (2, WorkoutType.tempo, Decimal("6"), 60),
        (3, WorkoutType.strength_b, None, 60),
        (4, WorkoutType.easy, Decimal("5"), 45),
        (5, WorkoutType.long, Decimal("14"), 182),
        (6, WorkoutType.rest, None, None),
    ]
    base = date(2026, 6, 1)  # Monday
    for offset, wtype, dist, dur in week:
        d = base + timedelta(days=offset)
        pw = PlannedWorkout(
            cycle_id=cycle.id,
            scheduled_date=d,
            original_date=d,
            week_number=8,
            type=wtype,
            family=family_for_planned(wtype),
            distance_mi=dist,
            duration_min=dur,
            title=f"{wtype.value} workout",
            description_md="desc",
            intent_md="intent",
        )
        db.add(pw)
        workouts.append(pw)
    await db.commit()
    for w in workouts:
        await db.refresh(w)
    return workouts


MOCK_TOOL_RESULT = {
    "summary": "Moving tempo from Wednesday to Thursday stacks it with strength B.",
    "options": [
        {
            "id": "option_a",
            "label": "Swap strength B to Wednesday",
            "tradeoff": "Keeps spacing",
            "edits": [],
            "rationale": "Maintains separation.",
        },
        {
            "id": "option_b",
            "label": "Drop strength B volume",
            "tradeoff": "Lighter Thursday",
            "edits": [],
            "rationale": "Reduces load.",
        },
    ],
}


@pytest.mark.asyncio
async def test_propose_rebalance(db, athlete):
    workouts = await _seed_week(db, athlete.id)
    tempo = workouts[2]  # Wednesday tempo
    new_date = date(2026, 6, 4)  # Thursday

    # Mock the Anthropic response
    mock_block = MagicMock()
    mock_block.type = "tool_use"
    mock_block.input = MOCK_TOOL_RESULT

    mock_response = MagicMock()
    mock_response.content = [mock_block]
    mock_response.usage.input_tokens = 100
    mock_response.usage.output_tokens = 200

    mock_client = MagicMock()
    mock_client.messages.create = AsyncMock(return_value=mock_response)

    with patch(
        "app.services.agents.plan_adapter.get_anthropic_client",
        return_value=mock_client,
    ):
        from app.services.agents.plan_adapter import propose_rebalance

        result = await propose_rebalance(db, athlete.id, tempo.id, new_date)

    assert "proposal_id" in result
    assert result["summary"] == MOCK_TOOL_RESULT["summary"]
    assert len(result["options"]) == 2

    # Verify persisted in agent_messages
    msg_result = await db.execute(
        select(AgentMessage).where(AgentMessage.related_workout_id == tempo.id)
    )
    msg = msg_result.scalar_one()
    assert msg.agent.value == "plan_adapter"
    assert msg.proposal_state_json is not None
    assert msg.proposal_state_json["state"] == "pending"


@pytest.mark.asyncio
async def test_propose_rebalance_context_snapshot(db, athlete):
    """Verify the context snapshot is persisted correctly."""
    workouts = await _seed_week(db, athlete.id)
    tempo = workouts[2]
    new_date = date(2026, 6, 4)

    mock_block = MagicMock()
    mock_block.type = "tool_use"
    mock_block.input = MOCK_TOOL_RESULT

    mock_response = MagicMock()
    mock_response.content = [mock_block]
    mock_response.usage.input_tokens = 100
    mock_response.usage.output_tokens = 200

    mock_client = MagicMock()
    mock_client.messages.create = AsyncMock(return_value=mock_response)

    with patch(
        "app.services.agents.plan_adapter.get_anthropic_client",
        return_value=mock_client,
    ):
        from app.services.agents.plan_adapter import propose_rebalance

        await propose_rebalance(db, athlete.id, tempo.id, new_date)

    msg_result = await db.execute(
        select(AgentMessage).where(AgentMessage.related_workout_id == tempo.id)
    )
    msg = msg_result.scalar_one()
    ctx = msg.context_snapshot_json
    assert ctx is not None
    assert ctx["new_date"] == "2026-06-04"
    assert ctx["plan_philosophy"] == "Durability over peak fitness."
    assert len(ctx["week_workouts"]) == 7  # full week seeded


@pytest.mark.asyncio
async def test_propose_rebalance_calls_anthropic_correctly(db, athlete):
    """Verify the Anthropic API is called with correct parameters."""
    workouts = await _seed_week(db, athlete.id)
    tempo = workouts[2]
    new_date = date(2026, 6, 4)

    mock_block = MagicMock()
    mock_block.type = "tool_use"
    mock_block.input = MOCK_TOOL_RESULT

    mock_response = MagicMock()
    mock_response.content = [mock_block]
    mock_response.usage.input_tokens = 100
    mock_response.usage.output_tokens = 200

    mock_client = MagicMock()
    mock_client.messages.create = AsyncMock(return_value=mock_response)

    with patch(
        "app.services.agents.plan_adapter.get_anthropic_client",
        return_value=mock_client,
    ):
        from app.services.agents.plan_adapter import propose_rebalance

        await propose_rebalance(db, athlete.id, tempo.id, new_date)

    call_kwargs = mock_client.messages.create.call_args.kwargs
    assert call_kwargs["model"] == "claude-sonnet-4-5-20250514"
    assert call_kwargs["tool_choice"] == {"type": "tool", "name": "propose_rebalance"}
    assert len(call_kwargs["tools"]) == 1
    assert call_kwargs["tools"][0]["name"] == "propose_rebalance"
    assert "tempo" in call_kwargs["messages"][0]["content"].lower()
