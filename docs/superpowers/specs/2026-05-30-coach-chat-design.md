# Coach Chat — Design Spec

**Date:** 2026-05-30
**Status:** Approved (brainstorming) → ready for implementation plan
**Author:** Session 3 (coach chat)

## 1. Summary

A free-form conversational running coach on the **Chat tab**, powered by **Google
Gemini**. The coach has live context on the athlete's program and progress, holds a
single persistent conversation thread, gives advice, and can **propose plan changes**
that flow through the app's *existing* proposal → apply machinery.

Chosen during brainstorming:

| Decision | Choice | Rationale |
|----------|--------|-----------|
| LLM provider | **Google Gemini** | Large context window + low cost; good fit for injecting a rich athlete-context block every turn. |
| Coach powers | **Advice + propose plan changes** | Reuses the existing `proposal_state_json` / `ProposalSheet` / `apply-move` loop. |
| Living context | **Auto-assembled from live DB each turn** | Always fresh, zero manual upkeep. |
| History | **Persistent single thread** | Stored in `agent_messages` (`agent=user_chat`); coach remembers prior chats. |
| Integration | **Reuse proposal contract** | Chat proposals write the same `proposal_state_json` shape; the Anthropic drag-rebalance flow is left untouched. |

**Single-athlete simplification:** there is exactly one athlete. The `user_chat` thread
is simply *all* `agent_messages` rows with `agent=user_chat`. The `athlete_id` FK is
retained (it already exists and is free), but there is no multi-tenant logic to build.

## 2. Existing foundation (already in the codebase)

- **`agent_messages` table** (`app/models/agent.py`) — `AgentKind` enum already includes
  `user_chat`; `MessageRole` (system/user/assistant); columns `content_md`,
  `context_snapshot_json` (JSONB), `proposal_state_json` (JSONB), `related_workout_id`,
  `related_reconciliation_id`, `created_at`. No schema migration required.
- **Stubs to implement:** `app/routes/chat.py` (returns 501), and
  `app/services/agent_context.py:build_athlete_context()` (raises `NotImplementedError`).
- **Working proposal loop (reuse target):** dragging a workout calls
  `app/services/agents/plan_adapter.py:propose_rebalance()` (Anthropic Claude + tool-use),
  persists an `AgentMessage` with `proposal_state_json`, surfaces the mobile `ProposalSheet`,
  and applies via `POST /workouts/{workout_id}/apply-move` (`app/routes/workouts.py`). Note
  the existing route matches the proposal on **both** `related_workout_id == workout_id`
  **and** `proposal_id`; the new shared apply service (see §3.2) instead looks proposals up
  **by `proposal_id` alone, scoped to the athlete** so chat proposals (which have no
  workout-scoped route) apply through the same path.
- **Context source aggregators (reuse for `build_athlete_context`):**
  `app/services/plan_aggregator.py` (`build_plan_stats`, `build_plan_full`) and
  `app/routes/plan.py` helpers (`_build_plan_current`, today/week queries, `_build_coach_brief`).
- **Mobile placeholder:** `mobile/src/screens/ChatPlaceholderScreen.tsx` (to be replaced).
- **Heuristic `coach_brief.py`** is a *separate* feature (Today-screen 1-3 sentence brief);
  it is NOT the chat and is out of scope here.

## 3. Architecture & components

### 3.1 Backend (new + implemented)

- **`app/services/llm/gemini_client.py`** *(new)* — thin async Gemini client wrapper,
  separated for test mocking (mirrors `plan_adapter.get_anthropic_client()`). Reads
  `settings.gemini_api_key`. Default model **`gemini-2.5-flash`** (configurable via
  `settings.gemini_model` / `GEMINI_MODEL`).
  Declares the `propose_plan_change` function/tool. Uses Gemini **context caching** for the
  static system prompt + plan philosophy where available.
- **`app/services/agent_context.py`** *(implement stub)* —
  `build_athlete_context(db, athlete_id) -> AthleteContext` returns:
  - `snapshot: dict` — structured data, persisted to `context_snapshot_json` for audit.
  - `markdown: str` — compact rendered block injected into the prompt.
  Assembled from the existing aggregators (see §4). May reuse the existing short-TTL plan
  caches; no new caching layer required for v1.
