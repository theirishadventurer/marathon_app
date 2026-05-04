# Session 1 — Backend Foundation

> **Paste this entire file into Claude Code as the opening message.**
> Read `SPEC.md`, `PLAN.md`, and `schema.sql` first. Then propose your build
> order and **stop and wait for confirmation before writing any code.**

---

## Goal

Stand up the backend. By the end of this session I should be able to:

1. `docker compose up` and have a healthy API + Postgres
2. Run `python -m app.seed.load_plan` and have my full Marathon Trilogy plan
   loaded into `planned_workouts` (every week, every workout, all 3 phases)
3. Log in via `POST /auth/login` and get a JWT
4. Hit `GET /plan/today` and see today's planned workout
5. Hit `GET /plan/week?date=2026-10-19` and see the 7 days of MCM race week
6. Run `POST /admin/sync` with valid Garmin tokens and see my last 7 days of
   activities populated in `completed_workouts`
7. See reconciler matches between planned and completed runs

**No mobile app this session. No agent calls this session.** (Stub agent
files exist but return placeholders.)

---

## Scope: what you build

### 1. Project skeleton
```
.
├── pyproject.toml            (uv, target Python 3.12)
├── docker-compose.yml         (postgres:16-alpine + api)
├── Dockerfile                 (api)
├── .env.example
├── .gitignore
├── alembic.ini
├── alembic/
│   └── versions/
├── app/
│   ├── __init__.py
│   ├── main.py
│   ├── config.py              (pydantic-settings)
│   ├── db.py                  (async engine, session factory)
│   ├── auth.py                (JWT issue/verify, password hash)
│   ├── deps.py                (get_db, get_current_athlete)
│   ├── models/
│   │   ├── __init__.py
│   │   ├── base.py            (Base = DeclarativeBase, mixins)
│   │   ├── athlete.py
│   │   ├── plan.py            (Plan, Cycle)
│   │   ├── workout.py         (PlannedWorkout, CompletedWorkout)
│   │   ├── reconciliation.py
│   │   ├── metrics.py         (DailyMetric)
│   │   ├── agent.py           (AgentMessage)
│   │   └── garmin.py          (GarminAuthState)
│   ├── schemas/               (Pydantic v2)
│   │   ├── __init__.py
│   │   ├── auth.py
│   │   ├── plan.py
│   │   ├── workout.py
│   │   ├── metrics.py
│   │   └── garmin.py
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── auth.py
│   │   ├── plan.py
│   │   ├── workouts.py
│   │   ├── metrics.py
│   │   ├── garmin.py
│   │   ├── chat.py            (stub: returns 501)
│   │   └── admin.py
│   ├── services/
│   │   ├── __init__.py
│   │   ├── garmin_sync.py
│   │   ├── reconciler.py
│   │   ├── agent_context.py   (stub for now)
│   │   └── agents/
│   │       ├── __init__.py
│   │       ├── daily_coach.py     (stub)
│   │       ├── plan_adapter.py    (stub)
│   │       └── run_analyst.py     (stub)
│   ├── seed/
│   │   ├── __init__.py
│   │   ├── load_plan.py           (parses PLAN.md, idempotent)
│   │   └── plan_parser.py         (the table-parsing logic)
│   └── lib/
│       └── workout_family.py      (type → family mapping)
└── tests/
    ├── conftest.py
    ├── test_auth.py
    ├── test_seed.py
    ├── test_plan_routes.py
    ├── test_reconciler.py
    └── test_workout_family.py
```

### 2. Database
- Translate `schema.sql` to SQLAlchemy 2.0 typed declarative models. Use
  `Mapped[T]` and `mapped_column(...)` everywhere. No legacy 1.x style.
- Generate the initial Alembic migration. **Verify it matches `schema.sql`
  exactly.** If it doesn't, fix the models, not the schema.
- `family` column on `planned_workouts` and `completed_workouts` is
  derived. Keep a single source of truth in `app/lib/workout_family.py`:
  ```python
  def family_for_planned(t: WorkoutType) -> WorkoutFamily: ...
  def family_for_garmin_activity_type(s: str) -> WorkoutFamily: ...
  ```
  Set the column at insert time. Tests cover this.

### 3. Auth
- `POST /auth/login` with `{email, password}` → `{token, expires_at}`
- JWT signed with `SECRET_KEY` from env, HS256, 30-day expiry
- `get_current_athlete` dependency reads `Authorization: Bearer ...`,
  decodes JWT, loads athlete from DB
- All routes except `/auth/login` and `/health` require auth
- No signup endpoint. Athlete is created by the seed script.

### 4. Seed: load the plan from `PLAN.md`

