import json
import uuid
from datetime import date, timedelta
from typing import Any

import anthropic
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import settings
from app.models.agent import AgentKind, AgentMessage, MessageRole
from app.models.plan import Cycle
from app.models.workout import CompletedWorkout, PlannedWorkout


def get_anthropic_client() -> anthropic.AsyncAnthropic:
    """Create an async Anthropic client. Separated for test mocking."""
    return anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)


COACH_SYSTEM_PROMPT = (
    "You are a marathon coach working with this athlete on a 12-month, three-marathon plan.\n"
    "When the athlete moves a workout, analyze the impact and propose 2 rebalance options.\n"
    "Consider: hard-day stacking, long run proximity to strength, "
    "plan philosophy (durability over peak fitness).\n"
    "Be specific about which workouts to adjust and why."
)

PROPOSE_REBALANCE_TOOL: dict[str, Any] = {
    "name": "propose_rebalance",
    "description": "Propose rebalance options after a workout move",
    "input_schema": {
        "type": "object",
        "required": ["summary", "options"],
        "properties": {
            "summary": {
                "type": "string",
                "description": "1-2 sentence impact assessment",
            },
            "options": {
                "type": "array",
                "items": {
                    "type": "object",
                    "required": ["id", "label", "tradeoff", "edits", "rationale"],
                    "properties": {
                        "id": {
                            "type": "string",
                            "enum": ["option_a", "option_b"],
                        },
                        "label": {"type": "string"},
                        "tradeoff": {"type": "string"},
                        "edits": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "required": ["workout_id", "field", "new_value"],
                                "properties": {
                                    "workout_id": {"type": "string"},
                                    "field": {
                                        "type": "string",
                                        "enum": ["scheduled_date", "status"],
                                    },
                                    "new_value": {"type": "string"},
                                },
                            },
                        },
                        "rationale": {"type": "string"},
                    },
                },
                "minItems": 2,
                "maxItems": 2,
            },
        },
    },
}


def _monday_of(d: date) -> date:
    """Return the Monday of the ISO week containing date d."""
    return d - timedelta(days=d.weekday())


def _serialize_workout(pw: PlannedWorkout) -> dict[str, Any]:
    return {
        "id": str(pw.id),
        "scheduled_date": pw.scheduled_date.isoformat(),
        "original_date": pw.original_date.isoformat(),
        "type": pw.type.value,
        "family": pw.family.value,
        "status": pw.status.value,
        "title": pw.title,
        "distance_mi": float(pw.distance_mi) if pw.distance_mi is not None else None,
        "duration_min": pw.duration_min,
        "intent_md": pw.intent_md,
    }


def _serialize_completed(cw: CompletedWorkout) -> dict[str, Any]:
    return {
        "id": str(cw.id),
        "activity_date": cw.activity_date.isoformat(),
        "activity_type": cw.activity_type,
        "family": cw.family.value,
        "duration_s": cw.duration_s,
        "distance_m": float(cw.distance_m) if cw.distance_m is not None else None,
        "avg_hr": cw.avg_hr,
    }


async def _build_adapter_context(
    db: AsyncSession,
    athlete_id: uuid.UUID,
    workout_id: uuid.UUID,
    new_date: date,
) -> dict[str, Any]:
    """Build focused context for the rebalance proposal."""
    # Load the workout being moved, with its cycle and plan
    workout_result = await db.execute(
        select(PlannedWorkout)
        .options(selectinload(PlannedWorkout.cycle).selectinload(Cycle.plan))
        .where(PlannedWorkout.id == workout_id)
    )
    workout = workout_result.scalar_one()
    cycle = workout.cycle
    plan = cycle.plan

    # Determine affected weeks (old week + new week)
    old_monday = _monday_of(workout.scheduled_date)
    new_monday = _monday_of(new_date)
    week_starts = {old_monday}
    if new_monday != old_monday:
        week_starts.add(new_monday)

    # Load all planned workouts in the affected week(s)
    week_conditions = []
    for monday in week_starts:
        sunday = monday + timedelta(days=6)
        week_conditions.append(
            (PlannedWorkout.scheduled_date >= monday) & (PlannedWorkout.scheduled_date <= sunday)
        )

    from sqlalchemy import or_

    week_query = (
        select(PlannedWorkout)
        .where(PlannedWorkout.cycle_id == cycle.id)
        .where(or_(*week_conditions))
        .order_by(PlannedWorkout.scheduled_date)
    )
    week_result = await db.execute(week_query)
    week_workouts = week_result.scalars().all()

    # Load recent completed workouts (last 7 days)
    seven_days_ago = new_date - timedelta(days=7)
    completed_result = await db.execute(
        select(CompletedWorkout)
        .where(CompletedWorkout.athlete_id == athlete_id)
        .where(CompletedWorkout.activity_date >= seven_days_ago)
        .order_by(CompletedWorkout.activity_date.desc())
    )
    recent_completed = completed_result.scalars().all()

    return {
        "moved_workout": _serialize_workout(workout),
        "new_date": new_date.isoformat(),
        "cycle": {
            "id": str(cycle.id),
            "name": cycle.name,
            "race_name": cycle.race_name,
            "race_date": cycle.race_date.isoformat(),
        },
        "plan_philosophy": plan.philosophy_md,
        "week_workouts": [_serialize_workout(w) for w in week_workouts],
        "recent_completed": [_serialize_completed(c) for c in recent_completed],
    }


async def propose_rebalance(
    db: AsyncSession,
    athlete_id: uuid.UUID,
    workout_id: uuid.UUID,
    new_date: date,
) -> dict[str, Any]:
    """Propose rebalance options when a workout is moved."""
    context = await _build_adapter_context(db, athlete_id, workout_id, new_date)

    # Build the user message
    moved = context["moved_workout"]
    user_message = (
        f"The athlete is moving their {moved['type']} workout "
        f'("{moved["title"]}") from {moved["scheduled_date"]} to {context["new_date"]}.\n\n'
        f"Plan philosophy: {context['plan_philosophy']}\n\n"
        f"Current week layout:\n"
        + json.dumps(context["week_workouts"], indent=2)
        + "\n\nRecent completed workouts:\n"
        + json.dumps(context["recent_completed"], indent=2)
        + "\n\nAnalyze the impact and propose two rebalance options."
    )

    client = get_anthropic_client()
    response = await client.messages.create(
        model="claude-sonnet-4-5-20250514",
        max_tokens=1024,
        system=COACH_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_message}],
        tools=[PROPOSE_REBALANCE_TOOL],
        tool_choice={"type": "tool", "name": "propose_rebalance"},
    )

    # Extract the tool_use block
    tool_block = next(b for b in response.content if b.type == "tool_use")
    result = tool_block.input

    summary = result["summary"]
    options = result["options"]
    proposal_id = str(uuid.uuid4())

    # Persist an AgentMessage
    agent_msg = AgentMessage(
        athlete_id=athlete_id,
        agent=AgentKind.plan_adapter,
        role=MessageRole.assistant,
        content_md=summary,
        context_snapshot_json=context,
        related_workout_id=workout_id,
        proposal_state_json={
            "proposal_id": proposal_id,
            "original_date": moved["scheduled_date"],
            "new_date": context["new_date"],
            "options": options,
            "state": "pending",
        },
    )
    db.add(agent_msg)
    await db.commit()

    return {
        "proposal_id": proposal_id,
        "summary": summary,
        "options": options,
    }