- **`app/services/agents/coach_chat.py`** *(new)* — the turn engine `run_turn(db, athlete_id, message) -> ChatTurnResult`:
  1. `build_athlete_context()`.
  2. Persist the user `AgentMessage` (`agent=user_chat`, `role=user`, `context_snapshot_json=snapshot`).
  3. Load recent history (last ~20 `user_chat` messages, chronological).
  4. Call Gemini: `system` + context markdown + history + user message, with
     `propose_plan_change` declared.
  5. Branch:
     - **Function call** → build `proposal_state_json` (same shape as `plan_adapter`),
       persist assistant `AgentMessage` with the proposal, return `{reply_md, proposal}`.
     - **Plain text** → persist assistant `AgentMessage`, return `{reply_md}`.
- **`app/routes/chat.py`** *(implement stubs)*:
  - `GET /chat?limit=&before=` → paginated `user_chat` thread (chronological), newest-last.
  - `POST /chat` `{ "message": str }` → runs a turn, returns `{ reply_md, proposal? }`.
- **`app/config.py`** — add `gemini_api_key: str = ""` and `gemini_model: str = "gemini-2.5-flash"`.
- **Dependencies** — add `google-genai` to `pyproject.toml`.

### 3.2 Proposal reuse (the "advice + propose" path)

- The `propose_plan_change` Gemini function mirrors the established `proposal_state_json`
  contract: `summary`, `options[]` each with `id`, `label`, `tradeoff`, `rationale`, and
  `edits[]` of `{workout_id, field ∈ {scheduled_date, status}, new_value}`.
- On a function call, `coach_chat` persists a proposal `AgentMessage`
  (`agent=user_chat`, `role=assistant`, `proposal_state_json={...,state:"pending"}`,
  `related_workout_id` = the lead edited workout) — exactly as `plan_adapter` does.
- **Apply path (plan-phase decision):** `apply-move` is currently path-scoped as
  `POST /workouts/{workout_id}/apply-move` and finds the proposal by `proposal_id`. Two
  options, to be settled in the implementation plan:
  **Decided:** factor the apply/cancel core out of `apply-move` into a shared service
  function (e.g. `app/services/proposal_apply.py`) and call it from both the existing
  `POST /workouts/{workout_id}/apply-move` and a new thin
  `POST /chat/proposal/apply` `{proposal_id, choice}`. Avoids duplicating the
  proposal-state transition logic and keeps chat proposals off the workout-scoped route.

- **Security requirement (from the Session 3 audit — non-negotiable):** the shared
  apply/cancel service MUST re-validate every edit's `workout_id` against the current
  athlete (`Plan.athlete_id == athlete.id`) before applying — never trust workout IDs
  emitted by the LLM. Proposals reference workouts the model chose; the server is the
  authority. This makes prompt-injection-to-data-mutation a non-issue even though the user
  also approves via `ProposalSheet`. The existing `apply-move` already does this per-edit
  ownership join (`app/routes/workouts.py`); the refactor MUST preserve it unchanged in the
  shared service and apply it identically on the `POST /chat/proposal/apply` path.

### 3.3 Mobile

- **Replace** `ChatPlaceholderScreen.tsx` with **`ChatScreen.tsx`**:
  - Message list — user/assistant bubbles, markdown rendering, auto-scroll to latest,
    keyboard-avoiding input bar with send button.
  - When an assistant reply carries a `proposal`, render a "Review proposal" affordance
    that opens the existing **`ProposalSheet`**; accept routes through the existing
    `useApplyMove` (or the new shared apply hook) → optimistic plan refresh.
  - Empty/loading/error states; respects the retro theme tokens.
- **API hooks** — `useChatHistory` (GET `/chat`) and `useSendChat` (POST `/chat`) following
  existing react-query patterns; regenerate `mobile/src/api/openapi-generated.ts` and add
  types to `mobile/src/api/types.ts`.
- **Validation gate:** `cd mobile && npx tsc --noEmit`.

## 4. Living context — `build_athlete_context`

Assembled fresh per turn (live DB; may use existing short-TTL plan caches). Contents:

- **Plan & philosophy:** plan name, `plan.philosophy_md`, active cycle (`race_name`,
  `race_date`, days-to-race, week X / total weeks, `peak_week_target`).
- **Progress KPIs** (from `build_plan_stats`): `on_plan_pct`, done/skipped counts,
  planned vs actual miles, `streak_days`, next milestone.
