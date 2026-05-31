# Coach Chat Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship a free-form conversational running coach on the Chat tab, powered by Google Gemini (`gemini-2.5-flash`), with live athlete context, a persistent single thread, and the ability to propose plan changes that flow through the app's existing proposal → apply machinery.

**Architecture:** Backend-first. A thin mockable Gemini client wraps `google-genai`; `build_athlete_context` assembles a live snapshot+markdown block from the existing plan aggregators; `coach_chat.run_turn` persists the user turn, calls Gemini with a `propose_plan_change` function declaration, and persists the assistant turn (text or proposal). The apply/cancel core is refactored out of `apply-move` into a shared `proposal_apply` service — which re-validates every edit's `workout_id` against the athlete before mutating — and is called from both `apply-move` and a new `POST /chat/proposal/apply`. Mobile replaces the placeholder with a real `ChatScreen` that reuses the existing `ProposalSheet`.

**Tech Stack:** Backend — FastAPI, Pydantic v2, SQLAlchemy async, `google-genai`. Mobile — Expo SDK 54, RN 0.81, React 19, TS 5.9 strict, NativeWind v4, react-query, `react-native-markdown-display`.

**Spec source:** `docs/superpowers/specs/2026-05-30-coach-chat-design.md` (with the §3.2 security requirement added 2026-05-30).

**Validation gates:**
- Backend: `docker compose exec -T api pytest` (tests run IN the container — host pytest lacks deps). Single test: `docker compose exec -T api pytest tests/path::test_name -v`.
- Mobile: `cd mobile && npx tsc --noEmit` (no jest infra; typecheck + manual smoke is the gate).

**Resolved §10 open questions (decided in this plan):**
- **Q1 — Gemini context caching in v1:** **OFF.** The static prefix (system prompt + philosophy) is small; explicit `CachedContent` management adds API surface, TTL bookkeeping, and a cache-miss failure mode for a single-athlete app with low call volume and near-zero cost on Flash. Keep `run_turn` simple: send the full prompt each turn. Leave a one-line `# TODO(caching)` note in `gemini_client.py`. Revisit only if token cost becomes material.
- **Q2 — User-turn persistence on Gemini failure:** **Keep-and-mark, do NOT roll back.** Persist the user turn (so the thread shows what the athlete typed and `context_snapshot_json` is captured for audit), then call Gemini in a separate try/except. On failure: commit the user turn, persist NO assistant row, raise `HTTPException(502)`. The user turn carries `proposal_state_json=None` and is simply un-replied; the next successful turn includes it in history. This avoids the "user typed, got an error, and their message vanished" UX, and keeps a single commit boundary before the LLM call.
- **Q3 — Mobile markdown renderer:** **`react-native-markdown-display`.** It is the de-facto RN markdown lib, renders on web (Expo web/PWA) and native, supports custom style rules to map onto the retro theme tokens, and avoids hand-rolling a parser. A minimal custom renderer would re-implement lists/bold/links badly. Pin it and map headings/links/code to `fonts`/`colors`.

**Deployment gotchas that apply (from CLAUDE.md):**
- `GEMINI_API_KEY` is a **backend** env var (Railway). It is NEVER `EXPO_PUBLIC_*` — that would inline the key into the client JS bundle. The mobile app only calls `/chat`; it never sees the key.
- 5xx without CORS headers makes the browser report a phantom "CORS error." All Gemini/key failures MUST surface as `HTTPException(4xx/5xx)` from route-level try/except so FastAPI's CORS middleware still wraps them. Use 502 for Gemini failure, 503 for missing key.
- `EXPO_PUBLIC_API_URL` must include `https://` (axios treats bare hosts as relative). No change needed here — `ChatScreen` reuses the existing `api` axios client.
- After adding the `google-genai` dep, the container must be rebuilt (`docker compose build api`) — host-installed packages don't exist in the container.

---

## File Structure

**Backend — new files (4):**
- `app/services/llm/gemini_client.py` — thin async Gemini wrapper + `propose_plan_change` function declaration + system prompt. Mockable like `get_anthropic_client()`.
- `app/services/llm/__init__.py` — package marker.
- `app/services/agents/coach_chat.py` — `run_turn()` turn engine.
- `app/services/proposal_apply.py` — shared apply/cancel core (extracted from `apply-move`), with athlete ownership re-validation.

**Backend — implement stubs (2):**
- `app/services/agent_context.py` — implement `build_athlete_context()` → returns `AthleteContext` (snapshot dict + markdown).
- `app/routes/chat.py` — implement `GET /chat`, `POST /chat`, `POST /chat/proposal/apply`.

**Backend — modify (3):**
- `app/config.py` — add `gemini_api_key`, `gemini_model`.
- `pyproject.toml` — add `google-genai`.
- `app/routes/workouts.py` — `apply_move` route delegates to the shared `proposal_apply` service.

**Backend — new schemas (1):**
- `app/schemas/chat.py` — `ChatMessageOut`, `ChatHistoryOut`, `PostChatRequest`, `PostChatResponse`, `ChatProposalApplyRequest`.

**Backend — tests (4):**
- `tests/services/test_agent_context.py`
- `tests/services/test_coach_chat.py`
- `tests/services/test_proposal_apply.py`
- `tests/routes/test_chat.py`

**Mobile — new files (3):**
- `mobile/src/screens/ChatScreen.tsx` — replaces `ChatPlaceholderScreen.tsx`.
- `mobile/src/api/hooks/useChat.ts` — `useChatHistory`, `useSendChat`, `useApplyChatProposal`.
- `mobile/src/components/ChatBubble.tsx` — user/assistant bubble with markdown.

**Mobile — modify (3):**
- `mobile/src/api/types.ts` — add chat types.
- `mobile/src/navigation/RootNavigator.tsx` — point Chat tab at `ChatScreen`.
- `mobile/package.json` — add `react-native-markdown-display`.

**Mobile — delete (1):**
- `mobile/src/screens/ChatPlaceholderScreen.tsx`.

**Design-review note carried into the plan (apply-by-proposal_id, not by workout_id):** the existing `apply-move` looks proposals up by BOTH `related_workout_id == workout_id` AND `proposal_id`. The new `/chat/proposal/apply` route has no `workout_id` in its path, and a chat proposal's `related_workout_id` may be NULL or a non-primary "lead" workout. Therefore the shared service MUST look the proposal up by **`proposal_id` alone, scoped to the athlete via `AgentMessage.athlete_id`** — not by workout_id. The `apply-move` route keeps its own workout_id 404 check before delegating, preserving its existing contract; the shared core does the proposal lookup.

---

## Phase A — Backend foundation: config, deps, Gemini client

### Task A1: Add Gemini config + dependency

**Files:**
- Modify: `app/config.py`
- Modify: `pyproject.toml:5-20`

- [ ] **Step 1: Add config fields**

In `app/config.py`, inside `Settings`, after `anthropic_api_key`:

```python
    anthropic_api_key: str = ""
    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.5-flash"
```

- [ ] **Step 2: Add the dependency**

In `pyproject.toml`, add to the `dependencies` list (after `"anthropic>=0.39.0",`):

```toml
    "google-genai>=1.0.0",
```

- [ ] **Step 3: Rebuild the container so the dep is installed**

Run: `docker compose build api && docker compose up -d api`
Expected: build succeeds; `docker compose exec -T api python -c "import google.genai; print('ok')"` prints `ok`.

- [ ] **Step 4: Commit**

```bash
git add app/config.py pyproject.toml
git commit -m "feat(chat): add gemini config + google-genai dependency"
```

### Task A2: Gemini client wrapper + function declaration

**Files:**
- Create: `app/services/llm/__init__.py`
- Create: `app/services/llm/gemini_client.py`
- Test: `tests/services/test_gemini_client.py`

- [ ] **Step 1: Create the package marker**

`app/services/llm/__init__.py`:

```python
```

(empty file)

- [ ] **Step 2: Write the failing test**

`tests/services/test_gemini_client.py`:

