# Session 2A: Backend — Move Endpoints + Plan Adapter Agent

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add workout move/skip endpoints and the real Plan Adapter AI agent so the mobile app can drag-to-move workouts and receive AI-proposed rebalance options.

**Architecture:** Three new endpoints on the existing FastAPI backend. The Plan Adapter agent calls Anthropic's API (Claude Sonnet) with structured tool use to propose 2 rebalance options when a workout is moved. Proposals are persisted in `agent_messages` with `proposal_state_json`. Apply-move commits edits atomically. All existing tests must continue to pass.

**Tech Stack:** FastAPI, Anthropic Python SDK (tool use), Pydantic v2, SQLAlchemy 2.0 async, pytest

---

## File Structure

```
app/
├── schemas/
│   └── move.py                  # NEW: MoveRequest, ApplyMoveRequest, AdapterOption, ProposalOut
├── routes/
│   └── workouts.py              # MODIFY: add move, apply-move, skip endpoints
├── services/
│   └── agents/
│       └── plan_adapter.py      # MODIFY: replace stub with real Anthropic call
scripts/
└── export_openapi.sh            # NEW: exports OpenAPI spec to mobile/openapi.json
tests/
├── test_move_endpoints.py       # NEW: move, apply-move, skip, validation tests
└── test_plan_adapter.py         # NEW: adapter unit tests with mocked Anthropic
```

---

## Task 1: Skip Endpoint

**Files:**
- Modify: `app/routes/workouts.py`
- Test: `tests/test_move_endpoints.py`

- [ ] **Step 1: Write failing test**

Create `tests/test_move_endpoints.py`:

```python
import uuid
from datetime import date
from decimal import Decimal

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.lib.workout_family import family_for_planned
from app.models.plan import Cycle, Plan
from app.models.workout import PlannedWorkout, WorkoutStatus, WorkoutType


async def _seed_workout(
    db: AsyncSession, athlete_id: uuid.UUID, workout_date: date = date(2026, 6, 1)
) -> PlannedWorkout:
    """Create a plan -> cycle -> workout for testing."""
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
async def test_skip_workout(client: AsyncClient, db: AsyncSession, athlete, auth_headers):
    pw = await _seed_workout(db, athlete.id)
    resp = await client.patch(f"/workouts/{pw.id}/skip", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["ok"] is True

    await db.refresh(pw)
    assert pw.status == WorkoutStatus.skipped


@pytest.mark.asyncio
async def test_skip_workout_not_found(client: AsyncClient, athlete, auth_headers):
    fake_id = uuid.uuid4()
    resp = await client.patch(f"/workouts/{fake_id}/skip", headers=auth_headers)
    assert resp.status_code == 404
```

- [ ] **Step 2: Run test to verify it fails**

```bash
docker compose -f "C:/Coding Projects/marathon_app/docker-compose.yml" exec api pytest tests/test_move_endpoints.py::test_skip_workout -v
```
Expected: FAIL — no route for PATCH /workouts/{id}/skip

- [ ] **Step 3: Implement skip endpoint**

Add to `app/routes/workouts.py`:

```python
@router.patch("/{workout_id}/skip")
async def skip_workout(
    workout_id: uuid.UUID,
    athlete: Athlete = Depends(get_current_athlete),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(PlannedWorkout)
        .join(Cycle)
        .join(Plan)
        .where(PlannedWorkout.id == workout_id, Plan.athlete_id == athlete.id)
    )
    pw = result.scalar_one_or_none()
    if pw is None:
        raise HTTPException(status_code=404, detail="Workout not found")
    pw.status = WorkoutStatus.skipped
    await db.commit()
    return {"ok": True}
```

Add missing imports to workouts.py: `WorkoutStatus`, `Cycle`, `Plan`.

- [ ] **Step 4: Run tests**