**This is the most important piece of session 1.** The seed has to load the
entire trilogy plan, not just a fake week.

- `app/seed/plan_parser.py` reads `PLAN.md` and parses:
  - The `Athlete Profile` YAML block → athlete row (prompt for password
    when called interactively, or use `SEED_PASSWORD` env var when run
    non-interactively)
  - The `The Three Races` table → cycles (3 rows)
  - The `Plan Philosophy` block → `plans.philosophy_md`
  - Each phase's `WEEK N` blocks → `planned_workouts` rows
- Workout date = cycle start_date + (week-1)*7 + day_offset where
  Mon=0, Tue=1, ..., Sun=6
- `original_date == scheduled_date` at seed time
- `family` derived via `workout_family.py`
- **Idempotent.** Running `load_plan` twice does nothing the second time.
  Strategy: compute a deterministic key per workout (cycle_seq, week,
  day) and upsert. Or: drop and recreate within a transaction with a
  `--reset` flag.
- Print a summary: `Loaded 1 athlete, 1 plan, 3 cycles, N planned workouts.`

**Cycle anchor dates** (don't reverse-engineer from the plan; use these):
- Phase 1 (MCM): start `2026-04-13` (Mon), race `2026-10-25` (Sun)
- Phase 2 (Disney): start `2026-10-26` (Mon), race `2027-01-10` (Sun)
- Phase 3 (Delaware): start `2027-01-11` (Mon), race `2027-04-11` (Sun)

### 5. Read endpoints
- `GET /plan/current` → `{plan, active_cycle, cycle_progress: {week, total}}`
- `GET /plan/today` → `{date, workouts: [PlannedWorkoutOut], coach_brief: null}`
  (`coach_brief` stays null this session — wired in session 3)
- `GET /plan/week?date=YYYY-MM-DD` → `{week_start, days: [{date, workouts: [...]}]}`
  - Week is Mon-Sun containing `date`
- `GET /workouts/{id}` → `{planned, completed, reconciliation}` (any may be null)
- `GET /metrics/recent?days=14` → `[DailyMetricOut]`

### 6. Garmin sync
- `app/services/garmin_sync.py` using `python-garminconnect`
- Single class `GarminSyncService` with methods:
  - `async def reauth(email, password) -> None`
  - `async def sync_activities(since_date: date) -> list[CompletedWorkout]`
  - `async def sync_daily_metrics(since_date: date) -> list[DailyMetric]`
  - `async def sync_all(days_back: int = 7) -> SyncReport`
- `python-garminconnect` is sync — wrap calls in `asyncio.to_thread`
- Tokens at `./data/garmin_tokens/{athlete_id}/`
- FIT files at `./data/fit/{garmin_activity_id}.fit` (use `download_activity`
  with `dl_fmt=ActivityDownloadFormat.ORIGINAL`)
- On `GarminConnectAuthenticationError`: update `garmin_auth_state` with
  `needs_reauth=True`, `last_error=str(e)`, `last_error_at=now()`. Do not
  retry. Surface in `GET /garmin/status`.
- After `sync_all` completes, run the reconciler.

### 7. Garmin auth endpoints
- `POST /garmin/reauth` `{email, password}` → calls `reauth()`, returns
  `{ok, last_sync}`
- `GET /garmin/status` → `{needs_reauth, last_sync, last_error,
  last_error_at}`

### 8. Admin endpoints (dev convenience)
- `POST /admin/sync` → triggers `sync_all`, returns `SyncReport`
  (later this becomes APScheduler hourly; for session 1, manual is fine)

### 9. Reconciler
- `app/services/reconciler.py`
- `async def reconcile(athlete_id) -> ReconciliationReport`
- For each `completed_workouts` row that has no `reconciliations` row:
  - Find `planned_workouts` rows where:
    - `cycle.plan.athlete_id == athlete_id`
    - `scheduled_date == completed.activity_date`
    - `family == completed.family`
    - `status IN ('planned', 'moved')`
    - No existing reconciliation
  - 0 matches → create reconciliation with `planned_id=NULL`, confidence
    `NULL`
  - 1 match → create reconciliation, confidence 1.0, set planned status
    to `done`
  - 2+ matches → pick by closest `abs(distance_planned - distance_completed)`
    (or duration if no distance), confidence 0.7, set planned status to
    `done`
- Also create reconciliation rows for `planned_workouts` that are >24h past
  their `scheduled_date` with no completed match — these represent skipped
  workouts. Set their status to `skipped` and create reconciliation with
  `completed_id=NULL`.

### 10. Tests
Required passing tests:
- `test_auth.py` — login returns JWT, JWT validates, bad creds → 401
- `test_seed.py` — load_plan creates 1 athlete + 1 plan + 3 cycles + the
  exact expected workout count (you'll need to count from PLAN.md and
  hardcode the assertion); running it twice doesn't dupe
- `test_plan_routes.py` — `/plan/today`, `/plan/week`, `/plan/current`
  return correct shapes; auth required
- `test_reconciler.py` — single match, multi match, no match, skipped
  detection; idempotent
- `test_workout_family.py` — every WorkoutType maps to a family; common
  Garmin activity strings map correctly (`running`, `strength_training`,
  `cycling`, etc.)

Don't write Garmin sync tests this session. Mark them TODO. Real sync
verification is manual via `POST /admin/sync`.

### 11. Stubs (so session 2/3 has clean drop-in points)
- `app/services/agent_context.py`:
  ```python
  async def build_athlete_context(db, athlete_id) -> dict:
      raise NotImplementedError("Wired in session 3")
  ```
- `app/services/agents/{daily_coach,plan_adapter,run_analyst}.py`: empty
  stubs with the function signatures from `SPEC.md`, all raising
  `NotImplementedError`.
- `app/routes/chat.py`: returns 501 Not Implemented.

---

## Out of scope (explicitly do NOT build this session)

- ❌ The `/workouts/{id}/move` endpoint (session 2)
- ❌ The `/workouts/{id}/apply-move` endpoint (session 2)
- ❌ Any actual agent calls to Anthropic API (session 3)
- ❌ APScheduler scheduling (use `POST /admin/sync` manual trigger)
- ❌ Mobile app code
- ❌ Production deploy scripts beyond docker-compose
- ❌ Push notifications, web app, multi-user

---

## Constraints

1. **Pydantic v2 syntax.** No `BaseSettings` from pydantic — use
   `pydantic-settings`. No `Config` class — use `model_config = ConfigDict(...)`.
2. **SQLAlchemy 2.0 typed declarative.** `Mapped[...]`, `mapped_column(...)`.
   Async session everywhere. No sync DB calls.
3. **No global state.** Pass session via FastAPI `Depends`.
4. **Format with `ruff format`. Lint with `ruff check`.** Both must pass.
5. **Type hints everywhere.** `mypy --strict app/` should pass (don't
   actually run mypy as a hard gate, but write code as if you would).
6. **Don't change `SPEC.md` or `PLAN.md` or `schema.sql`** without asking
   me first. If you find a problem, stop and raise it.

---

## Working style

1. Read `SPEC.md`, `PLAN.md`, `schema.sql` end to end.
2. Propose your build order as a numbered list. Stop. Wait for me to
   confirm.
3. Build one numbered slice at a time. After each, run tests + lint and
   confirm green before moving on.
4. Commit after each major slice with a clear commit message.
5. If you hit a decision the spec doesn't cover, **stop and ask** rather
   than guessing.

---

## Done criteria checklist (verify each before declaring done)

Backend functionality:
- [ ] `docker compose up` brings up healthy postgres + api
- [ ] `alembic upgrade head` succeeds against the db
- [ ] `alembic check` shows no schema drift between models and migration
- [ ] `python -m app.seed.load_plan` populates 1 athlete, 1 plan, 3 cycles,
      and the full set of planned workouts from PLAN.md
- [ ] Re-running seed doesn't duplicate rows (count is identical)
- [ ] `curl -X POST /auth/login -d '{"email":"...","password":"..."}'`
      returns a JWT
- [ ] `curl -H "Authorization: Bearer ..." /plan/today` returns today's
      planned workouts
- [ ] `curl ... /plan/week?date=2026-10-19` returns 7 days
- [ ] `curl ... /plan/current` returns active cycle = "Phase 1: MCM" if
      run between 2026-04-13 and 2026-10-25
- [ ] `curl -X POST /admin/sync` with valid Garmin tokens populates
      `completed_workouts`
- [ ] At least one reconciliation row exists after sync
- [ ] `curl ... /workouts/{id}` returns planned + completed + reconciliation

Quality:
- [ ] `pytest` passes, all tests green
- [ ] `ruff check` passes
- [ ] `ruff format --check` passes
- [ ] No `TODO` or `FIXME` comments left in code that should have been
      done this session (TODOs for sessions 2/3 are fine and welcome)

Stubs:
- [ ] Agent stub files exist with correct signatures and `NotImplementedError`
- [ ] `/chat` route exists and returns 501

---

## First action

Read `SPEC.md`, `PLAN.md`, `schema.sql`. Then reply with:

1. Confirmation you've understood the scope
2. Your proposed build order (numbered slices)
3. Any questions about ambiguity in the spec

Wait for my approval. Then start with slice 1.