```python
from app.services.llm.gemini_client import (
    COACH_SYSTEM_PROMPT,
    PROPOSE_PLAN_CHANGE_DECLARATION,
)


def test_declaration_shape():
    d = PROPOSE_PLAN_CHANGE_DECLARATION
    assert d["name"] == "propose_plan_change"
    props = d["parameters"]["properties"]
    assert set(props) >= {"summary", "options"}
    opt = props["options"]["items"]["properties"]
    assert set(opt) >= {"id", "label", "tradeoff", "rationale", "edits"}
    edit = opt["edits"]["items"]["properties"]
    assert set(edit) == {"workout_id", "field", "new_value"}
    assert edit["field"]["enum"] == ["scheduled_date", "status"]


def test_system_prompt_mentions_guardrails():
    assert "never fabricate" in COACH_SYSTEM_PROMPT.lower()
```

- [ ] **Step 3: Run test to verify it fails**

Run: `docker compose exec -T api pytest tests/services/test_gemini_client.py -v`
Expected: FAIL — `ModuleNotFoundError: app.services.llm.gemini_client`.

- [ ] **Step 4: Write the client**

`app/services/llm/gemini_client.py`:

```python
from typing import Any

from google import genai

from app.config import settings

COACH_SYSTEM_PROMPT = (
    "You are an experienced marathon coach working with this athlete on a 12-month, "
    "three-marathon plan. You value durability over peak fitness.\n"
    "Be specific, reference the athlete's data, and stay encouraging and concise.\n"
    "You may propose plan changes via the propose_plan_change function; always explain "
    "the tradeoffs of any proposal. Otherwise answer conversationally.\n"
    "Guardrails: give general training guidance only — no medical advice; defer to the "
    "athlete on injury and health. Never fabricate data: reason only from the provided "
    "athlete context. If data is missing, say so plainly."
)

# propose_plan_change mirrors the established proposal_state_json contract
# (summary + options[] each with id/label/tradeoff/rationale/edits[]).
# Each edit is {workout_id, field in {scheduled_date, status}, new_value}.
PROPOSE_PLAN_CHANGE_DECLARATION: dict[str, Any] = {
    "name": "propose_plan_change",
    "description": "Propose one or more plan-change options for the athlete to review.",
    "parameters": {
        "type": "object",
        "required": ["summary", "options"],
        "properties": {
            "summary": {"type": "string", "description": "1-2 sentence impact assessment"},
            "options": {
                "type": "array",
                "items": {
                    "type": "object",
                    "required": ["id", "label", "tradeoff", "rationale", "edits"],
                    "properties": {
                        "id": {"type": "string", "enum": ["option_a", "option_b"]},
                        "label": {"type": "string"},
                        "tradeoff": {"type": "string"},
                        "rationale": {"type": "string"},
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
                    },
                },
            },
        },
    },
}


def get_gemini_client() -> genai.Client:
    """Create a Gemini client. Separated for test mocking (mirrors get_anthropic_client)."""
    # TODO(caching): v1 sends the full prompt each turn; revisit CachedContent if cost matters.
    return genai.Client(api_key=settings.gemini_api_key)
```

- [ ] **Step 5: Run test to verify it passes**

Run: `docker compose exec -T api pytest tests/services/test_gemini_client.py -v`
Expected: PASS (2 passed).

- [ ] **Step 6: Commit**

```bash
git add app/services/llm/__init__.py app/services/llm/gemini_client.py tests/services/test_gemini_client.py
git commit -m "feat(chat): gemini client wrapper + propose_plan_change declaration"
```

---

## Phase B — Living context: `build_athlete_context`

### Task B1: Implement `build_athlete_context`

**Files:**
- Modify: `app/services/agent_context.py`
- Test: `tests/services/test_agent_context.py`

Returns a dataclass with both a structured `snapshot` dict (persisted to `context_snapshot_json`) and a compact `markdown` block (injected into the prompt). Reuses `build_plan_stats` (KPIs), `_build_plan_current` data, and direct today/week/recent-completed queries. Must NOT raise when there is no active plan — returns a minimal context.

- [ ] **Step 1: Write the failing test**

`tests/services/test_agent_context.py`:

```python
import pytest

from app.services.agent_context import build_athlete_context


@pytest.mark.asyncio
async def test_build_context_has_snapshot_and_markdown(db_session, seeded_athlete):
    ctx = await build_athlete_context(db_session, seeded_athlete.id)
    assert isinstance(ctx.snapshot, dict)
    assert isinstance(ctx.markdown, str)
    assert ctx.markdown  # non-empty
    # snapshot carries plan + progress sections
    assert "plan" in ctx.snapshot
    assert "progress" in ctx.snapshot
    assert "today" in ctx.snapshot


@pytest.mark.asyncio
async def test_build_context_no_plan_is_minimal(db_session, athlete_without_plan):
    ctx = await build_athlete_context(db_session, athlete_without_plan.id)
    assert ctx.snapshot["plan"] is None
    assert "no plan" in ctx.markdown.lower()
```

> **Fixture note:** `seeded_athlete` and `db_session` already exist in `tests/conftest.py` (used by other service tests). Add an `athlete_without_plan` fixture if one is not present — an `Athlete` row with no `Plan`. Check `tests/conftest.py` before writing; reuse existing fixtures.

- [ ] **Step 2: Run test to verify it fails**

Run: `docker compose exec -T api pytest tests/services/test_agent_context.py -v`
Expected: FAIL — `NotImplementedError: Wired in session 3`.

- [ ] **Step 3: Implement the context builder**

Replace `app/services/agent_context.py` entirely:

