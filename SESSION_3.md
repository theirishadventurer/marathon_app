# Session 3 — Daily Coach + Run Analyst + Chat + Polish

> **Paste this entire file into Claude Code as the opening message.**
> Read `SPEC.md`, `PLAN.md`, and skim `SESSION_1.md` and `SESSION_2.md`.
> Then propose your build order and **stop for confirmation before
> writing code.**
>
> **Prerequisite:** Sessions 1 and 2 done. Backend has Plan Adapter
> working. Mobile app has drag-to-move working end-to-end.

---

## Goal

By the end of this session:

1. Tomorrow at 6am local time, a fresh Daily Coach brief shows up on
   the Today screen
2. After my next Garmin sync that matches a planned workout, the Run
   Analyst writes a 1-paragraph review I can read on the Workout Detail
   screen
3. I can have a free-form chat with the coach in the Chat tab — it knows
   my training context and responds in the coach's voice
4. The app handles a Garmin auth failure gracefully (banner, reauth
   screen works)
5. Empty/loading/error states across all screens look intentional

This is the session that turns the app from "scaffolding" into "actually
useful."

---

## Scope: what you build

### Part A — The shared context builder (most important piece)

#### A1. `build_athlete_context()`

`app/services/agent_context.py` — fully implement:

```python
class AthleteContext(TypedDict):
    profile: AthleteProfileDict             # name, hr_zones, paces, injury_notes
    plan: PlanSummaryDict                   # name, philosophy_md, dates
    active_cycle: CycleSummaryDict          # name, race_date, week_number
    cycle_progress: dict                    # week N of M, days to race
    this_week: list[PlannedWorkoutDict]     # all 7 days
    last_14_days_completed: list[CompletedSummaryDict]
    last_14_days_metrics: list[DailyMetricDict]
    recent_reconciliations: list[ReconciliationDict]   # last 5 with reviews
    recent_chat: list[MessageDict]          # last 10 user_chat
    decision_rules: list[str]               # parsed from PLAN.md decision_rules
    today: date

async def build_athlete_context(db, athlete_id: UUID) -> AthleteContext: ...
```

Rules:
- Single function, single round-trip set of queries
- No Anthropic calls — this is data assembly only
- Returns plain dict-like data, JSON-serializable
- Each agent persists this snapshot in `agent_messages.context_snapshot_json`

#### A2. Refactor Plan Adapter to use shared context

Plan Adapter from session 2 used a focused context. Refactor it to use
`build_athlete_context()` plus its move-specific extras. This validates
the shared context works for the trickiest case.

---

### Part B — Daily Coach

#### B1. The agent

`app/services/agents/daily_coach.py`

```python
async def generate_daily_brief(db, athlete_id: UUID) -> AgentMessage: ...
```

- Builds athlete context
- Calls Anthropic with system prompt = coaching persona + plan philosophy
- User message: "Write today's brief covering: today's workout and why,
  notable trends from the last 14 days, one specific cue for execution,
  and any flags from recent recovery metrics."
- 2-3 paragraphs of output, markdown
- Persists to `agent_messages` with `agent='daily_coach'`,
  `role='assistant'`, today's `created_at`
- Idempotent for the same day — if a brief already exists for today,
  regenerate it (overwrite by inserting a new row with later timestamp;
  consumer always reads latest)

#### B2. Schedule it
- APScheduler job at 6am local time (config-driven timezone)
- Runs `generate_daily_brief` for the athlete
- Logs success/failure
- On failure, log but don't crash the scheduler

#### B3. Endpoint
- `GET /coach/today-brief` returns the latest `daily_coach` message for
  today's date
- If none exists yet (e.g., first run before 6am), trigger generation
  on-demand and return it

#### B4. Wire into mobile
- `TodayScreen.tsx` — replace placeholder with real brief
- Loading skeleton while fetching
- "Refresh brief" button (calls a `POST /coach/regenerate-brief` endpoint
  for ad-hoc regen; rate-limited to once per minute)