```bash
docker compose -f "C:/Coding Projects/marathon_app/docker-compose.yml" exec api pytest tests/test_move_endpoints.py -v
```
Expected: both skip tests PASS

- [ ] **Step 5: Commit**

```bash
git add app/routes/workouts.py tests/test_move_endpoints.py
git commit -m "feat: PATCH /workouts/{id}/skip endpoint with tests"
```

---

## Task 2: Move Schemas

**Files:**
- Create: `app/schemas/move.py`

- [ ] **Step 1: Create Pydantic schemas for the move flow**

Create `app/schemas/move.py`:

```python
from datetime import date
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class MoveRequest(BaseModel):
    new_date: date


class WorkoutEdit(BaseModel):
    workout_id: UUID
    field: str  # "scheduled_date" or "status"
    new_value: str


class AdapterOption(BaseModel):
    id: str  # "option_a" or "option_b"
    label: str
    tradeoff: str
    edits: list[WorkoutEdit]
    rationale: str


class ProposalOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    proposal_id: UUID
    summary: str
    options: list[AdapterOption]


class ApplyMoveRequest(BaseModel):
    proposal_id: UUID
    choice: str  # "option_a", "option_b", "just_move", "cancel"
```

- [ ] **Step 2: Commit**

```bash
git add app/schemas/move.py
git commit -m "feat: Pydantic schemas for move/apply-move flow"
```

---

## Task 3: Plan Adapter Agent (Anthropic API)

**Files:**
- Modify: `app/services/agents/plan_adapter.py`
- Create: `tests/test_plan_adapter.py`

- [ ] **Step 1: Write failing test with mocked Anthropic**

Create `tests/test_plan_adapter.py`:

```python
import uuid
from datetime import date
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.lib.workout_family import family_for_planned
from app.models.agent import AgentMessage
from app.models.plan import Cycle, Plan
from app.models.workout import PlannedWorkout, WorkoutType


async def _seed_week(db: AsyncSession, athlete_id: uuid.UUID) -> list[PlannedWorkout]:
    """Seed a full week of workouts for adapter testing."""
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
    week_template = [
        (0, WorkoutType.easy, Decimal("4"), 35, "Easy run"),
        (1, WorkoutType.strength_a, None, 60, "Strength A"),
        (2, WorkoutType.tempo, Decimal("6"), 60, "Tempo run"),
        (3, WorkoutType.strength_b, None, 60, "Strength B"),
        (4, WorkoutType.easy, Decimal("5"), 45, "Easy run"),
        (5, WorkoutType.long, Decimal("14"), 182, "Long run"),
        (6, WorkoutType.rest, None, None, "Rest day"),
    ]
    base = date(2026, 6, 1)  # a Monday
    for offset, wtype, dist, dur, desc in week_template:
        d = base + __import__("datetime").timedelta(days=offset)
        pw = PlannedWorkout(
            cycle_id=cycle.id,
            scheduled_date=d,
            original_date=d,
            week_number=8,
            type=wtype,
            family=family_for_planned(wtype),
            distance_mi=dist,
            duration_min=dur,
            title=desc,
            description_md=desc,
            intent_md=f"Intent for {desc}",
        )
        db.add(pw)
        workouts.append(pw)

    await db.commit()
    for w in workouts:
        await db.refresh(w)
    return workouts


# Mock Anthropic response that returns a tool use with propose_rebalance
MOCK_TOOL_USE_RESPONSE = {
    "summary": "Moving tempo from Wednesday to Thursday stacks it with strength B.",
    "options": [
        {
            "id": "option_a",
            "label": "Swap strength B to Wednesday",
            "tradeoff": "Keeps hard days separated",
            "edits": [],  # will be populated dynamically in test
            "rationale": "Maintains the spacing between quality sessions.",
        },
        {
            "id": "option_b",
            "label": "Drop strength B volume",
            "tradeoff": "Lighter Thursday allows tempo",
            "edits": [],
            "rationale": "Reduces Thursday load to accommodate the tempo move.",
        },
    ],
}


@pytest.mark.asyncio
async def test_propose_rebalance_calls_anthropic(db: AsyncSession, athlete):
    workouts = await _seed_week(db, athlete.id)
    tempo_workout = workouts[2]  # Wednesday tempo
    new_date = date(2026, 6, 4)  # Thursday

    # Build mock Anthropic response
    mock_tool_block = MagicMock()
    mock_tool_block.type = "tool_use"
    mock_tool_block.input = MOCK_TOOL_USE_RESPONSE

    mock_response = MagicMock()
    mock_response.content = [mock_tool_block]
    mock_response.usage.input_tokens = 100
    mock_response.usage.output_tokens = 200

    mock_client = MagicMock()
    mock_client.messages.create = AsyncMock(return_value=mock_response)

    with patch("app.services.agents.plan_adapter.get_anthropic_client", return_value=mock_client):
        from app.services.agents.plan_adapter import propose_rebalance

        result = await propose_rebalance(db, athlete.id, tempo_workout.id, new_date)

    assert "proposal_id" in result
    assert result["summary"] == MOCK_TOOL_USE_RESPONSE["summary"]
    assert len(result["options"]) == 2
    assert result["options"][0]["id"] == "option_a"

    # Verify agent_messages row was persisted
    from sqlalchemy import select

    msg_result = await db.execute(
        select(AgentMessage).where(AgentMessage.related_workout_id == tempo_workout.id)
    )
    msg = msg_result.scalar_one()
    assert msg.agent.value == "plan_adapter"
    assert msg.proposal_state_json is not None
```