```python
from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.plan import Cycle, Plan
from app.models.workout import CompletedWorkout, PlannedWorkout
from app.services.plan_aggregator import build_plan_stats


@dataclass
class AthleteContext:
    snapshot: dict[str, Any]
    markdown: str


async def _active_plan(db: AsyncSession, athlete_id: uuid.UUID) -> Plan | None:
    return (
        await db.execute(
            select(Plan).where(Plan.athlete_id == athlete_id, Plan.is_active.is_(True)).limit(1)
        )
    ).scalar_one_or_none()


async def _active_cycle(db: AsyncSession, plan_id: uuid.UUID, today: date) -> Cycle | None:
    cycle = (
        await db.execute(
            select(Cycle)
            .where(Cycle.plan_id == plan_id, Cycle.start_date <= today, Cycle.end_date >= today)
            .order_by(Cycle.sequence)
            .limit(1)
        )
    ).scalar_one_or_none()
    if cycle is not None:
        return cycle
    return (
        await db.execute(
            select(Cycle)
            .where(Cycle.plan_id == plan_id, Cycle.start_date <= today)
            .order_by(Cycle.start_date.desc())
            .limit(1)
        )
    ).scalar_one_or_none()


def _wk(w: PlannedWorkout) -> dict[str, Any]:
    return {
        "id": str(w.id),
        "date": w.scheduled_date.isoformat(),
        "type": w.type.value,
        "status": w.status.value,
        "title": w.title,
        "distance_mi": float(w.distance_mi) if w.distance_mi is not None else None,
    }


async def build_athlete_context(db: AsyncSession, athlete_id: uuid.UUID) -> AthleteContext:
    """Assemble a fresh live-DB context (snapshot dict + markdown block) for the coach."""
    today = date.today()
    plan = await _active_plan(db, athlete_id)

    if plan is None:
        snapshot: dict[str, Any] = {
            "plan": None,
            "progress": None,
            "today": [],
            "week": [],
            "recent_actuals": [],
        }
        return AthleteContext(snapshot=snapshot, markdown="No plan is currently loaded.")

    cycle = await _active_cycle(db, plan.id, today)

    # Progress KPIs (reuse the aggregator; cycle scope).
    stats = await build_plan_stats(db, athlete_id, scope="cycle")

    # Today's prescribed workouts.
    today_rows = (
        (
            await db.execute(
                select(PlannedWorkout)
                .join(Cycle, PlannedWorkout.cycle_id == Cycle.id)
                .where(Cycle.plan_id == plan.id, PlannedWorkout.scheduled_date == today)
                .order_by(PlannedWorkout.scheduled_date)
            )
        )
        .scalars()
        .all()
    )

    # This week (Mon..Sun).
    week_start = today - timedelta(days=today.weekday())
    week_end = week_start + timedelta(days=6)
    week_rows = (
        (
            await db.execute(
                select(PlannedWorkout)
                .join(Cycle, PlannedWorkout.cycle_id == Cycle.id)
                .where(
                    Cycle.plan_id == plan.id,
                    PlannedWorkout.scheduled_date >= week_start,
                    PlannedWorkout.scheduled_date <= week_end,
                )
                .order_by(PlannedWorkout.scheduled_date)
            )
        )
        .scalars()
        .all()
    )

    # Recent actuals (last 14 days of Garmin-synced completions).
    recent_rows = (
        (
            await db.execute(
                select(CompletedWorkout)
                .where(
                    CompletedWorkout.athlete_id == athlete_id,
                    CompletedWorkout.activity_date >= today - timedelta(days=14),
                )
                .order_by(CompletedWorkout.activity_date.desc())
            )
        )
        .scalars()
        .all()
    )

    cycle_snap = None
    if cycle is not None:
        cycle_snap = {
            "name": cycle.name,
            "race_name": cycle.race_name,
            "race_date": cycle.race_date.isoformat(),
            "days_to_race": (cycle.race_date - today).days,
            "peak_week_target": cycle.peak_week_target,
        }

    snapshot = {
        "plan": {"name": plan.name, "philosophy_md": plan.philosophy_md, "cycle": cycle_snap},
        "progress": {
            "on_plan_pct": stats.on_plan_pct,
            "done_count": stats.done_count,
            "skipped_count": stats.skipped_count,
            "planned_mi": str(stats.planned_mi),
            "actual_mi": str(stats.actual_mi),
            "streak_days": stats.streak_days,
            "next_milestone": stats.next_milestone.label if stats.next_milestone else None,
        },
        "today": [_wk(w) for w in today_rows],
        "week": [_wk(w) for w in week_rows],
        "recent_actuals": [
            {
                "date": c.activity_date.isoformat(),
                "type": c.activity_type,
                "distance_mi": round(float(c.distance_m) / 1609.344, 2)
                if c.distance_m is not None
                else None,
                "avg_hr": c.avg_hr,
            }
            for c in recent_rows
        ],
    }

    markdown = _render_markdown(snapshot)
    return AthleteContext(snapshot=snapshot, markdown=markdown)


def _render_markdown(s: dict[str, Any]) -> str:
    lines: list[str] = []
    p = s["plan"]
    lines.append(f"## Plan: {p['name']}")
    if p["philosophy_md"]:
        lines.append(f"Philosophy: {p['philosophy_md']}")
    c = p["cycle"]
    if c:
        lines.append(
            f"Cycle **{c['name']}** — {c['race_name']} on {c['race_date']} "
            f"({c['days_to_race']}d out). Peak week target: {c['peak_week_target']}."
        )
    pr = s["progress"]
    if pr:
        lines.append(
            f"\n## Progress (cycle): {pr['on_plan_pct']:.0%} on-plan; "
            f"{pr['done_count']} done / {pr['skipped_count']} skipped; "
            f"{pr['actual_mi']} of {pr['planned_mi']} mi; streak {pr['streak_days']}d. "
            f"Next: {pr['next_milestone']}."
        )
    lines.append("\n## Today")
    lines.append(
        "\n".join(f"- {w['title']} ({w['type']}, {w['status']})" for w in s["today"]) or "- Rest"
    )
    lines.append("\n## This week")
    lines.append(
        "\n".join(
            f"- {w['date']}: {w['title']} ({w['type']}, {w['status']}) [id {w['id']}]"
            for w in s["week"]
        )
        or "- (empty)"
    )
    lines.append("\n## Recent actuals (14d)")
    lines.append(
        "\n".join(
            f"- {a['date']}: {a['type']} {a['distance_mi']}mi"
            f"{f' @ {a['avg_hr']}bpm' if a['avg_hr'] else ''}"
            for a in s["recent_actuals"]
        )
        or "- (none synced)"
    )
    return "\n".join(lines)
```

> **Note:** workout IDs ARE included in the "This week" markdown block on purpose — the model needs real IDs to reference in `propose_plan_change.edits[].workout_id`. The server re-validates ownership before applying (Task D1), so injection-via-bad-ID is a non-issue.

- [ ] **Step 4: Run test to verify it passes**

Run: `docker compose exec -T api pytest tests/services/test_agent_context.py -v`
Expected: PASS (2 passed).

- [ ] **Step 5: Commit**

```bash
git add app/services/agent_context.py tests/services/test_agent_context.py
git commit -m "feat(chat): implement build_athlete_context (snapshot + markdown)"
```

---

## Phase C — Turn engine: `coach_chat.run_turn`

### Task C1: Chat schemas

**Files:**
- Create: `app/schemas/chat.py`

- [ ] **Step 1: Write the schemas**

`app/schemas/chat.py`:

```python
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.move import ProposalOut


class ChatMessageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    role: str  # "user" | "assistant"
    content_md: str
    created_at: datetime
    proposal: ProposalOut | None = None


class ChatHistoryOut(BaseModel):
    messages: list[ChatMessageOut]


class PostChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)


class PostChatResponse(BaseModel):
    reply_md: str
    proposal: ProposalOut | None = None


class ChatProposalApplyRequest(BaseModel):
    proposal_id: UUID
    choice: str  # "option_a" | "option_b" | "just_move" | "cancel"
```

- [ ] **Step 2: Verify it imports**

Run: `docker compose exec -T api python -c "import app.schemas.chat; print('ok')"`
Expected: `ok`.

- [ ] **Step 3: Commit**

```bash
git add app/schemas/chat.py
git commit -m "feat(chat): chat request/response schemas"
```

### Task C2: `run_turn` — text + proposal branches

**Files:**
- Create: `app/services/agents/coach_chat.py`
- Test: `tests/services/test_coach_chat.py`

`run_turn` persists the user turn, calls Gemini, branches on a function call vs plain text, persists the assistant turn. Gemini is mocked in tests by patching `get_gemini_client`. The Gemini SDK returns function calls and text on `response.candidates[0].content.parts`; the wrapper inspects parts for a `function_call` named `propose_plan_change`.

- [ ] **Step 1: Write the failing tests**

`tests/services/test_coach_chat.py`:

```python
from unittest.mock import MagicMock, patch

import pytest

from app.models.agent import AgentKind, AgentMessage, MessageRole
from app.services.agents import coach_chat
from sqlalchemy import select


def _text_response(text: str):
    part = MagicMock()
    part.function_call = None
    part.text = text
    cand = MagicMock()
    cand.content.parts = [part]
    resp = MagicMock()
    resp.candidates = [cand]
    return resp


def _proposal_response(summary: str, workout_id: str):
    fc = MagicMock()
    fc.name = "propose_plan_change"
    fc.args = {
        "summary": summary,
        "options": [
            {
                "id": "option_a",
                "label": "Shift long run",
                "tradeoff": "more rest",
                "rationale": "durability",
                "edits": [
                    {"workout_id": workout_id, "field": "scheduled_date", "new_value": "2026-06-02"}
                ],
            }
        ],
    }
    part = MagicMock()
    part.function_call = fc
    part.text = None
    cand = MagicMock()
    cand.content.parts = [part]
    resp = MagicMock()
    resp.candidates = [cand]
    return resp


@pytest.mark.asyncio
async def test_run_turn_text_persists_two_rows(db_session, seeded_athlete):
    fake = MagicMock()
    fake.models.generate_content.return_value = _text_response("Nice work this week.")
    with patch.object(coach_chat, "get_gemini_client", return_value=fake):
        result = await coach_chat.run_turn(db_session, seeded_athlete.id, "How am I doing?")

    assert result.reply_md == "Nice work this week."
    assert result.proposal is None
    rows = (
        (await db_session.execute(
            select(AgentMessage)
            .where(AgentMessage.agent == AgentKind.user_chat)
            .order_by(AgentMessage.created_at)
        )).scalars().all()
    )
    assert len(rows) == 2
    assert rows[0].role == MessageRole.user
    assert rows[0].context_snapshot_json is not None
    assert rows[1].role == MessageRole.assistant


@pytest.mark.asyncio
async def test_run_turn_proposal_branch(db_session, seeded_athlete, a_planned_workout):
    fake = MagicMock()
    fake.models.generate_content.return_value = _proposal_response(
        "Moving your long run helps recovery.", str(a_planned_workout.id)
    )
    with patch.object(coach_chat, "get_gemini_client", return_value=fake):
        result = await coach_chat.run_turn(
            db_session, seeded_athlete.id, "Can I move my long run?"
        )

    assert result.proposal is not None
    assert result.proposal["state"] == "pending"
    assert result.proposal["options"][0]["id"] == "option_a"
    # assistant row carries the proposal
    msg = (
        (await db_session.execute(
            select(AgentMessage).where(AgentMessage.role == MessageRole.assistant)
        )).scalars().first()
    )
    assert msg.proposal_state_json["proposal_id"] == result.proposal["proposal_id"]
```

