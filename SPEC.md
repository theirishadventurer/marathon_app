# Marathon Coach — Design Specification

> **Read this at the start of every Claude Code session.** This is the
> durable design contract. The per-session briefs (`SESSION_*.md`) tell you
> what to build *this session*; this file tells you the rules that span all
> of them.

---

## 1. What we're building

A personal mobile app that helps me train for three marathons over 12 months
(MCM Oct 2026, Disney Jan 2027, Coastal Delaware Apr 2027). Goal for all
three: sub-5:00, healthy, enjoyed.

**Functional summary:**
- Training plan visible as a weekly calendar
- Drag-to-move workouts; AI proposes rebalances
- Pulls completed runs from Garmin Connect
- Three AI agents: Daily Coach (morning brief), Plan Adapter (move handler),
  Run Analyst (post-run review)
- Free-form chat with the coach

**Non-functional summary:**
- Single user (me)
- iPhone only (Expo Go)
- Personal-grade polish — clean, not fancy
- Self-hosted on a $5/month VPS

---

## 2. Architecture

```
iPhone (Expo + React Native + TypeScript)
        │  HTTPS, JWT
┌───────▼────────────────────────────────┐
│ FastAPI backend (Python 3.12)          │
│  • REST API                            │
│  • APScheduler (Garmin sync hourly,    │
│    daily coach 6am)                    │
│  • Agent orchestrator (Anthropic API)  │
└───┬─────────────────────────┬──────────┘
    │                         │
┌───▼──────────┐    ┌─────────▼──────────┐
│ PostgreSQL 16│    │ Disk: FIT files,   │
│              │    │ Garmin tokens      │
└──────────────┘    └────────────────────┘
```

**One backend service.** Sync, API, agents, scheduler all in the same FastAPI
process. Personal app — splitting them adds operational pain for zero
benefit.

**Hosting target:** Hetzner CX22 or similar small VPS. Postgres on the same
box. Docker Compose to deploy.

---

## 3. Tech stack — locked

### Backend
- Python 3.12, `uv` for package management
- FastAPI + Pydantic v2 (`pydantic-settings` for config)
- SQLAlchemy 2.0 typed declarative (async) + Alembic
- `asyncpg` driver
- `python-garminconnect` (MIT, actively maintained)
- `apscheduler` for scheduled jobs
- `anthropic` Python SDK
- `python-jose[cryptography]` + `passlib[bcrypt]` for JWT
- `pytest`, `pytest-asyncio` for tests
- `ruff` for format + lint

### Mobile
- Expo SDK 51+, managed workflow
- React Native + TypeScript (strict mode)
- `react-native-reanimated` v3
- `react-native-gesture-handler`
- `@shopify/flash-list`
- `expo-haptics`
- `expo-secure-store` (JWT storage)
- `@tanstack/react-query` v5
- `nativewind` for styling
- `axios` for HTTP

### Infra
- PostgreSQL 16
- Docker Compose for local + production
- `.env` for secrets (one file, not split)

---

## 4. Data model

The schema is canonical in `schema.sql`. Key shape:

```
athletes
plans  ──────── cycles ─────── planned_workouts
                                      │
                                      │ (matched via reconciliations)
                                      │
completed_workouts ───┬───── reconciliations
                      │
daily_metrics         │
                      │
agent_messages ───────┘ (linked by related_workout_id, related_reconciliation_id)
garmin_auth_state
```

### Key design decisions worth not relitigating

**`scheduled_date` vs `original_date` on `planned_workouts`.** Moves are
non-destructive. `original_date` is immutable. This is what lets the Plan
Adapter agent reason about "the plan as designed" vs "the plan as
executed."

**Reconciliation as its own table.** Three cases must be representable:
planned-only (skipped), completed-only (bonus run), both (matched). A
separate table handles all three.

**Always store the raw FIT file.** Parse on ingest, but keep the FIT.
Library upgrades add fields; we want to be able to re-parse without
re-syncing.

**Agent messages persist `context_snapshot_json`.** Whatever the agent saw,
exactly. Critical for debugging coach behavior weeks later.

**Single athlete row.** No multi-tenancy. The `athlete_id` foreign keys are
there because they're free, not because we ever expect a second user.

---

## 5. The three agents

All agents share `build_athlete_context()` which returns a dict containing:
- Athlete profile (zones, paces, injury notes)
- Active plan + active cycle
- This week's planned workouts
- Last 14 days of completed workouts
- Last 14 days of daily metrics (sleep, HRV, RHR, training readiness)
- Last 5 reconciliations with reviews
- Last 10 user_chat messages (for Daily Coach + Run Analyst — they shouldn't
  ignore what we discussed yesterday)
- Plan philosophy (`plans.philosophy_md`)

This function is the most important piece of code in the backend. Get it
right.

### Daily Coach
- Triggered by APScheduler at 6am local time
- Writes `agent_messages` row with `agent='daily_coach'`, `role='assistant'`
- Today screen reads the latest one for today's date
- Output: 2-3 paragraphs covering today's workout, why, recent trends,
  one specific cue