- Render markdown properly (use `react-native-markdown-display`)

---

### Part C — Run Analyst

#### C1. The agent

`app/services/agents/run_analyst.py`

```python
async def review_reconciliation(db, reconciliation_id: UUID) -> str: ...
```

- Takes a reconciliation row that has both `planned_id` and `completed_id`
- Builds athlete context
- Adds reconciliation-specific data: planned target details, actual
  metrics, deviation calculations
- Calls Anthropic with system prompt + structured comparison
- Output: 1 paragraph (4-6 sentences) of markdown
- Writes to `reconciliations.agent_review_md` and
  `reconciliations.agent_reviewed_at`
- Also persists in `agent_messages` with `related_reconciliation_id`

#### C2. Trigger
- After reconciler creates a new matched reconciliation, fire the
  Run Analyst
- For backfill: a one-off `POST /admin/review-pending` endpoint that
  reviews all reconciliations missing reviews

#### C3. Wire into mobile
- `WorkoutDetailScreen.tsx` — replace placeholder with real review
- Loading skeleton during fetch
- Markdown rendering

---

### Part D — Free-form chat

#### D1. The endpoint

```
POST /chat                {message: str}    → {reply: str, message_id: UUID}
GET  /chat?limit=50                          → list[MessageDict]
```

- Persists user message as `agent_messages` with `agent='user_chat'`,
  `role='user'`
- Builds athlete context + recent chat history (last 20 messages)
- Calls Anthropic with coaching system prompt
- Persists assistant reply with `role='assistant'`
- Returns reply

#### D2. The screen

`mobile/src/screens/ChatScreen.tsx`

- Vertical scrolling message list (FlashList, inverted)
- User messages right-aligned, coach left-aligned
- Markdown in assistant messages
- Text input at bottom, send button
- "Coach is thinking…" indicator during the API call (typing dots)
- Pull to top to load older messages
- Empty state with suggested prompts ("How should I approach this week?",
  "I had knee tightness yesterday — should I adjust?")

---

### Part E — Polish pass

#### E1. APScheduler in production
- Move Garmin sync from manual `/admin/sync` to APScheduler hourly
- Daily Coach scheduled at 6am
- Both jobs log success/failure
- Lifecycle: scheduler starts on FastAPI startup, shuts down cleanly
- Keep the `/admin/sync` endpoint for manual triggering

#### E2. Garmin failure UX
- `GET /garmin/status` already exists; surface it in mobile
- If `needs_reauth=true`:
  - Banner across top of Today screen ("Garmin needs reauthentication")
  - Banner is dismissable for the session but reappears next launch
  - Tapping banner opens Settings → Reauth flow
- If `last_sync` is >24h old (and not needs_reauth): subtle "last synced
  X hours ago" indicator
- Manual sync button in Settings always available