> **Fixture note:** `a_planned_workout` should return one `PlannedWorkout` belonging to `seeded_athlete`. Reuse an existing fixture from `tests/conftest.py` if present; otherwise add one.

- [ ] **Step 2: Run tests to verify they fail**

Run: `docker compose exec -T api pytest tests/services/test_coach_chat.py -v`
Expected: FAIL — `ModuleNotFoundError: app.services.agents.coach_chat`.

- [ ] **Step 3: Implement `run_turn`**

`app/services/agents/coach_chat.py`:

```python
from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.agent import AgentKind, AgentMessage, MessageRole
from app.services.agent_context import build_athlete_context
from app.services.llm.gemini_client import (
    COACH_SYSTEM_PROMPT,
    PROPOSE_PLAN_CHANGE_DECLARATION,
    get_gemini_client,
)

HISTORY_LIMIT = 20


@dataclass
class ChatTurnResult:
    reply_md: str
    proposal: dict[str, Any] | None = None


async def _recent_history(db: AsyncSession, athlete_id: uuid.UUID) -> list[AgentMessage]:
    rows = (
        (
            await db.execute(
                select(AgentMessage)
                .where(
                    AgentMessage.athlete_id == athlete_id,
                    AgentMessage.agent == AgentKind.user_chat,
                )
                .order_by(AgentMessage.created_at.desc())
                .limit(HISTORY_LIMIT)
            )
        )
        .scalars()
        .all()
    )
    return list(reversed(rows))


def _build_prompt(context_md: str, history: list[AgentMessage], message: str) -> str:
    parts = [f"Athlete context:\n{context_md}", "---"]
    if history:
        convo = "\n".join(
            f"{m.role.value}: {m.content_md}" for m in history if m.content_md
        )
        parts.append(convo)
        parts.append("---")
    parts.append(f"user: {message}")
    return "\n".join(parts)


def _extract(response: Any) -> tuple[str, dict[str, Any] | None]:
    """Return (text, function_args|None) from a Gemini response."""
    text_chunks: list[str] = []
    fc_args: dict[str, Any] | None = None
    for cand in response.candidates or []:
        for part in cand.content.parts or []:
            fc = getattr(part, "function_call", None)
            if fc is not None and getattr(fc, "name", None) == "propose_plan_change":
                fc_args = dict(fc.args)
            elif getattr(part, "text", None):
                text_chunks.append(part.text)
    return ("".join(text_chunks).strip(), fc_args)


async def run_turn(
    db: AsyncSession, athlete_id: uuid.UUID, message: str
) -> ChatTurnResult:
    ctx = await build_athlete_context(db, athlete_id)

    # 1. Persist the user turn (kept even if Gemini later fails — see plan Q2).
    user_msg = AgentMessage(
        athlete_id=athlete_id,
        agent=AgentKind.user_chat,
        role=MessageRole.user,
        content_md=message,
        context_snapshot_json=ctx.snapshot,
    )
    db.add(user_msg)
    await db.commit()

    # 2. Load history (includes the just-persisted user turn at the tail; drop it).
    history = await _recent_history(db, athlete_id)
    history = [m for m in history if m.id != user_msg.id]

    # 3. Call Gemini. The caller (route) wraps this in try/except → 502.
    client = get_gemini_client()
    from google.genai import types  # local import keeps module import-safe in tests

    response = client.models.generate_content(
        model=settings.gemini_model,
        contents=_build_prompt(ctx.markdown, history, message),
        config=types.GenerateContentConfig(
            system_instruction=COACH_SYSTEM_PROMPT,
            tools=[types.Tool(function_declarations=[PROPOSE_PLAN_CHANGE_DECLARATION])],
        ),
    )

    text, fc_args = _extract(response)

    # 4. Branch.
    if fc_args is not None:
        summary = fc_args["summary"]
        options = fc_args["options"]
        proposal_id = str(uuid.uuid4())
        lead_workout_id = _lead_workout_id(options)
        proposal_state = {
            "proposal_id": proposal_id,
            "summary": summary,
            "options": options,
            "state": "pending",
            "created_by": "user_chat",
        }
        assistant_msg = AgentMessage(
            athlete_id=athlete_id,
            agent=AgentKind.user_chat,
            role=MessageRole.assistant,
            content_md=summary,
            related_workout_id=lead_workout_id,
            proposal_state_json=proposal_state,
        )
        db.add(assistant_msg)
        await db.commit()
        return ChatTurnResult(reply_md=summary, proposal=proposal_state)

    reply = text or "I'm not sure how to respond to that — could you rephrase?"
    assistant_msg = AgentMessage(
        athlete_id=athlete_id,
        agent=AgentKind.user_chat,
        role=MessageRole.assistant,
        content_md=reply,
    )
    db.add(assistant_msg)
    await db.commit()
    return ChatTurnResult(reply_md=reply, proposal=None)


def _lead_workout_id(options: list[dict[str, Any]]) -> uuid.UUID | None:
    """The first edit's workout_id, used only as a soft pointer. Ownership is
    re-validated at apply time (proposal_apply), never trusted here."""
    for opt in options:
        for edit in opt.get("edits", []):
            try:
                return uuid.UUID(edit["workout_id"])
            except (KeyError, ValueError):
                continue
    return None
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `docker compose exec -T api pytest tests/services/test_coach_chat.py -v`
Expected: PASS (2 passed).

- [ ] **Step 5: Commit**

```bash
git add app/services/agents/coach_chat.py tests/services/test_coach_chat.py
git commit -m "feat(chat): coach_chat.run_turn (text + proposal branches)"
```

---

## Phase D — Shared apply/cancel service + ownership re-validation

### Task D1: Extract `proposal_apply` service with athlete ownership re-validation

**Files:**
- Create: `app/services/proposal_apply.py`
- Test: `tests/services/test_proposal_apply.py`

Extract the apply/cancel core from `apply-move`. **Lookup is by `proposal_id` scoped to the athlete via `AgentMessage.athlete_id`** (NOT by workout_id — the chat route has no workout_id). **Every edit's `workout_id` is re-validated against `Plan.athlete_id == athlete_id` before mutation** — the §3.2 security requirement. The service handles `cancel`, `just_move`, `option_a`, `option_b`.

- [ ] **Step 1: Write the failing tests**

`tests/services/test_proposal_apply.py`:

```python
import uuid

import pytest
from sqlalchemy import select

from app.models.agent import AgentKind, AgentMessage, MessageRole
from app.models.workout import PlannedWorkout, WorkoutStatus
from app.services.proposal_apply import ProposalNotFound, apply_proposal


async def _make_proposal(db, athlete_id, workout_id, *, new_date="2026-06-02"):
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
                        {"workout_id": str(workout_id), "field": "scheduled_date",
                         "new_value": new_date}
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