- [ ] **Step 2: Run test to verify it fails**

```bash
docker compose -f "C:/Coding Projects/marathon_app/docker-compose.yml" exec api pytest tests/test_plan_adapter.py -v
```
Expected: FAIL — NotImplementedError from stub

- [ ] **Step 3: Implement Plan Adapter agent**

Replace `app/services/agents/plan_adapter.py`:

```python
"""Plan Adapter agent — proposes rebalance options when a workout is moved."""

import json
import logging
import uuid
from datetime import date, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.agent import AgentKind, AgentMessage, MessageRole
from app.models.plan import Cycle, Plan
from app.models.workout import CompletedWorkout, PlannedWorkout

logger = logging.getLogger(__name__)

COACH_SYSTEM_PROMPT = """You are a marathon coach who has been working with this athlete on their \
specific 12-month, three-marathon plan. You know their plan philosophy, \
their injury history, and their goal: sub-5:00 finishes, healthy, enjoyed.

When the athlete moves a workout, analyze the impact and propose 2 rebalance options. \
Consider:
- Hard-day stacking (quality run + strength within 24h is a warning)
- Long run proximity to strength_a (same/next day is risky)
- The plan philosophy: durability over peak fitness
- Keep the weekly training balance intact when possible

Be specific about which workouts to adjust and why."""

PROPOSE_REBALANCE_TOOL = {
    "name": "propose_rebalance",
    "description": "Propose rebalance options after a workout move",
    "input_schema": {
        "type": "object",
        "required": ["summary", "options"],
        "properties": {
            "summary": {
                "type": "string",
                "description": "1-2 sentence read on the move and its impact",
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
                        "label": {"type": "string", "description": "Short name"},
                        "tradeoff": {
                            "type": "string",
                            "description": "What this prioritizes",
                        },
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


def get_anthropic_client():
    """Create Anthropic client. Separated for easy mocking in tests."""
    import anthropic

    return anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)


async def _build_adapter_context(
    db: AsyncSession,
    athlete_id: uuid.UUID,
    workout_id: uuid.UUID,
    new_date: date,
) -> dict[str, Any]:
    """Build focused context for the Plan Adapter."""
    # Load the workout being moved
    result = await db.execute(
        select(PlannedWorkout).where(PlannedWorkout.id == workout_id)
    )
    workout = result.scalar_one()

    # Load the cycle
    result = await db.execute(select(Cycle).where(Cycle.id == workout.cycle_id))
    cycle = result.scalar_one()

    # Load the plan for philosophy
    result = await db.execute(select(Plan).where(Plan.id == cycle.plan_id))
    plan = result.scalar_one()

    # Load all workouts in the affected week(s)
    old_week_start = workout.scheduled_date - timedelta(days=workout.scheduled_date.weekday())
    new_week_start = new_date - timedelta(days=new_date.weekday())
    earliest = min(old_week_start, new_week_start)
    latest = max(old_week_start, new_week_start) + timedelta(days=6)

    result = await db.execute(
        select(PlannedWorkout).where(
            PlannedWorkout.cycle_id == cycle.id,
            PlannedWorkout.scheduled_date >= earliest,
            PlannedWorkout.scheduled_date <= latest,
        )
    )
    week_workouts = result.scalars().all()

    # Recent completed workouts
    result = await db.execute(
        select(CompletedWorkout)
        .where(
            CompletedWorkout.athlete_id == athlete_id,
            CompletedWorkout.activity_date >= date.today() - timedelta(days=7),
        )
        .order_by(CompletedWorkout.activity_date.desc())
    )
    recent_completed = result.scalars().all()

    def _workout_dict(pw: PlannedWorkout) -> dict:
        return {
            "id": str(pw.id),
            "date": pw.scheduled_date.isoformat(),
            "original_date": pw.original_date.isoformat(),
            "type": pw.type.value,
            "family": pw.family.value,
            "status": pw.status.value,
            "title": pw.title,
            "distance_mi": str(pw.distance_mi) if pw.distance_mi else None,
            "duration_min": pw.duration_min,
            "description": pw.description_md,
        }

    return {
        "workout": _workout_dict(workout),
        "proposed_new_date": new_date.isoformat(),
        "week_workouts": [_workout_dict(w) for w in week_workouts],
        "cycle_info": {
            "name": cycle.name,
            "race_date": cycle.race_date.isoformat(),
            "race_name": cycle.race_name,
            "week_number": workout.week_number,
        },
        "plan_philosophy": plan.philosophy_md,
        "recent_completed": [
            {
                "date": c.activity_date.isoformat(),
                "type": c.activity_type,
                "distance_m": str(c.distance_m) if c.distance_m else None,
                "duration_s": c.duration_s,
            }
            for c in recent_completed
        ],
    }


async def propose_rebalance(
    db: AsyncSession,
    athlete_id: uuid.UUID,
    workout_id: uuid.UUID,
    new_date: date,
) -> dict[str, Any]:
    """Call Anthropic to propose rebalance options for a workout move.

    Returns dict with proposal_id, summary, and options.
    Persists the proposal in agent_messages.
    """
    context = await _build_adapter_context(db, athlete_id, workout_id, new_date)

    user_message = (
        f"The athlete wants to move this workout:\n"
        f"  {context['workout']['title']} ({context['workout']['type']})\n"
        f"  From: {context['workout']['date']}\n"
        f"  To: {context['proposed_new_date']}\n\n"
        f"Current week layout:\n"
    )
    for w in sorted(context["week_workouts"], key=lambda x: x["date"]):
        user_message += f"  {w['date']} | {w['type']:12s} | {w['title']}\n"

    user_message += (
        f"\nCycle: {context['cycle_info']['name']}, "
        f"Week {context['cycle_info']['week_number']}, "
        f"Race: {context['cycle_info']['race_date']}\n\n"
        f"Propose 2 rebalance options using the propose_rebalance tool."
    )

    client = get_anthropic_client()
    response = await client.messages.create(
        model="claude-sonnet-4-5-20250514",
        max_tokens=1500,
        system=COACH_SYSTEM_PROMPT + "\n\nPlan philosophy:\n" + context["plan_philosophy"],
        messages=[{"role": "user", "content": user_message}],
        tools=[PROPOSE_REBALANCE_TOOL],
        tool_choice={"type": "tool", "name": "propose_rebalance"},
    )

    # Extract tool use result
    tool_result = None
    for block in response.content:
        if block.type == "tool_use":
            tool_result = block.input
            break

    if tool_result is None:
        raise RuntimeError("Plan Adapter did not return a tool use response")

    # Persist as agent_message
    proposal_id = uuid.uuid4()
    msg = AgentMessage(
        athlete_id=athlete_id,
        agent=AgentKind.plan_adapter,
        role=MessageRole.assistant,
        content_md=tool_result["summary"],
        context_snapshot_json=context,
        related_workout_id=workout_id,
        proposal_state_json={
            "proposal_id": str(proposal_id),
            "original_date": context["workout"]["date"],
            "new_date": context["proposed_new_date"],
            "options": tool_result["options"],
            "state": "pending",
        },
    )
    db.add(msg)
    await db.commit()

    return {
        "proposal_id": proposal_id,
        "summary": tool_result["summary"],
        "options": tool_result["options"],
    }
```