#### E3. Empty / loading / error states
Each screen gets:
- Loading: skeleton placeholders matching the final shape
- Empty: tasteful explainer + action ("No completed runs yet — go run
  something")
- Error: error message + retry button

#### E4. Pull-to-refresh on Today, Week, Workout Detail, Chat

#### E5. Sync state indicator
- Persistent small indicator (top of Today screen, near header) showing
  last sync time
- Tap to trigger manual sync
- Spinner while syncing

#### E6. Markdown rendering
- One shared `<Markdown>` component used everywhere
- Style hooks for: headers, bold, italic, lists, code spans, links,
  blockquotes
- Match app theme

---

## Out of scope (explicitly NOT this session)

- ❌ Push notifications (V2)
- ❌ Apple Health / Strava (V2)
- ❌ Multi-user
- ❌ Web app
- ❌ Pushing structured workouts to Garmin (Connect IQ)
- ❌ Race day live tracking
- ❌ Plan editing UI (creating new plans, editing the philosophy)

---

## Constraints

1. **All three agents share `build_athlete_context()`.** No per-agent
   context builders. If an agent needs something extra (Plan Adapter
   needs the proposed move), it adds to the shared base, doesn't replace
   it.
2. **Every agent call persists `context_snapshot_json`.** Whatever the
   agent saw, exactly. This is debugging gold — don't skip it.
3. **System prompts live in code, not env vars.** Each agent has its
   prompt at the top of its file.
4. **Anthropic calls use the current Sonnet model string.** Confirm the
   exact string at session start (search the docs if unsure — model
   strings change).
5. **No streaming yet.** Full response, then return. Streaming is V2.
6. **Token budgets are real.** Each agent call sends athlete context
   (~3-5K tokens) + system prompt + task. Watch context size on long
   chat histories — truncate user_chat history to last 20 messages, not
   all-time.
7. **Don't change `SPEC.md` or `PLAN.md`** without asking.

---

## Working style

1. Read `SPEC.md`, `PLAN.md`. Skim sessions 1 and 2.
2. Verify both prior sessions still work end-to-end.
3. Propose build order. I'd suggest:
   - Part A first (shared context — everything depends on it)
   - Part C second (Run Analyst — simplest, builds confidence)
   - Part B third (Daily Coach + scheduler)
   - Part D fourth (chat)
   - Part E last (polish)
4. Stop for confirmation. Then build.
5. Commit per part.
6. Test on real iPhone, not simulator.

---

## Agent prompt design — coach persona

Use this voice across all three agents. It's the voice the human had
designing the plan, so the agents should sound like the same coach.

```
You are a marathon coach who has been working with this athlete on their
specific 12-month, three-marathon plan. You know their plan philosophy,
their injury history, and their goal: sub-5:00 finishes, healthy, enjoyed.

Tone:
- Direct, not effusive. Skip pep talks.
- Honest. Say when something is off-plan or risky.
- Specific. Reference the actual workouts, distances, dates, metrics
  the athlete is dealing with — not generic advice.
- Brief. The athlete is busy. Two paragraphs of useful is better than
  five of comprehensive.
- One specific cue per response. Not a checklist of ten things.

Boundaries:
- You are not a doctor. Symptoms get a "talk to a sports medicine doc."
- You don't override the philosophy. Plan integrity matters.
- You propose; the athlete decides.
```

Each agent then has its task-specific addendum.

---

## Done criteria checklist

Shared context:
- [ ] `build_athlete_context()` returns the full TypedDict shape
- [ ] Tested with sample data — all fields populate correctly
- [ ] Plan Adapter refactored to use it; existing behavior unchanged
- [ ] Every agent call persists context snapshot

Daily Coach:
- [ ] APScheduler job at 6am generates a brief
- [ ] `/coach/today-brief` returns it
- [ ] Today screen displays it as proper markdown
- [ ] Manual regen button works
- [ ] First-time-of-day (before 6am) on-demand generation works

Run Analyst:
- [ ] Triggered after reconciler matches a new pair
- [ ] 1-paragraph review written to reconciliation
- [ ] Workout Detail screen displays it
- [ ] Backfill endpoint works

Chat:
- [ ] `POST /chat` and `GET /chat` work
- [ ] Chat screen renders messages correctly
- [ ] Markdown rendering in coach replies
- [ ] "Thinking" indicator during API call
- [ ] History truncation keeps context size bounded

Polish:
- [ ] APScheduler runs sync hourly + coach at 6am in prod
- [ ] Garmin reauth banner appears + works
- [ ] All screens have proper empty/loading/error states
- [ ] Pull-to-refresh on key screens
- [ ] Sync indicator visible

Quality:
- [ ] `pytest` green
- [ ] `ruff` green
- [ ] `tsc --noEmit` green
- [ ] No console warnings in RN
- [ ] Real-iPhone tested

---

## First action

Confirm sessions 1 and 2 are running healthy. Read `SPEC.md`, `PLAN.md`.
Propose build order. Wait for approval.

After approval, start with Part A (shared context). Don't touch agents
until A1 is solid and tested.