@pytest.mark.asyncio
async def test_apply_option_moves_owned_workout(db_session, seeded_athlete, a_planned_workout):
    pid = await _make_proposal(db_session, seeded_athlete.id, a_planned_workout.id)
    await apply_proposal(db_session, seeded_athlete.id, uuid.UUID(pid), "option_a")
    refreshed = (
        await db_session.execute(
            select(PlannedWorkout).where(PlannedWorkout.id == a_planned_workout.id)
        )
    ).scalar_one()
    assert refreshed.status == WorkoutStatus.moved
    assert refreshed.scheduled_date.isoformat() == "2026-06-02"


@pytest.mark.asyncio
async def test_apply_rejects_foreign_workout_id(
    db_session, seeded_athlete, foreign_planned_workout
):
    # Proposal references a workout owned by a DIFFERENT athlete (LLM-emitted bad ID).
    pid = await _make_proposal(db_session, seeded_athlete.id, foreign_planned_workout.id)
    with pytest.raises(Exception) as exc:
        await apply_proposal(db_session, seeded_athlete.id, uuid.UUID(pid), "option_a")
    assert "not found or not owned" in str(exc.value).lower()
    # foreign workout untouched
    refreshed = (
        await db_session.execute(
            select(PlannedWorkout).where(PlannedWorkout.id == foreign_planned_workout.id)
        )
    ).scalar_one()
    assert refreshed.status != WorkoutStatus.moved


@pytest.mark.asyncio
async def test_cancel_marks_discarded(db_session, seeded_athlete, a_planned_workout):
    pid = await _make_proposal(db_session, seeded_athlete.id, a_planned_workout.id)
    await apply_proposal(db_session, seeded_athlete.id, uuid.UUID(pid), "cancel")
    msg = (
        await db_session.execute(
            select(AgentMessage).where(
                AgentMessage.proposal_state_json["proposal_id"].as_string() == pid
            )
        )
    ).scalar_one()
    assert msg.proposal_state_json["state"] == "discarded"


@pytest.mark.asyncio
async def test_unknown_proposal_raises_not_found(db_session, seeded_athlete):
    with pytest.raises(ProposalNotFound):
        await apply_proposal(db_session, seeded_athlete.id, uuid.uuid4(), "option_a")
```

> **Fixture note:** `foreign_planned_workout` is a `PlannedWorkout` under a SECOND athlete's plan. Add it to `tests/conftest.py` if absent. `a_planned_workout` is the seeded athlete's own workout.

- [ ] **Step 2: Run tests to verify they fail**

Run: `docker compose exec -T api pytest tests/services/test_proposal_apply.py -v`
Expected: FAIL — `ModuleNotFoundError: app.services.proposal_apply`.

- [ ] **Step 3: Implement the shared service**

`app/services/proposal_apply.py`:

```python
from __future__ import annotations

import uuid
from datetime import date
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

from app.models.agent import AgentMessage
from app.models.plan import Cycle, Plan
from app.models.workout import PlannedWorkout, WorkoutStatus


class ProposalNotFound(Exception):
    """Raised when no pending proposal matches the (proposal_id, athlete) pair."""


class ProposalApplyError(Exception):
    """Raised on an invalid choice/edit (maps to HTTP 400 at the route)."""


async def _owned_workout(
    db: AsyncSession, athlete_id: uuid.UUID, workout_id: uuid.UUID
) -> PlannedWorkout | None:
    return (
        await db.execute(
            select(PlannedWorkout)
            .join(Cycle, PlannedWorkout.cycle_id == Cycle.id)
            .join(Plan, Cycle.plan_id == Plan.id)
            .where(PlannedWorkout.id == workout_id, Plan.athlete_id == athlete_id)
        )
    ).scalar_one_or_none()


async def apply_proposal(
    db: AsyncSession,
    athlete_id: uuid.UUID,
    proposal_id: uuid.UUID,
    choice: str,
) -> None:
    """Apply or cancel a proposal. Looks proposals up by proposal_id scoped to the
    athlete (NOT by workout_id). Re-validates every edit's workout_id against the
    athlete before mutating — never trusts LLM-emitted IDs (spec §3.2)."""
    msg = (
        await db.execute(
            select(AgentMessage).where(
                AgentMessage.athlete_id == athlete_id,
                AgentMessage.proposal_state_json["proposal_id"].as_string() == str(proposal_id),
            )
        )
    ).scalar_one_or_none()
    if msg is None:
        raise ProposalNotFound(f"Proposal {proposal_id} not found for athlete")

    proposal: dict[str, Any] = msg.proposal_state_json

    if choice == "cancel":
        proposal["state"] = "discarded"
        flag_modified(msg, "proposal_state_json")
        # reschedule_original cleanup parity: delete the orphaned shadow workout.
        if proposal.get("created_by") == "reschedule_original" and msg.related_workout_id:
            orphan = await _owned_workout(db, athlete_id, msg.related_workout_id)
            if orphan is not None:
                await db.delete(orphan)
        await db.commit()
        return

    # just_move: move the lead/related workout to the proposal's new_date.
    if choice == "just_move":
        new_date_str = proposal.get("new_date")
        if new_date_str is None or msg.related_workout_id is None:
            raise ProposalApplyError("just_move requires new_date + related workout")
        lead = await _owned_workout(db, athlete_id, msg.related_workout_id)
        if lead is None:
            raise ProposalApplyError("Lead workout not found or not owned by athlete")
        lead.scheduled_date = date.fromisoformat(new_date_str)
        lead.status = WorkoutStatus.moved
        proposal["state"] = "applied"
        proposal["applied_choice"] = "just_move"
        flag_modified(msg, "proposal_state_json")
        await db.commit()
        return

    if choice not in ("option_a", "option_b"):
        raise ProposalApplyError(f"Invalid choice: {choice}")

    chosen = next((o for o in proposal.get("options", []) if o["id"] == choice), None)
    if chosen is None:
        raise ProposalApplyError("Option not found in proposal")

    for edit in chosen.get("edits", []):
        field = edit["field"]
        if field not in ("scheduled_date", "status"):
            raise ProposalApplyError(f"Invalid edit field: {field}")
        try:
            edit_workout_id = uuid.UUID(edit["workout_id"])
        except (KeyError, ValueError) as e:
            raise ProposalApplyError("Invalid workout_id in edit") from e

        # SECURITY (§3.2): re-validate ownership before mutating. Never trust LLM IDs.
        target = await _owned_workout(db, athlete_id, edit_workout_id)
        if target is None:
            raise ProposalApplyError(
                f"Workout {edit_workout_id} not found or not owned by athlete"
            )

        value = edit["new_value"]
        if field == "scheduled_date":
            target.scheduled_date = date.fromisoformat(value)
            target.status = WorkoutStatus.moved
        else:  # status
            if value not in {"planned", "moved", "skipped"}:
                raise ProposalApplyError(f"Invalid status value: {value}")
            target.status = WorkoutStatus(value)

    proposal["state"] = "applied"
    proposal["applied_choice"] = choice
    flag_modified(msg, "proposal_state_json")
    await db.commit()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `docker compose exec -T api pytest tests/services/test_proposal_apply.py -v`
Expected: PASS (4 passed).

- [ ] **Step 5: Commit**

```bash
git add app/services/proposal_apply.py tests/services/test_proposal_apply.py
git commit -m "feat(chat): shared proposal_apply service with athlete ownership re-validation"
```

### Task D2: Refactor `apply-move` to delegate to the shared service

**Files:**
- Modify: `app/routes/workouts.py:257-366`

Keep the route's workout_id 404 check and `invalidate_for_athlete` call. Replace the inline apply/cancel body with a call to `apply_proposal`, mapping `ProposalNotFound` → 404 and `ProposalApplyError` → 400. This preserves the existing `apply-move` contract while routing through one code path. **Regression gate: the existing `tests/.../test_apply_move*` suite must still pass unchanged.**

- [ ] **Step 1: Find the existing apply-move tests**

Run: `docker compose exec -T api pytest -k apply_move -v`
Expected: existing apply-move tests PASS (baseline before refactor).

- [ ] **Step 2: Add imports**