### Plan Adapter
- Triggered by `PATCH /workouts/{id}/move`
- Input: workout id + proposed new date
- Output: `AdapterProposal` JSON with 2-3 rebalance options + reasoning
- Persists with `agent='plan_adapter'`, `proposal_state_json` populated
- **Does not commit the move.** UI calls `POST /workouts/{id}/apply-move`
  with the user's chosen option to commit.

### Run Analyst
- Triggered by reconciler when a new `(planned, completed)` pair is matched
- Input: the reconciliation id
- Output: 1-paragraph review written to `reconciliations.agent_review_md`
- Compares planned target (pace, HR zone, distance) vs actual

---

## 6. API surface

```
POST   /auth/login                     {email, password} → {token}

POST   /garmin/reauth                  {email, password} → {ok}
GET    /garmin/status                  → {needs_reauth, last_sync, last_error}
POST   /admin/sync                     → {synced_activities, synced_metrics}

GET    /plan/current                   → current plan summary
GET    /plan/today                     → today's workout(s) + coach brief
GET    /plan/week?date=YYYY-MM-DD      → 7-day array (Mon-Sun containing date)

GET    /workouts/{id}                  → planned + completed + reconciliation
PATCH  /workouts/{id}/move             {new_date} → AdapterProposal
POST   /workouts/{id}/apply-move       {proposal_id, choice} → {ok}
PATCH  /workouts/{id}/skip             → {ok}

GET    /metrics/recent?days=14         → daily_metrics array

POST   /chat                           {message} → {reply}
GET    /chat?limit=50                  → message array

GET    /coach/today-brief              → latest daily_coach message for today
```

All routes except `/auth/login` require `Authorization: Bearer <jwt>`.

---

## 7. UI screens

1. **Login** — email/password → JWT
2. **Today** — coach brief, today's workout card, recent completed runs strip
3. **Week** — 7 day-cards, drag-to-move, "Why?" sheets
4. **Workout detail** — full prescription + completed comparison + analyst review
5. **Chat** — coach conversation, full-screen
6. **Settings** — Garmin reauth, sync status, plan info, logout

---

## 8. Garmin sync

- Hourly via APScheduler in the FastAPI process
- Pulls per cycle: `get_activities_by_date`, `get_activity_details` (per new
  activity), `get_stats_and_body`, `get_sleep_data`, `get_hrv_data`,
  `get_training_status`
- Tokens stored at `./data/garmin_tokens/{athlete_id}/`
- FIT files at `./data/fit/{garmin_activity_id}.fit`
- On `GarminConnectAuthenticationError`: set `garmin_auth_state.needs_reauth
  = TRUE`, log to `last_error`, do not retry until reauth
- After every sync, run the reconciler

---

## 9. Reconciler

For each unmatched `completed_workout`, find planned workouts on the same
date with a compatible type-family:

```
Running family: easy, long, tempo, intervals, hills, mp_long, recovery, strides
Strength family: strength_a, strength_b
Other:            cross, rest, race
```

If exactly one same-date same-family planned workout exists → match with
confidence 1.0.
If multiple → take the closest by distance/duration → confidence 0.7.
If none → leave unreconciled (becomes "bonus" or unscheduled completed run).

After matching, fire Run Analyst (session 3 only).

---

## 10. Design principles

1. **Plan integrity.** Original plan is immutable. Moves are tracked.
2. **Agents propose, user decides.** No automatic plan changes.
3. **Context is the product.** `build_athlete_context()` is the soul of the
   coach. Keep it honest.
4. **Boring tech.** No microservices, no queues, no GraphQL. One service,
   one DB, REST.
5. **Sync failures are normal state.** Garmin auth breaks. Show it honestly
   in the UI; don't hide it.
6. **No silent spec changes.** If the SPEC seems wrong, stop and ask.

---

## 11. Out of scope (explicitly)

- Multi-user / sharing
- Push notifications (V2)
- Apple Health / Strava (V2)
- Pushing structured workouts back to Garmin (would require Connect IQ)
- Web app
- Offline writes (cache reads only)
- Wearable other than Garmin
- Race-day live tracking

---

## 12. File layout (target)

```
.
├── SPEC.md                  # this file
├── PLAN.md                  # the training plan as data
├── SESSION_1.md             # backend foundation
├── SESSION_2.md             # mobile + drag/move + Plan Adapter
├── SESSION_3.md             # Daily Coach + Run Analyst + chat
├── schema.sql               # canonical schema (Alembic generates from models)
├── docker-compose.yml
├── .env.example
├── pyproject.toml
├── alembic/
├── app/
│   ├── main.py
│   ├── config.py
│   ├── db.py
│   ├── auth.py
│   ├── models/              # SQLAlchemy
│   ├── schemas/             # Pydantic
│   ├── routes/              # FastAPI routers
│   ├── services/
│   │   ├── garmin_sync.py
│   │   ├── reconciler.py
│   │   ├── agent_context.py
│   │   └── agents/
│   │       ├── daily_coach.py
│   │       ├── plan_adapter.py
│   │       └── run_analyst.py
│   └── seed/
│       └── load_plan.py
├── tests/
└── mobile/                  # added in session 2
    ├── app.json
    ├── package.json
    ├── App.tsx
    └── src/
        ├── api/
        ├── screens/
        ├── components/
        └── hooks/
```