- [ ] **Step 4: Run tests**

```bash
docker compose -f "C:/Coding Projects/marathon_app/docker-compose.yml" exec api pytest tests/test_plan_adapter.py -v
```
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add app/services/agents/plan_adapter.py tests/test_plan_adapter.py
git commit -m "feat: Plan Adapter agent with Anthropic tool use"
```

---

## Task 4: Move Endpoint

**Files:**
- Modify: `app/routes/workouts.py`
- Test: `tests/test_move_endpoints.py`

- [ ] **Step 1: Add failing test for move endpoint**

Append to `tests/test_move_endpoints.py`:

```python
from unittest.mock import AsyncMock, MagicMock, patch


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
async def test_move_workout(client: AsyncClient, db: AsyncSession, athlete, auth_headers):
    pw = await _seed_workout(db, athlete.id, date(2026, 6, 3))  # Wednesday

    with patch(
        "app.routes.workouts.propose_rebalance",
        new_callable=AsyncMock,
        return_value=MOCK_PROPOSAL,
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
async def test_move_workout_not_found(client: AsyncClient, athlete, auth_headers):
    fake_id = uuid.uuid4()
    resp = await client.patch(
        f"/workouts/{fake_id}/move",
        json={"new_date": "2026-06-04"},
        headers=auth_headers,
    )
    assert resp.status_code == 404
```

- [ ] **Step 2: Run to verify failure**

```bash
docker compose -f "C:/Coding Projects/marathon_app/docker-compose.yml" exec api pytest tests/test_move_endpoints.py::test_move_workout -v
```

- [ ] **Step 3: Implement move endpoint**

Add to `app/routes/workouts.py`:

```python
from app.schemas.move import MoveRequest, ProposalOut
from app.services.agents.plan_adapter import propose_rebalance


@router.patch("/{workout_id}/move", response_model=ProposalOut)
async def move_workout(
    workout_id: uuid.UUID,
    body: MoveRequest,
    athlete: Athlete = Depends(get_current_athlete),
    db: AsyncSession = Depends(get_db),
):
    # Verify workout exists and belongs to athlete
    result = await db.execute(
        select(PlannedWorkout)
        .join(Cycle)
        .join(Plan)
        .where(PlannedWorkout.id == workout_id, Plan.athlete_id == athlete.id)
    )
    pw = result.scalar_one_or_none()
    if pw is None:
        raise HTTPException(status_code=404, detail="Workout not found")

    proposal = await propose_rebalance(db, athlete.id, workout_id, body.new_date)
    return ProposalOut(
        proposal_id=proposal["proposal_id"],
        summary=proposal["summary"],
        options=proposal["options"],
    )
```

- [ ] **Step 4: Run tests**

```bash
docker compose -f "C:/Coding Projects/marathon_app/docker-compose.yml" exec api pytest tests/test_move_endpoints.py -v
```

- [ ] **Step 5: Commit**

```bash
git add app/routes/workouts.py tests/test_move_endpoints.py
git commit -m "feat: PATCH /workouts/{id}/move calls Plan Adapter"
```

---

## Task 5: Apply-Move Endpoint

**Files:**
- Modify: `app/routes/workouts.py`
- Test: `tests/test_move_endpoints.py`

- [ ] **Step 1: Add failing tests for apply-move**

Append to `tests/test_move_endpoints.py`:

```python
from app.models.agent import AgentKind, AgentMessage, MessageRole


async def _create_proposal(
    db: AsyncSession,
    athlete_id: uuid.UUID,
    workout: PlannedWorkout,
    option_edits: list[dict] | None = None,
) -> uuid.UUID:
    """Create a proposal agent_message for testing apply-move."""
    proposal_id = uuid.uuid4()
    msg = AgentMessage(
        athlete_id=athlete_id,
        agent=AgentKind.plan_adapter,
        role=MessageRole.assistant,
        content_md="Test proposal",
        related_workout_id=workout.id,
        proposal_state_json={
            "proposal_id": str(proposal_id),
            "original_date": workout.scheduled_date.isoformat(),
            "new_date": (workout.scheduled_date + __import__("datetime").timedelta(days=1)).isoformat(),
            "options": [
                {
                    "id": "option_a",
                    "label": "Option A",
                    "tradeoff": "Test tradeoff",
                    "edits": option_edits or [],
                    "rationale": "Test rationale",
                },
                {
                    "id": "option_b",
                    "label": "Option B",
                    "tradeoff": "Test tradeoff B",
                    "edits": [],
                    "rationale": "Test rationale B",
                },
            ],
            "state": "pending",
        },
    )
    db.add(msg)
    await db.commit()
    return proposal_id


@pytest.mark.asyncio
async def test_apply_move_just_move(client: AsyncClient, db: AsyncSession, athlete, auth_headers):
    pw = await _seed_workout(db, athlete.id, date(2026, 6, 3))
    proposal_id = await _create_proposal(db, athlete.id, pw)

    resp = await client.post(
        f"/workouts/{pw.id}/apply-move",
        json={"proposal_id": str(proposal_id), "choice": "just_move"},
        headers=auth_headers,
    )
    assert resp.status_code == 200

    await db.refresh(pw)
    assert pw.scheduled_date == date(2026, 6, 4)
    assert pw.status == WorkoutStatus.moved
    assert pw.original_date == date(2026, 6, 3)  # unchanged


@pytest.mark.asyncio
async def test_apply_move_cancel(client: AsyncClient, db: AsyncSession, athlete, auth_headers):
    pw = await _seed_workout(db, athlete.id, date(2026, 6, 3))
    original_date = pw.scheduled_date
    proposal_id = await _create_proposal(db, athlete.id, pw)

    resp = await client.post(
        f"/workouts/{pw.id}/apply-move",
        json={"proposal_id": str(proposal_id), "choice": "cancel"},
        headers=auth_headers,
    )
    assert resp.status_code == 200

    await db.refresh(pw)
    assert pw.scheduled_date == original_date  # unchanged
    assert pw.status == WorkoutStatus.planned  # unchanged


@pytest.mark.asyncio
async def test_apply_move_option_a_with_edits(
    client: AsyncClient, db: AsyncSession, athlete, auth_headers
):
    pw = await _seed_workout(db, athlete.id, date(2026, 6, 3))
    # Create a second workout to be edited by option_a
    pw2 = await _seed_workout(db, athlete.id, date(2026, 6, 4))

    edits = [
        {"workout_id": str(pw2.id), "field": "scheduled_date", "new_value": "2026-06-05"},
    ]
    proposal_id = await _create_proposal(db, athlete.id, pw, option_edits=edits)

    resp = await client.post(
        f"/workouts/{pw.id}/apply-move",
        json={"proposal_id": str(proposal_id), "choice": "option_a"},
        headers=auth_headers,
    )
    assert resp.status_code == 200

    await db.refresh(pw)
    assert pw.scheduled_date == date(2026, 6, 4)
    assert pw.status == WorkoutStatus.moved

    await db.refresh(pw2)
    assert pw2.scheduled_date == date(2026, 6, 5)
    assert pw2.status == WorkoutStatus.moved


@pytest.mark.asyncio
async def test_apply_move_invalid_proposal(client: AsyncClient, db: AsyncSession, athlete, auth_headers):
    pw = await _seed_workout(db, athlete.id)
    fake_proposal = uuid.uuid4()
    resp = await client.post(
        f"/workouts/{pw.id}/apply-move",
        json={"proposal_id": str(fake_proposal), "choice": "just_move"},
        headers=auth_headers,
    )
    assert resp.status_code == 404
```

- [ ] **Step 2: Run to verify failure**

```bash
docker compose -f "C:/Coding Projects/marathon_app/docker-compose.yml" exec api pytest tests/test_move_endpoints.py::test_apply_move_just_move -v
```

- [ ] **Step 3: Implement apply-move endpoint**

Add to `app/routes/workouts.py`:

```python
from datetime import date as date_type

from app.schemas.move import ApplyMoveRequest


@router.post("/{workout_id}/apply-move")
async def apply_move(
    workout_id: uuid.UUID,
    body: ApplyMoveRequest,
    athlete: Athlete = Depends(get_current_athlete),
    db: AsyncSession = Depends(get_db),
):
    # Find the workout
    result = await db.execute(
        select(PlannedWorkout)
        .join(Cycle)
        .join(Plan)
        .where(PlannedWorkout.id == workout_id, Plan.athlete_id == athlete.id)
    )
    pw = result.scalar_one_or_none()
    if pw is None:
        raise HTTPException(status_code=404, detail="Workout not found")

    # Find the proposal
    from app.models.agent import AgentMessage

    result = await db.execute(
        select(AgentMessage).where(
            AgentMessage.related_workout_id == workout_id,
            AgentMessage.proposal_state_json["proposal_id"].as_string()
            == str(body.proposal_id),
        )
    )
    msg = result.scalar_one_or_none()
    if msg is None:
        raise HTTPException(status_code=404, detail="Proposal not found")

    proposal = msg.proposal_state_json

    if body.choice == "cancel":
        proposal["state"] = "discarded"
        msg.proposal_state_json = proposal
        from sqlalchemy.orm.attributes import flag_modified

        flag_modified(msg, "proposal_state_json")
        await db.commit()
        return {"ok": True}

    # Apply the move to the primary workout
    new_date = date_type.fromisoformat(proposal["new_date"])
    pw.scheduled_date = new_date
    pw.status = WorkoutStatus.moved

    if body.choice in ("option_a", "option_b"):
        # Find the chosen option and apply its edits
        chosen = None
        for opt in proposal["options"]:
            if opt["id"] == body.choice:
                chosen = opt
                break

        if chosen is None:
            raise HTTPException(status_code=400, detail=f"Invalid choice: {body.choice}")

        for edit in chosen.get("edits", []):
            edit_wid = uuid.UUID(edit["workout_id"])
            # Validate workout belongs to same athlete
            edit_result = await db.execute(
                select(PlannedWorkout)
                .join(Cycle)
                .join(Plan)
                .where(PlannedWorkout.id == edit_wid, Plan.athlete_id == athlete.id)
            )
            edit_pw = edit_result.scalar_one_or_none()
            if edit_pw is None:
                raise HTTPException(
                    status_code=400,
                    detail=f"Edit references unknown workout {edit_wid}",
                )

            field = edit["field"]
            value = edit["new_value"]

            if field == "scheduled_date":
                edit_pw.scheduled_date = date_type.fromisoformat(value)
                edit_pw.status = WorkoutStatus.moved
            elif field == "status":
                if value not in ("planned", "moved", "skipped"):
                    raise HTTPException(
                        status_code=400, detail=f"Invalid status: {value}"
                    )
                edit_pw.status = WorkoutStatus(value)
            else:
                raise HTTPException(
                    status_code=400, detail=f"Invalid edit field: {field}"
                )

    # Mark proposal as applied
    proposal["state"] = "applied"
    proposal["applied_choice"] = body.choice
    msg.proposal_state_json = proposal
    from sqlalchemy.orm.attributes import flag_modified

    flag_modified(msg, "proposal_state_json")
    await db.commit()
    return {"ok": True}
```

- [ ] **Step 4: Run all move tests**

```bash
docker compose -f "C:/Coding Projects/marathon_app/docker-compose.yml" exec api pytest tests/test_move_endpoints.py -v
```
Expected: all PASS

- [ ] **Step 5: Commit**

```bash
git add app/routes/workouts.py tests/test_move_endpoints.py
git commit -m "feat: POST /workouts/{id}/apply-move with edit validation"
```

---

## Task 6: OpenAPI Export Script

**Files:**
- Create: `scripts/export_openapi.sh`

- [ ] **Step 1: Create the export script**

Create `scripts/export_openapi.sh`:

```bash
#!/bin/bash
# Export FastAPI OpenAPI spec for the mobile app
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

echo "Exporting OpenAPI spec..."
docker compose -f "$PROJECT_DIR/docker-compose.yml" exec -T api python -c "
import json
from app.main import app
spec = app.openapi()
print(json.dumps(spec, indent=2, default=str))
" > "$PROJECT_DIR/mobile/openapi.json"

echo "Exported to mobile/openapi.json"
```

- [ ] **Step 2: Make executable and create mobile directory**

```bash
cd "C:/Coding Projects/marathon_app"
mkdir -p mobile
chmod +x scripts/export_openapi.sh
```

- [ ] **Step 3: Commit**

```bash
git add scripts/export_openapi.sh
git commit -m "feat: OpenAPI export script for mobile type generation"
```

---

## Task 7: Full Test Suite + Lint Verification

**Files:**
- All test files
- All source files

- [ ] **Step 1: Run full test suite**

```bash
docker compose -f "C:/Coding Projects/marathon_app/docker-compose.yml" exec api pytest -v
```
Expected: all tests pass (22 from Session 1 + new move/adapter tests)

- [ ] **Step 2: Run ruff check + format**

```bash
docker compose -f "C:/Coding Projects/marathon_app/docker-compose.yml" exec api ruff check app/ tests/
docker compose -f "C:/Coding Projects/marathon_app/docker-compose.yml" exec api ruff format --check app/ tests/
```
Fix any issues.

- [ ] **Step 3: Commit if any fixes needed**

```bash
git add -A
git commit -m "chore: lint clean, all tests passing"
```

- [ ] **Step 4: Push**

```bash
git push
```

---

## Done Criteria

- [ ] `PATCH /workouts/{id}/move` calls Plan Adapter, returns proposal with 2 options
- [ ] `POST /workouts/{id}/apply-move` correctly applies edits per option choice
- [ ] `POST /workouts/{id}/apply-move` with "just_move" moves only the target workout
- [ ] `POST /workouts/{id}/apply-move` with "cancel" makes no changes
- [ ] `PATCH /workouts/{id}/skip` sets status to skipped
- [ ] Plan Adapter persists request/response in agent_messages
- [ ] Edit validation rejects bad workout_ids or fields
- [ ] Atomic transaction — no partial application
- [ ] All Session 1 tests still pass
- [ ] `ruff check` + `ruff format --check` clean