In `app/routes/workouts.py`, add near the other service imports (top of file):

```python
from app.services.proposal_apply import (
    ProposalApplyError,
    ProposalNotFound,
    apply_proposal,
)
```

- [ ] **Step 3: Replace the apply_move body**

Replace the body of `apply_move` (everything after the workout 404 check, `app/routes/workouts.py:264` onward) with:

```python
    # 1. Workout 404 check (preserves the route's existing contract).
    result = await db.execute(
        select(PlannedWorkout)
        .join(Cycle, PlannedWorkout.cycle_id == Cycle.id)
        .join(Plan, Cycle.plan_id == Plan.id)
        .where(PlannedWorkout.id == workout_id, Plan.athlete_id == athlete.id)
    )
    if result.scalar_one_or_none() is None:
        raise HTTPException(status_code=404, detail="Workout not found")

    # 2. Delegate apply/cancel to the shared service (ownership re-validated within).
    try:
        await apply_proposal(db, athlete.id, body.proposal_id, body.choice)
    except ProposalNotFound:
        raise HTTPException(status_code=404, detail="Proposal not found") from None
    except ProposalApplyError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    invalidate_for_athlete(athlete.id)
    return {"ok": True}
```

> **Note on `just_move`:** the drag flow's proposal carries `new_date` and `related_workout_id`, so `proposal_apply.just_move` handles it. Confirm the drag proposal (`plan_adapter.propose_rebalance`) sets `new_date` in `proposal_state_json` — it does (line 222-227 of `plan_adapter.py`). The shared service reads `proposal["new_date"]`; for chat proposals (no `new_date`), `just_move` is not offered by the chat UI, so this path is drag-only.

- [ ] **Step 4: Run the apply-move regression suite**

Run: `docker compose exec -T api pytest -k apply_move -v`
Expected: PASS — all existing apply-move tests still green.

- [ ] **Step 5: Commit**

```bash
git add app/routes/workouts.py
git commit -m "refactor(chat): apply-move delegates to shared proposal_apply service"
```

---

## Phase E — Chat routes

### Task E1: Implement `GET /chat`, `POST /chat`, `POST /chat/proposal/apply`

**Files:**
- Modify: `app/routes/chat.py`
- Test: `tests/routes/test_chat.py`

`POST /chat` runs a turn; wraps `run_turn` in try/except — missing key → 503, Gemini failure → 502 (both CORS-safe). `GET /chat` returns the chronological `user_chat` thread with pagination. `POST /chat/proposal/apply` delegates to `apply_proposal`.

- [ ] **Step 1: Write the failing tests**

`tests/routes/test_chat.py`:

```python
from unittest.mock import MagicMock, patch

import pytest

from app.services.agents import coach_chat


def _text_response(text):
    part = MagicMock(); part.function_call = None; part.text = text
    cand = MagicMock(); cand.content.parts = [part]
    resp = MagicMock(); resp.candidates = [cand]
    return resp


@pytest.mark.asyncio
async def test_post_chat_returns_reply(client, auth_headers):
    fake = MagicMock()
    fake.models.generate_content.return_value = _text_response("Keep it up.")
    with patch.object(coach_chat, "get_gemini_client", return_value=fake):
        r = await client.post("/chat", json={"message": "hi"}, headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["reply_md"] == "Keep it up."


@pytest.mark.asyncio
async def test_post_chat_gemini_failure_is_502(client, auth_headers):
    fake = MagicMock()
    fake.models.generate_content.side_effect = RuntimeError("gemini down")
    with patch.object(coach_chat, "get_gemini_client", return_value=fake):
        r = await client.post("/chat", json={"message": "hi"}, headers=auth_headers)
    assert r.status_code == 502


@pytest.mark.asyncio
async def test_post_chat_missing_key_is_503(client, auth_headers, monkeypatch):
    from app.config import settings
    monkeypatch.setattr(settings, "gemini_api_key", "")
    r = await client.post("/chat", json={"message": "hi"}, headers=auth_headers)
    assert r.status_code == 503


@pytest.mark.asyncio
async def test_get_chat_returns_thread_chronological(client, auth_headers):
    fake = MagicMock()
    fake.models.generate_content.return_value = _text_response("Reply one.")
    with patch.object(coach_chat, "get_gemini_client", return_value=fake):
        await client.post("/chat", json={"message": "first"}, headers=auth_headers)
    r = await client.get("/chat", headers=auth_headers)
    assert r.status_code == 200
    msgs = r.json()["messages"]
    assert [m["role"] for m in msgs] == ["user", "assistant"]
    assert msgs[0]["content_md"] == "first"
```

> **Fixture note:** `client` (httpx AsyncClient) and `auth_headers` already power the other route tests in `tests/routes/`. Reuse them.

- [ ] **Step 2: Run tests to verify they fail**

Run: `docker compose exec -T api pytest tests/routes/test_chat.py -v`
Expected: FAIL — current stubs return 501.

- [ ] **Step 3: Implement the routes**

Replace `app/routes/chat.py` entirely:

```python
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.deps import get_current_athlete, get_db
from app.models.agent import AgentKind, AgentMessage, MessageRole
from app.models.athlete import Athlete
from app.schemas.chat import (
    ChatHistoryOut,
    ChatMessageOut,
    ChatProposalApplyRequest,
    PostChatRequest,
    PostChatResponse,
)
from app.services.agents import coach_chat
from app.services.cache_invalidation import invalidate_for_athlete
from app.services.proposal_apply import (
    ProposalApplyError,
    ProposalNotFound,
    apply_proposal,
)

router = APIRouter(prefix="/chat", tags=["chat"])


@router.get("", response_model=ChatHistoryOut)
async def get_chat(
    limit: int = Query(default=50, ge=1, le=200),
    before: uuid.UUID | None = Query(default=None),
    athlete: Athlete = Depends(get_current_athlete),
    db: AsyncSession = Depends(get_db),
):
    q = (
        select(AgentMessage)
        .where(
            AgentMessage.athlete_id == athlete.id,
            AgentMessage.agent == AgentKind.user_chat,
        )
        .order_by(AgentMessage.created_at.desc())
        .limit(limit)
    )
    if before is not None:
        anchor = (
            await db.execute(select(AgentMessage).where(AgentMessage.id == before))
        ).scalar_one_or_none()
        if anchor is not None:
            q = q.where(AgentMessage.created_at < anchor.created_at)
    rows = list(reversed((await db.execute(q)).scalars().all()))

    return ChatHistoryOut(
        messages=[
            ChatMessageOut(
                id=m.id,
                role=m.role.value,
                content_md=m.content_md,
                created_at=m.created_at,
                proposal=m.proposal_state_json if m.proposal_state_json else None,
            )
            for m in rows
        ]
    )


@router.post("", response_model=PostChatResponse)
async def post_chat(
    body: PostChatRequest,
    athlete: Athlete = Depends(get_current_athlete),
    db: AsyncSession = Depends(get_db),
):
    if not settings.gemini_api_key:
        raise HTTPException(status_code=503, detail="Coach unavailable — GEMINI_API_KEY not set")
    try:
        result = await coach_chat.run_turn(db, athlete.id, body.message)
    except HTTPException:
        raise
    except Exception as e:  # noqa: BLE001 — convert to CORS-safe 502
        raise HTTPException(status_code=502, detail="Coach failed to respond") from e

    if result.proposal is not None:
        invalidate_for_athlete(athlete.id)  # a proposal row was written
    return PostChatResponse(reply_md=result.reply_md, proposal=result.proposal)


@router.post("/proposal/apply")
async def apply_chat_proposal(
    body: ChatProposalApplyRequest,
    athlete: Athlete = Depends(get_current_athlete),
    db: AsyncSession = Depends(get_db),
):
    try:
        await apply_proposal(db, athlete.id, body.proposal_id, body.choice)
    except ProposalNotFound:
        raise HTTPException(status_code=404, detail="Proposal not found") from None
    except ProposalApplyError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    invalidate_for_athlete(athlete.id)
    return {"ok": True}
```