- **Today + this week:** today's prescribed workout(s); the current week's layout with
  per-day status (done/skipped/moved/upcoming).
- **Recent actuals:** last 7–14 days of Garmin-synced `CompletedWorkout` rows
  (distance, pace, avg HR).

Rendered to a compact markdown block (the `markdown` field) and also returned as the
structured `snapshot` dict, which is persisted to `context_snapshot_json` on the user turn.

**Token control:** history capped to ~last 20 messages; the context block is bounded by
construction. Gemini's large window comfortably absorbs both; context caching covers the
static prefix (system prompt + philosophy).

## 5. Initial prompt template

System prompt (literal text to be finalized in the plan; intent captured here):

- **Persona:** an experienced marathon coach for a 12-month, three-marathon plan; values
  *durability over peak fitness*; specific, data-referencing, encouraging, concise.
- **Capabilities:** may propose plan changes via the `propose_plan_change` function; must
  explain tradeoffs for any proposal; otherwise answers conversationally.
- **Guardrails:** no medical advice beyond general training guidance; defer to the athlete
  on injury/health; **never fabricate data** — reason only from the provided context block;
  if data is missing, say so.

First-turn assembly:

```
system:  <coach system prompt>
user:    Athlete context:
         <rendered markdown context block>
         ---
         <conversation history, last ~20 messages>
         ---
         <new user message>
```

(History turns after the first reuse the persisted thread; the context block is refreshed
each turn so the coach always sees current progress.)

## 6. Turn data flow

```
Mobile POST /chat {message}
  → route loads the athlete, calls coach_chat.run_turn
    → build_athlete_context()                  (live DB)
    → persist user AgentMessage (+context_snapshot_json)
    → load recent history (~20 msgs)
    → Gemini call (propose_plan_change declared)
      ├─ function_call → persist proposal AgentMessage → return {reply_md, proposal}
      └─ text          → persist assistant AgentMessage → return {reply_md}
  → mobile renders reply
    └─ if proposal → open ProposalSheet → apply via shared apply path
```

## 7. Error handling (follows project CLAUDE.md lessons)

- **Gemini API failure** → route-level `try/except` → `HTTPException(502)` so the response
  keeps CORS headers (the "5xx without CORS headers → browser blames CORS" gotcha). Nothing
  persisted for the assistant turn on failure (the user turn may remain, marked as having
  no reply, or be rolled back — decided in the plan).
- **Missing `GEMINI_API_KEY`** → `HTTPException(503)` "coach unavailable."
- **No active plan** → `build_athlete_context` returns a minimal context; the coach still
  chats and states that no plan is loaded.
- **Input bounds** → cap user message length; cap history window. (No per-user rate limit
  needed for a single athlete.)

## 8. Testing

- **Backend (container `pytest`):** mock the Gemini client (like `get_anthropic_client` is
  mockable). Cover: `build_athlete_context` snapshot/markdown shape; `run_turn` persists
  one user + one assistant row; proposal branch writes a valid `proposal_state_json`;
  Gemini error → 502; missing key → 503; GET `/chat` pagination/order.
- **Mobile:** `npx tsc --noEmit` gate (no jest infra) + manual smoke on web and iPhone PWA
  (bubbles render, markdown renders, send works, proposal opens `ProposalSheet`, apply works).

## 9. Out of scope / deferred

- Response **streaming** (v1 returns the full reply).
- `daily_coach` LLM morning brief and `run_analyst` (separate agents; heuristic
  `coach_brief.py` already serves the Today screen).
- **Multi-thread** / conversation management (single thread for v1).
- **Provider unification** — porting the Anthropic drag-rebalance (`plan_adapter`) to Gemini
  is deferred; the two providers coexist for now.

## 10. Resolved decisions & remaining plan-phase questions

**Resolved during brainstorming:**
- **Gemini model:** `gemini-2.5-flash` (default; tunable via `GEMINI_MODEL`).
- **Apply path:** shared apply/cancel service called from both `apply-move` and a new
  `POST /chat/proposal/apply` (see §3.2).

**Remaining for the implementation plan:**
1. Whether to enable Gemini **context caching** in v1 (static system prompt + philosophy).
2. **User-turn persistence on Gemini failure** — keep-and-mark vs. roll back.
3. **Mobile markdown renderer** — lightweight RN markdown lib vs. minimal custom renderer.