> **CORS-safe note:** the broad `except Exception → 502` is intentional per CLAUDE.md — a raw 500 skips FastAPI's CORS middleware and the browser reports a phantom "CORS error." `HTTPException` re-raise keeps the 503/already-typed paths intact.

- [ ] **Step 4: Confirm the router is registered**

Verify `app/main.py` includes `chat.router` (the stub was already wired). If not, add `app.include_router(chat.router)`.

Run: `docker compose exec -T api pytest tests/routes/test_chat.py -v`
Expected: PASS (4 passed).

- [ ] **Step 5: Full backend suite (no regressions)**

Run: `docker compose exec -T api pytest`
Expected: all green.

- [ ] **Step 6: Commit**

```bash
git add app/routes/chat.py tests/routes/test_chat.py
git commit -m "feat(chat): GET/POST /chat + /chat/proposal/apply routes"
```

---

## Phase F — Mobile

### Task F1: Add markdown lib + chat types

**Files:**
- Modify: `mobile/package.json`
- Modify: `mobile/src/api/types.ts:153` (after the move-flow types)

- [ ] **Step 1: Install the markdown renderer**

Run: `cd mobile && npm install react-native-markdown-display`
Expected: added to `dependencies`.

- [ ] **Step 2: Add chat types**

In `mobile/src/api/types.ts`, after the `ApplyMoveRequest` block:

```typescript
// chat
export interface ChatMessageOut {
  id: UUID;
  role: 'user' | 'assistant';
  content_md: string;
  created_at: IsoDateTime;
  proposal: ProposalOut | null;
}
export interface ChatHistoryOut {
  messages: ChatMessageOut[];
}
export interface PostChatRequest {
  message: string;
}
export interface PostChatResponse {
  reply_md: string;
  proposal: ProposalOut | null;
}
export interface ChatProposalApplyRequest {
  proposal_id: UUID;
  choice: ApplyChoice;
}
```

- [ ] **Step 3: Typecheck**

Run: `cd mobile && npx tsc --noEmit`
Expected: clean.

- [ ] **Step 4: Commit**

```bash
git add mobile/package.json mobile/package-lock.json mobile/src/api/types.ts
git commit -m "feat(chat-mobile): markdown lib + chat types"
```

### Task F2: Chat API hooks

**Files:**
- Create: `mobile/src/api/hooks/useChat.ts`

- [ ] **Step 1: Write the hooks**

`mobile/src/api/hooks/useChat.ts`:

```typescript
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { api } from '@/api/client';
import type {
  ApplyChoice,
  ChatHistoryOut,
  PostChatResponse,
} from '@/api/types';

export function useChatHistory() {
  return useQuery({
    queryKey: ['chat', 'history'],
    queryFn: async () => (await api.get<ChatHistoryOut>('/chat')).data,
  });
}

export function useSendChat() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (message: string) => {
      const res = await api.post<PostChatResponse>('/chat', { message });
      return res.data;
    },
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ['chat', 'history'] });
    },
  });
}

export function useApplyChatProposal() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (vars: { proposalId: string; choice: ApplyChoice }) => {
      await api.post('/chat/proposal/apply', {
        proposal_id: vars.proposalId,
        choice: vars.choice,
      });
    },
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ['plan'] });
      void qc.invalidateQueries({ queryKey: ['chat', 'history'] });
    },
  });
}
```

- [ ] **Step 2: Typecheck**

Run: `cd mobile && npx tsc --noEmit`
Expected: clean.

- [ ] **Step 3: Commit**

```bash
git add mobile/src/api/hooks/useChat.ts
git commit -m "feat(chat-mobile): useChatHistory / useSendChat / useApplyChatProposal"
```

### Task F3: ChatBubble component

**Files:**
- Create: `mobile/src/components/ChatBubble.tsx`

- [ ] **Step 1: Write the component**

`mobile/src/components/ChatBubble.tsx`:

```tsx
import { View } from 'react-native';
import Markdown from 'react-native-markdown-display';

import { colors, fonts } from '@/theme/tokens';

interface Props {
  role: 'user' | 'assistant';
  contentMd: string;
}

export function ChatBubble({ role, contentMd }: Props) {
  const isUser = role === 'user';
  return (
    <View
      style={{
        alignSelf: isUser ? 'flex-end' : 'flex-start',
        maxWidth: '85%',
        marginVertical: 4,
        marginHorizontal: 12,
        padding: 12,
        backgroundColor: isUser ? colors.bgPanel : colors.bg,
        borderWidth: 2,
        borderColor: isUser ? colors.accentRun : colors.line,
      }}
    >
      <Markdown
        style={{
          body: { color: colors.ink, fontFamily: fonts.body, fontSize: 16, lineHeight: 22 },
          strong: { fontFamily: fonts.monoBold, color: colors.ink },
          link: { color: colors.accentRun },
          code_inline: { fontFamily: fonts.mono, color: colors.accentRun },
        }}
      >
        {contentMd}
      </Markdown>
    </View>
  );
}
```

> **Theme note:** confirm `colors.bgPanel`, `colors.bg`, `colors.accentRun`, `colors.line`, `colors.ink` and `fonts.body/mono/monoBold` exist in `mobile/src/theme/tokens.ts` (they are used by `ProposalSheet.tsx`). Reuse the same token names.

- [ ] **Step 2: Typecheck**

Run: `cd mobile && npx tsc --noEmit`
Expected: clean.

- [ ] **Step 3: Commit**

```bash
git add mobile/src/components/ChatBubble.tsx
git commit -m "feat(chat-mobile): ChatBubble with markdown rendering"
```

### Task F4: ChatScreen + wire the tab; delete the placeholder

**Files:**
- Create: `mobile/src/screens/ChatScreen.tsx`
- Modify: `mobile/src/navigation/RootNavigator.tsx:6,104`
- Delete: `mobile/src/screens/ChatPlaceholderScreen.tsx`

The screen: message list (history + optimistic in-flight), keyboard-avoiding input bar, send button; when an assistant reply carries a `proposal`, show a "Review proposal" affordance that opens the existing `ProposalSheet`; apply routes through `useApplyChatProposal`. Empty/loading/error states.

- [ ] **Step 1: Write the screen**

`mobile/src/screens/ChatScreen.tsx`:

```tsx
import BottomSheet from '@gorhom/bottom-sheet';
import { useCallback, useRef, useState } from 'react';
import {
  ActivityIndicator,
  FlatList,
  KeyboardAvoidingView,
  Platform,
  Pressable,
  TextInput,
  View,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { useApplyChatProposal, useChatHistory, useSendChat } from '@/api/hooks/useChat';
import type { ApplyChoice, ChatMessageOut, ProposalOut } from '@/api/types';
import { ChatBubble } from '@/components/ChatBubble';
import { ProposalSheet } from '@/components/ProposalSheet';
import { RetroButton } from '@/components/retro/RetroButton';
import { colors, fonts } from '@/theme/tokens';

export function ChatScreen() {
  const history = useChatHistory();
  const send = useSendChat();
  const applyProposal = useApplyChatProposal();
  const sheetRef = useRef<BottomSheet>(null);

  const [input, setInput] = useState('');
  const [activeProposal, setActiveProposal] = useState<ProposalOut | null>(null);

  const onSend = useCallback(async () => {
    const text = input.trim();
    if (!text || send.isPending) return;
    setInput('');
    const res = await send.mutateAsync(text);
    if (res.proposal) {
      setActiveProposal(res.proposal);
      sheetRef.current?.expand();
    }
  }, [input, send]);

  const onApply = useCallback(
    async (choice: ApplyChoice) => {
      if (!activeProposal) return;
      await applyProposal.mutateAsync({ proposalId: activeProposal.proposal_id, choice });
      setActiveProposal(null);
      sheetRef.current?.close();
    },
    [activeProposal, applyProposal],
  );

  const onCancel = useCallback(async () => {
    if (activeProposal) {
      await applyProposal.mutateAsync({
        proposalId: activeProposal.proposal_id,
        choice: 'cancel',
      });
    }
    setActiveProposal(null);
    sheetRef.current?.close();
  }, [activeProposal, applyProposal]);

  const renderItem = useCallback(
    ({ item }: { item: ChatMessageOut }) => (
      <View>
        <ChatBubble role={item.role} contentMd={item.content_md} />
        {item.proposal && item.proposal.state === 'pending' && (
          <View style={{ marginHorizontal: 12, marginBottom: 8, alignSelf: 'flex-start' }}>
            <RetroButton
              label="Review proposal"
              tone="primary"
              onPress={() => {
                setActiveProposal(item.proposal);
                sheetRef.current?.expand();
              }}
            />
          </View>
        )}
      </View>
    ),
    [],
  );

  return (
    <SafeAreaView className="flex-1 bg-bg" edges={['top']}>
      <KeyboardAvoidingView
        style={{ flex: 1 }}
        behavior={Platform.OS === 'ios' ? 'padding' : undefined}
      >
        {history.isLoading ? (
          <View style={{ flex: 1, alignItems: 'center', justifyContent: 'center' }}>
            <ActivityIndicator color={colors.accentRun} />
          </View>
        ) : (
          <FlatList
            data={history.data?.messages ?? []}
            keyExtractor={(m) => m.id}
            renderItem={renderItem}
            contentContainerStyle={{ paddingVertical: 12 }}
          />
        )}

        <View
          style={{
            flexDirection: 'row',
            padding: 12,
            borderTopWidth: 2,
            borderColor: colors.line,
            alignItems: 'flex-end',
          }}
        >
          <TextInput
            value={input}
            onChangeText={setInput}
            placeholder="Ask your coach…"
            placeholderTextColor={colors.inkDim}
            multiline
            style={{
              flex: 1,
              color: colors.ink,
              fontFamily: fonts.body,
              fontSize: 16,
              maxHeight: 120,
              borderWidth: 2,
              borderColor: colors.line,
              padding: 10,
              marginRight: 8,
            }}
          />
          <Pressable
            onPress={() => void onSend()}
            disabled={send.isPending || !input.trim()}
            style={{ paddingVertical: 12, paddingHorizontal: 14, backgroundColor: colors.accentRun }}
          >
            {send.isPending ? (
              <ActivityIndicator color={colors.bg} />
            ) : (
              <View />
            )}
          </Pressable>
        </View>
      </KeyboardAvoidingView>

      <ProposalSheet
        ref={sheetRef}
        proposal={activeProposal}
        submitting={applyProposal.isPending}
        onApply={onApply}
        onCancel={onCancel}
      />
    </SafeAreaView>
  );
}
```

> **Send button glyph:** the `<View />` placeholder inside the Pressable is intentional — replace with the project's send icon/text per existing button conventions (e.g. a `Text` glyph like `▸`). Keep it minimal; this is the only cosmetic decision left to the implementer.

- [ ] **Step 2: Wire the tab to the new screen**

In `mobile/src/navigation/RootNavigator.tsx`:
- Line 6: change `import { ChatPlaceholderScreen } from '@/screens/ChatPlaceholderScreen';` → `import { ChatScreen } from '@/screens/ChatScreen';`
- Line 104: change `component={ChatPlaceholderScreen}` → `component={ChatScreen}`

- [ ] **Step 3: Delete the placeholder**

Run: `rm mobile/src/screens/ChatPlaceholderScreen.tsx`

- [ ] **Step 4: Typecheck**

Run: `cd mobile && npx tsc --noEmit`
Expected: clean (no dangling import of the deleted placeholder).

- [ ] **Step 5: Regenerate the OpenAPI types**

Run the existing export script to keep `mobile/src/api/openapi-generated.ts` current with the new `/chat` schemas:

Run: `bash scripts/export_openapi.sh && cd mobile && npm run gen-types`
Expected: `openapi-generated.ts` updates; typecheck still clean. (If the project's gen flow differs, follow the header comment in `mobile/src/api/types.ts`.)

- [ ] **Step 6: Commit**

```bash
git add mobile/src/screens/ChatScreen.tsx mobile/src/navigation/RootNavigator.tsx mobile/src/api/openapi-generated.ts
git rm mobile/src/screens/ChatPlaceholderScreen.tsx
git commit -m "feat(chat-mobile): ChatScreen replaces placeholder; reuse ProposalSheet"
```

---

## Phase G — Verification + close-out

### Task G1: Full verification

- [ ] **Step 1: Full backend suite in the container**

Run: `docker compose exec -T api pytest`
Expected: all green, including the apply-move regression suite.

- [ ] **Step 2: Mobile typecheck**

Run: `cd mobile && npx tsc --noEmit`
Expected: clean.

- [ ] **Step 3: Manual smoke (web + iPhone PWA)** — per CLAUDE.md PWA caveats:
  - Bubbles render; markdown (bold/lists/links) renders on web and native.
  - Send works; loading state shows; empty state on a fresh thread.
  - A proposal reply shows "Review proposal"; tapping opens `ProposalSheet` (bottom-sheet gesture works on touch-web).
  - Applying an option refreshes the plan (week/today reflect the move).
  - Cancel marks the proposal discarded and closes the sheet.
  - Force a 502 (bad key) → app surfaces an error, not a phantom CORS failure.

- [ ] **Step 4: Set the prod env var**

Confirm `GEMINI_API_KEY` is set as a **Railway backend env var** (NOT `EXPO_PUBLIC_*`). Confirm `GEMINI_MODEL` is unset (defaults to `gemini-2.5-flash`) or set intentionally.

### Task G2: Session close-out (per global CLAUDE.md protocol)

- [ ] Update project `CLAUDE.md` with any Gemini/google-genai gotchas discovered (e.g. response-parts shape, function-call extraction).
- [ ] Update `PROJECT_TRACKER.md` — add the Coach Chat epic entry + commits.
- [ ] Update `MEMORY.md` current status.
- [ ] Run `/update-notion` to sync project status.

---

## Self-Review

**Spec coverage:**
- §3.1 Gemini client / config / dep → A1, A2. ✓
- §3.1 `build_athlete_context` (snapshot + markdown) → B1. ✓
- §3.1 `coach_chat.run_turn` → C2. ✓
- §3.1 `GET`/`POST /chat` routes → E1. ✓
- §3.2 `propose_plan_change` mirroring `proposal_state_json` → A2 (declaration) + C2 (build proposal_state). ✓
- §3.2 shared apply service + ownership re-validation + both routes wired → D1, D2, E1. ✓
- §3.2 **security requirement** (re-validate every edit's workout_id) → D1 (`_owned_workout` per edit) + dedicated test `test_apply_rejects_foreign_workout_id`. ✓
- §3.3 mobile ChatScreen + hooks + ProposalSheet reuse + openapi regen + types → F1–F4. ✓
- §4 living context contents (plan/philosophy/cycle, KPIs, today+week, recent actuals) → B1. ✓
- §5 prompt template / persona / guardrails → A2 (system prompt) + C2 (`_build_prompt`). ✓
- §7 error handling: 502 Gemini (CORS-safe), 503 missing key, no-plan minimal context → E1 + B1. ✓
- §7 input bounds (message length, history cap) → C1 (`max_length=4000`) + C2 (`HISTORY_LIMIT=20`). ✓
- §8 tests: context shape, two-row persist, proposal branch, 502, 503, GET order → B1/C2/E1. ✓
- §10 three open questions → resolved in the header (caching OFF, keep-and-mark, react-native-markdown-display). ✓

**Type consistency:** `AthleteContext.snapshot/markdown` (B1) consumed in C2; `ChatTurnResult.reply_md/proposal` (C2) consumed in E1; `apply_proposal(db, athlete_id, proposal_id, choice)` signature identical in D1/D2/E1; `ProposalNotFound`/`ProposalApplyError` defined in D1, caught in D2/E1; `ProposalOut`/`ApplyChoice` mobile types reused from existing `types.ts`. ✓

**Placeholder scan:** every code step contains full code; the only two implementer-discretion notes (send-button glyph, fixture reuse) are explicitly flagged with concrete guidance, not "TODO". ✓
