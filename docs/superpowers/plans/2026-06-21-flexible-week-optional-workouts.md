# Flexible Week + Optional Workouts Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a per-workout `optional` flag so a 4–5 run week is the intended floor (not a failure), collapse 2 strength days into 1, and make the mileage tracker treat core miles as the goal and optional miles as bonus.

**Architecture:** One new boolean column `PlannedWorkout.optional` drives everything. The seed pre-tags optional workouts (parsed from a new `opt` flag cell in PLAN.md rows); the plan aggregator splits weekly/program mileage into core vs optional and computes "on plan / done" from core counts only; the mobile UI adds a self-serve core↔optional toggle, dims optional workouts, and renders core-as-goal / optional-as-bonus in the weekly card, tracker, and program chart.

**Tech Stack:** Backend — FastAPI, Pydantic v2, SQLAlchemy async, Alembic, pytest (in Docker). Mobile — Expo/React Native, TS strict, TanStack Query.

## Global Constraints

- Backend tests run in the container: `docker compose exec -T api pytest` (host has no deps).
- Pydantic v2 + SQLAlchemy: native enum columns + shared sessions in tests return raw strings — use enum members (`WorkoutStatus.done`) in fixtures, not `"done"`.
- Fail-closed config checks fire only when `APP_ENV=production`; dev + pytest use defaults.
- 5xx without CORS headers reads as "CORS blocked" — convert expected failures to explicit `HTTPException(4xx)`.
- Mobile validation gate per task: `cd mobile && npx tsc --noEmit`. No jest infra.
- Keep files under ~500 lines; hoist imports to top (ruff E402).
- Seed is idempotent by `(cycle_id, week_number, day)` upsert but does NOT delete rows no longer in PLAN.md. **No `(cycle, week, day)` key may be removed** by the PLAN.md rewrite — only retyped/retagged — or prod gets ghost rows. After structural plan edits: local `docker compose down -v` → `alembic upgrade head` → `python -m app.seed.load_plan`.
- The seed upsert must NOT reset `status` / reconciliation on existing rows (preserve completed/linked workouts) — match current seed behavior.
- `optional` semantics: core = counts toward "week done / on plan"; optional = upside, never a deficit. `actual_mi` always sums ALL completed miles (core + optional + makeup).

---

# Phase 1 — Backend foundation

### Task 1: `optional` column on PlannedWorkout + migration

**Files:**
- Modify: `app/models/workout.py` (PlannedWorkout)
- Create: `alembic/versions/<rev>_planned_workout_optional.py`
- Test: `tests/test_models_optional.py` (create)

**Interfaces:**
- Produces: `PlannedWorkout.optional: bool` (NOT NULL, server default false).

- [ ] **Step 1: Add the column** — in `app/models/workout.py`, ensure `Boolean` and `text` are imported from sqlalchemy (add to the existing `from sqlalchemy import ...` line if missing). Add to `PlannedWorkout` after `intent_md` (around line 32):

```python
    optional: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("false")
    )
```

- [ ] **Step 2: Generate an empty migration revision** (auto-sets down_revision to head)

Run: `docker compose exec -T api alembic revision -m "planned_workout optional"`
Expected: prints `Generating .../alembic/versions/<rev>_planned_workout_optional.py`.

- [ ] **Step 3: Fill the migration body** — replace the generated `upgrade`/`downgrade`:

```python
import sqlalchemy as sa
from alembic import op


def upgrade() -> None:
    op.add_column(
        "planned_workouts",
        sa.Column("optional", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )


def downgrade() -> None:
    op.drop_column("planned_workouts", "optional")
```

Leave the auto-generated `revision`/`down_revision` lines as-is.

- [ ] **Step 4: Apply + round-trip the migration**

Run:
```bash
docker compose exec -T api alembic upgrade head
docker compose exec -T api alembic downgrade -1
docker compose exec -T api alembic upgrade head
```
Expected: each completes; final state at head.

- [ ] **Step 5: Write a test** — create `tests/test_models_optional.py`:

```python
import pytest
from sqlalchemy import select


@pytest.mark.asyncio
async def test_planned_workout_optional_defaults_false(seeded_db):
    from app.models.workout import PlannedWorkout

    pw = (await seeded_db.execute(select(PlannedWorkout).limit(1))).scalar_one()
    assert pw.optional is False  # existing rows backfill to core
```

- [ ] **Step 6: Run the test**

Run: `docker compose exec -T api pytest tests/test_models_optional.py -v`
Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add app/models/workout.py alembic/versions/ tests/test_models_optional.py
git commit -m "feat(plan): optional column on planned_workouts + migration"
```

---

### Task 2: Parser reads the `opt` flag

**Files:**
- Modify: `app/seed/plan_parser.py` (`_parse_code_block`, `parse_plan`)
- Test: `tests/test_plan_parser_optional.py` (create)

**Interfaces:**
- Consumes: PLAN.md pipe rows `Day | type | dist | dur | description | intent | flags` where `flags` (7th cell, optional) contains `opt` to mark optional.
- Produces: each workout dict (raw and dated) gains `"optional": bool`.

- [ ] **Step 1: Write the failing test** — create `tests/test_plan_parser_optional.py`:

```python
from app.seed.plan_parser import _parse_code_block


def test_opt_flag_marks_optional():
    block = """WEEK 1
Sun | recovery | 3 | 30 | shakeout | flush | opt
Sat | long | 12 | 130 | long run | aerobic
"""
    rows = _parse_code_block(block)
    by_day = {r["day"]: r for r in rows}
    assert by_day["Sun"]["optional"] is True
    assert by_day["Sat"]["optional"] is False  # no flags cell -> core


def test_flags_cell_is_case_insensitive_and_tolerant():
    block = "WEEK 1\nTue | easy | 4 | 40 | easy aerobic | base | OPT\n"
    assert _parse_code_block(block)[0]["optional"] is True
```

- [ ] **Step 2: Run to verify it fails**

Run: `docker compose exec -T api pytest tests/test_plan_parser_optional.py -v`
Expected: FAIL (`KeyError: 'optional'`).

- [ ] **Step 3: Implement** — in `app/seed/plan_parser.py` `_parse_code_block`, after `intent = parts[5] if len(parts) > 5 else ""` add:

```python
        flags = parts[6] if len(parts) > 6 else ""
        optional = "opt" in flags.lower()
```

Add `"optional": optional,` to the appended workout dict (alongside `"intent_md": intent`).

Then in `parse_plan`, in the `dated_workouts.append({...})` dict, add:

```python
                    "optional": w["optional"],
```

- [ ] **Step 4: Run to verify pass**

Run: `docker compose exec -T api pytest tests/test_plan_parser_optional.py -v`
Expected: PASS (2 tests).

- [ ] **Step 5: Commit**

```bash
git add app/seed/plan_parser.py tests/test_plan_parser_optional.py
git commit -m "feat(seed): parse optional 'opt' flag cell from PLAN.md rows"
```

---

### Task 3: Seed persists `optional`

**Files:**
- Modify: `app/seed/load_plan.py:132-145` (the `PlannedWorkout(...)` construction)
- Test: `tests/test_seed_optional.py` (create)

**Interfaces:**
- Consumes: dated workout dicts with `"optional"` (Task 2).
- Produces: seeded `PlannedWorkout` rows with `optional` set.

- [ ] **Step 1: Implement** — in `app/seed/load_plan.py`, add to the `PlannedWorkout(...)` kwargs (after `intent_md=w["intent_md"],`):

```python
                optional=w.get("optional", False),
```

- [ ] **Step 2: Write a test** — create `tests/test_seed_optional.py`:

```python
import pytest
from sqlalchemy import select


@pytest.mark.asyncio
async def test_seed_round_trips_optional(seeded_db):
    """At least one seeded workout is optional and at least one is core,
    proving the flag survives parse -> seed (depends on PLAN.md tagging in Task 6).
    Until Task 6 tags rows, this asserts the column is at least populated as a bool."""
    from app.models.workout import PlannedWorkout

    rows = (await seeded_db.execute(select(PlannedWorkout))).scalars().all()
    assert all(isinstance(r.optional, bool) for r in rows)
```

- [ ] **Step 3: Run the test**

Run: `docker compose exec -T api pytest tests/test_seed_optional.py -v`
Expected: PASS.

- [ ] **Step 4: Commit**

```bash
git add app/seed/load_plan.py tests/test_seed_optional.py
git commit -m "feat(seed): persist optional flag to planned_workouts"
```

---

### Task 4: Aggregator — core/optional mileage + core-only status

**Files:**
- Modify: `app/schemas/plan.py` (WeekRollup, PlanStatsOut)
- Modify: `app/services/plan_aggregator.py` (`build_plan_full`, `_week_status`, `build_plan_stats`)
- Test: `tests/test_plan_full.py` (extend)

**Interfaces:**
- Produces: `WeekRollup.core_mi`, `.optional_mi`, `.core_planned_count`, `.core_done_count`; `PlanStatsOut.core_mi`, `.optional_mi`. `_week_status` computes status from core counts.

- [ ] **Step 1: Add schema fields** — in `app/schemas/plan.py`, add to `WeekRollup` (after `long_run_mi`):

```python
    core_mi: Decimal = Decimal("0")
    optional_mi: Decimal = Decimal("0")
    core_planned_count: int = 0
    core_done_count: int = 0
```

Add to `PlanStatsOut` (after its `planned_mi`/`actual_mi`):

```python
    core_mi: Decimal = Decimal("0")
    optional_mi: Decimal = Decimal("0")
```

- [ ] **Step 2: Write the failing test** — append to `tests/test_plan_full.py`:

```python
@pytest.mark.asyncio
async def test_week_rollup_splits_core_and_optional(seeded_db):
    from app.models.athlete import Athlete
    from app.services.plan_aggregator import build_plan_full

    athlete = (await seeded_db.execute(select(Athlete).limit(1))).scalar_one()
    plan = await build_plan_full(seeded_db, athlete.id)
    w = plan.cycles[0].weeks[0]
    # core + optional miles reconcile to the total planned
    assert w.core_mi + w.optional_mi == w.planned_mi
    assert w.core_planned_count <= w.planned_count
```

- [ ] **Step 3: Run to verify it fails**

Run: `docker compose exec -T api pytest tests/test_plan_full.py::test_week_rollup_splits_core_and_optional -v`
Expected: FAIL (`core_mi` is 0, not the split).

- [ ] **Step 4: Implement the query** — in `plan_aggregator.py` `build_plan_full`, add `and_` to the sqlalchemy import (`from sqlalchemy import and_, func, select`). Add these aggregates to the `rollup_rows` select (after the existing `planned_mi` / `long_run_mi` lines):

```python
                func.coalesce(
                    func.sum(PlannedWorkout.distance_mi).filter(
                        PlannedWorkout.optional.is_(False)
                    ),
                    0,
                ).label("core_mi"),
                func.coalesce(
                    func.sum(PlannedWorkout.distance_mi).filter(
                        PlannedWorkout.optional.is_(True)
                    ),
                    0,
                ).label("optional_mi"),
                func.count().filter(PlannedWorkout.optional.is_(False)).label("core_planned_count"),
                func.count()
                .filter(
                    and_(
                        PlannedWorkout.optional.is_(False),
                        PlannedWorkout.status == WorkoutStatus.done,
                    )
                )
                .label("core_done_count"),
                func.count()
                .filter(
                    and_(
                        PlannedWorkout.optional.is_(False),
                        PlannedWorkout.status == WorkoutStatus.skipped,
                    )
                )
                .label("core_skipped_count"),
```

- [ ] **Step 5: Wire the rollup + status** — in the `WeekRollup(...)` construction, add:

```python
                    core_mi=Decimal(str(r.core_mi or 0)),
                    optional_mi=Decimal(str(r.optional_mi or 0)),
                    core_planned_count=r.core_planned_count,
                    core_done_count=r.core_done_count,
```

Change the `_week_status(...)` call to pass core counts:

```python
            status = _week_status(
                week_start=r.week_start,
                week_end=r.week_end,
                planned_count=r.core_planned_count,
                done_count=r.core_done_count,
                skipped_count=r.core_skipped_count,
                today=today,
            )
```

`_week_status`'s body is unchanged (it already treats its `planned_count`/`done_count`/`skipped_count` generically — now fed core-only values, so optional workouts never force `partial`/`skipped`/block `done`).

- [ ] **Step 6: Split stats mileage** — in `build_plan_stats`, the `counts_q` already sums `planned_mi_total`. Add two more aggregates to that select:

```python
            func.coalesce(
                func.sum(PlannedWorkout.distance_mi).filter(PlannedWorkout.optional.is_(False)),
                0,
            ).label("core_mi_total"),
            func.coalesce(
                func.sum(PlannedWorkout.distance_mi).filter(PlannedWorkout.optional.is_(True)),
                0,
            ).label("optional_mi_total"),
```

And `on_plan_pct` — change `row.done`/`row.settled` to count core only by adding core-filtered counts to the same select (`done` filter gains `and_(... optional.is_(False))`), OR keep as-is if the `done`/`settled` already exclude optional via a follow-up. For this task: add `core_done` and `core_settled` counts to `counts_q` mirroring the existing `done`/`settled` but `and_`-ed with `PlannedWorkout.optional.is_(False)`, and compute `on_plan_pct = (row.core_done / row.core_settled) if row.core_settled else 0.0`. Then in `PlanStatsOut(...)` set `core_mi=Decimal(str(row.core_mi_total or 0))`, `optional_mi=Decimal(str(row.optional_mi_total or 0))`. Also update `_empty_stats` to pass `core_mi=Decimal("0")`, `optional_mi=Decimal("0")`.

- [ ] **Step 7: Run the suite**

Run: `docker compose exec -T api pytest tests/test_plan_full.py -v`
Expected: PASS (new test + existing green).

- [ ] **Step 8: Commit**

```bash
git add app/schemas/plan.py app/services/plan_aggregator.py tests/test_plan_full.py
git commit -m "feat(plan): split core/optional mileage + core-only week status & on-plan%"
```

---

### Task 5: API — core↔optional toggle on the workout edit

**Files:**
- Modify: `app/schemas/edit.py` (EditWorkoutRequest)
- Modify: `app/schemas/plan.py` (PlannedWorkoutOut — add `optional`)
- Modify: `app/routes/workouts.py` (`edit_workout`)
- Test: `tests/test_workout_optional_toggle.py` (create)

**Interfaces:**
- Consumes: `PATCH /workouts/{id}` with `{ "optional": true|false }`.
- Produces: flips `PlannedWorkout.optional`, busts plan cache, returns `PlannedWorkoutOut` with `optional`.

- [ ] **Step 1: Write the failing test** — create `tests/test_workout_optional_toggle.py`:

```python
import pytest
from sqlalchemy import select


@pytest.mark.asyncio
async def test_toggle_optional_flips_and_persists(client, seeded_auth_headers, seeded_db):
    from app.models.workout import PlannedWorkout, WorkoutStatus

    wid = str(
        (
            await seeded_db.execute(
                select(PlannedWorkout.id).where(PlannedWorkout.status == WorkoutStatus.planned).limit(1)
            )
        ).scalar_one()
    )
    r = await client.patch(f"/workouts/{wid}", json={"optional": True}, headers=seeded_auth_headers)
    assert r.status_code == 200, r.text
    assert r.json()["optional"] is True


@pytest.mark.asyncio
async def test_toggle_optional_rejects_foreign_workout(client, seeded_auth_headers):
    import uuid

    r = await client.patch(
        f"/workouts/{uuid.uuid4()}", json={"optional": True}, headers=seeded_auth_headers
    )
    assert r.status_code == 404
```

- [ ] **Step 2: Run to verify it fails**

Run: `docker compose exec -T api pytest tests/test_workout_optional_toggle.py -v`
Expected: FAIL (`extra="forbid"` rejects `optional`, or response lacks the field).

- [ ] **Step 3: Implement** — in `app/schemas/edit.py` add to `EditWorkoutRequest`:

```python
    optional: bool | None = None
```

In `app/schemas/plan.py` add to `PlannedWorkoutOut` (after `status`):

```python
    optional: bool = False
```

In `app/routes/workouts.py` `edit_workout`, add after the `intent_md` apply block:

```python
    if "optional" in updates:
        planned.optional = updates["optional"]
```

- [ ] **Step 4: Run to verify pass**

Run: `docker compose exec -T api pytest tests/test_workout_optional_toggle.py -v`
Expected: PASS (2 tests).

- [ ] **Step 5: Run the workouts + plan suites — no regressions**

Run: `docker compose exec -T api pytest tests/test_plan_full.py tests/test_workout_optional_toggle.py -q`
Expected: all pass.

- [ ] **Step 6: Commit**

```bash
git add app/schemas/edit.py app/schemas/plan.py app/routes/workouts.py tests/test_workout_optional_toggle.py
git commit -m "feat(workouts): core<->optional toggle via PATCH /workouts/{id}"
```

---

# Phase 2 — Plan content

### Task 6: Rewrite PLAN.md — 1 strength day + optional tagging

**Files:**
- Modify: `PLAN.md` (Weekly Template, Strength Sessions, every `WEEK N` block in all 3 phases)
- Test: parse + seed verification (below)

> **Critical:** Do NOT remove any `(week, day)` key. Each former Strength B (Fri)
> day must be RETYPED to a real workout (an `easy` run, often the optional 5th),
> not deleted — otherwise prod gets ghost rows. Only Sat `long` is day-pinned.

- [ ] **Step 1: Rewrite the prose sections** — In `PLAN.md`:
  - **Weekly Template** block → the new structure: Long (Sat, core), Quality (1 weekday, core), Easy ×2 (core), Strength/cross "The King" (1 day, core), optional easy 5th run + optional Sunday recovery.
  - **Strength Sessions** → replace Strength A/B with one "The King" session: glute-med/hip prehab warm-up (retained), main lifts 3×5 Squat/Deadlift/Bench/Pull-ups, 15-min metcon finisher.

- [ ] **Step 2: Rewrite each `WEEK N` block** — for all weeks across the 3 phases. **Preserve each week's existing distances/durations/paces; do NOT invent new mileage** — only change the strength rows and add `opt` flags. Specifically:
  - Keep ONE strength row (type `strength_a` to reuse the family mapping; retitle/redescribe it as "The King"). The OTHER former strength day (Fri Strength B) must be RETYPED to an `easy` run with the `opt` flag — it becomes the optional 5th run. (Pick that day's distance to match the week's other easy runs, scaled per the spec: ≈3 mi cutback, 4–5 mi build.)
  - Add ` | opt` as the 7th cell to: the Sunday recovery row and the retyped optional 5th easy run row.
  - Core rows (long, quality, the 2 easy runs, strength) get NO flags cell (default core) and keep their current distances.
  - Keep every `(week, day)` that previously had a row (retype, never delete).

Example week row set (illustrative shape — use each week's real existing distances):
```
WEEK 8
Mon | strength_a | | 50 | The King: SQ/DL/BN/PU 3x5 + 15min metcon | knee prehab + power
Tue | easy | 5 | 50 | easy aerobic | base
Wed | tempo | 6 | 60 | quality: tempo | threshold
Thu | easy | 5 | 50 | easy aerobic | base
Fri | easy | 4 | 40 | optional aerobic | base | opt
Sat | long | 16 | 175 | long run | aerobic endurance
Sun | recovery | 3 | 30 | shakeout | flush | opt
```

- [ ] **Step 3: Verify parse counts** (host-side parse is fine; no DB needed)

Run: `docker compose exec -T api python -c "from app.seed.plan_parser import parse_plan; d=parse_plan('PLAN.md'); ws=[w for c in d['cycles'] for w in c['workouts']]; str3=[w for w in ws if 'strength' in w['type']]; print('strength rows:', len(str3)); print('optional rows:', sum(1 for w in ws if w['optional'])); import collections; print('per-week strength<=1:', all(v<=1 for v in collections.Counter((w['week_number'], 'cyc') for w in str3).values()) if str3 else 'n/a')"`
Expected: prints sensible counts — at most 1 strength row per week; optional rows > 0.

- [ ] **Step 4: Reseed clean + verify no ghost rows**

Run:
```bash
docker compose down -v
docker compose up -d
docker compose exec -T api alembic upgrade head
docker compose exec -T api python -m app.seed.load_plan
docker compose exec -T api pytest tests/test_plan_full.py tests/test_seed_optional.py -q
```
Expected: seed succeeds; tests green (incl. the core/optional split + status). Confirm each cycle's week counts match the prior structure (no week lost a day).

- [ ] **Step 5: Commit**

```bash
git add PLAN.md
git commit -m "feat(plan): 1 strength day (The King) + optional tagging across all weeks"
```

---

# Phase 3 — Mobile

### Task 7: Mobile types — optional + core/optional rollup fields

**Files:**
- Modify: `mobile/src/api/types.ts`

**Interfaces:**
- Produces: `optional: boolean` on the planned-workout types; `core_mi`, `optional_mi`, `core_planned_count`, `core_done_count` (strings/numbers) on `WeekRollup`.

- [ ] **Step 1: Add fields** — in `mobile/src/api/types.ts`:
  - To `WeekRollup` (after `long_run_mi`):
    ```typescript
      core_mi: string;        // Decimal string — the GOAL line
      optional_mi: string;    // Decimal string — bonus/upside
      core_planned_count: number;
      core_done_count: number;
    ```
  - To the planned-workout interface(s) that mirror `PlannedWorkoutOut` / workout detail (search for `status:` + `family:` in a workout interface), add:
    ```typescript
      optional: boolean;
    ```
  - To the stats interface (mirrors `PlanStatsOut`), add `core_mi: string;` and `optional_mi: string;`.

- [ ] **Step 2: Typecheck**

Run: `cd mobile && npx tsc --noEmit`
Expected: clean.

- [ ] **Step 3: Commit**

```bash
git add mobile/src/api/types.ts
git commit -m "feat(mobile): optional + core/optional rollup types"
```

---

### Task 8: Optional toggle on WorkoutDetailScreen

**Files:**
- Modify: `mobile/src/screens/WorkoutDetailScreen.tsx`
- Consumes: existing `useEditWorkout()` (`mobile/src/api/hooks/useEditWorkout.ts`) — `mutateAsync({ workoutId, body })`.

- [ ] **Step 1: Add the toggle** — in `WorkoutDetailScreen.tsx`, near the "Mark done"/"Link a run" controls, add a control that reads `detail.data.planned.optional` and flips it:

```typescript
  const edit = useEditWorkout();
  // ...
  const onToggleOptional = async () => {
    const planned = detail.data?.planned;
    if (!planned) return;
    await edit.mutateAsync({ workoutId: planned.id, body: { optional: !planned.optional } });
  };
```

Render a `RetroButton` (match existing button style) labeled `planned.optional ? 'Make core' : 'Make optional'` wired to `onToggleOptional`. `useEditWorkout` already invalidates `['plan']`/`['workout']` (verify; if not, add the invalidation there).

- [ ] **Step 2: Typecheck**

Run: `cd mobile && npx tsc --noEmit`
Expected: clean.

- [ ] **Step 3: Commit**

```bash
git add mobile/src/screens/WorkoutDetailScreen.tsx
git commit -m "feat(mobile): core<->optional toggle on workout detail"
```

---

### Task 9: Optional visual treatment (dim + OPT badge)

**Files:**
- Modify: `mobile/src/components/WorkoutCard.tsx` (Week/Today list card — find the file rendering a planned workout row)
- Modify: `mobile/src/components/program/WeekTile.tsx` (already shows tags) if a per-tile optional cue is wanted

- [ ] **Step 1: Add the cue** — in `WorkoutCard.tsx`, when `workout.optional` is true: render an `OPT` badge (mirror the existing status-tag/badge styling in that file) and apply a dimmed opacity/`colors.inkDim` to the card text, so optional reads as "nice to do." Do not change layout/gestures.

- [ ] **Step 2: Typecheck**

Run: `cd mobile && npx tsc --noEmit`
Expected: clean.

- [ ] **Step 3: Commit**

```bash
git add mobile/src/components/WorkoutCard.tsx
git commit -m "feat(mobile): dim optional workouts + OPT badge"
```

---

### Task 10: WeekTile — core goal + optional bonus

**Files:**
- Modify: `mobile/src/components/program/WeekTile.tsx`

- [ ] **Step 1: Switch the goal to core + show optional** — in `formatMileageGlyph`, change the planned-mileage references from `week.planned_mi` to `week.core_mi` (the goal). After the existing glyph + the `LR Nmi` suffix, add an optional-bonus suffix when `parseFloat(week.optional_mi) > 0`:

```typescript
  const optMi = Math.round(parseFloat(week.optional_mi));
  // ...inside the mileage <Text>, after the LR suffix:
  {optMi > 0 && (
    <Text style={{ color: colors.inkDim }}>{`   +${optMi} opt`}</Text>
  )}
```

Use `week.core_planned_count`/`week.core_done_count` if the glyph shows a count (e.g. `✓ {core_done}/{core_planned} core`).

- [ ] **Step 2: Typecheck**

Run: `cd mobile && npx tsc --noEmit`
Expected: clean.

- [ ] **Step 3: Commit**

```bash
git add mobile/src/components/program/WeekTile.tsx
git commit -m "feat(mobile): WeekTile shows core goal + optional bonus"
```

---

### Task 11: WeeklyMileageTracker — core line + optional band

**Files:**
- Modify: `mobile/src/components/program/WeeklyMileageTracker.tsx`

- [ ] **Step 1: Make core the goal, optional the band** — in `WeeklyMileageTracker.tsx`:
  - Extend the `cumulative`/`sumMi` key unions to include `'core_mi' | 'optional_mi'`.
  - Switch the planned/goal references (`'planned_mi'`, `parseFloat(w.planned_mi)`, `maxPlanned`, `plannedToDate`) to `'core_mi'` so the solid bars + cumulative line + "to date" stat track CORE.
  - Add a faint band/segment above the core bar up to `core_mi + optional_mi` (render an extra `View` of height proportional to `optional_mi` in `colors.inkDim`/low opacity, stacked above the core bar). Keep `actual_mi` (all completed) plotted as today.

- [ ] **Step 2: Typecheck**

Run: `cd mobile && npx tsc --noEmit`
Expected: clean.

- [ ] **Step 3: Commit**

```bash
git add mobile/src/components/program/WeeklyMileageTracker.tsx
git commit -m "feat(mobile): tracker core goal line + faint optional band"
```

---

# Phase 4 — Rollout

### Task 12: Reseed + live verification

**Files:** none (ops + verification)

- [ ] **Step 1: Full backend suite green**

Run: `docker compose exec -T api pytest -q`
Expected: all pass.

- [ ] **Step 2: Mobile typecheck clean**

Run: `cd mobile && npx tsc --noEmit`
Expected: clean.

- [ ] **Step 3: Deploy** — merge to `master`, push. Railway redeploys (runs `alembic upgrade head` → adds `optional`; idempotent seed upserts the new PLAN.md content). Vercel rebuilds the PWA.

- [ ] **Step 4: Verify prod data integrity** — confirm on the live app that:
  - existing completed/linked workouts kept their `done` status + reconciliation (seed did not reset them);
  - no duplicate/ghost workouts appeared on any day;
  - each week shows ≤1 strength day; optional runs render dimmed with `OPT`;
  - the weekly card + tracker show core-as-goal and `+opt` bonus; `long_run_mi` still shows.

- [ ] **Step 5: Smoke the toggle** — in the app, flip a workout core↔optional; confirm the weekly card's core total and the tracker update accordingly.

---

## Self-Review Notes

- **Spec coverage:** optional column+migration (T1) · parser opt flag (T2) · seed persist (T3) · aggregator core/optional split + core-only status & on-plan% (T4) · toggle API (T5) · PLAN.md 1-strength + tagging (T6) · mobile types (T7) · toggle UI (T8) · dim+OPT visual (T9) · WeekTile core/bonus (T10) · tracker core line + optional band (T11) · reseed/prod integrity (T12). All spec sections mapped.
- **Ghost-row risk:** addressed in Global Constraints + T6 ("retype, never remove a day-key") + T12 Step 4 verification.
- **`actual_mi` unchanged:** still sums all completed miles (credit for optional/makeup) — T4 leaves the actual joins untouched.
- **Type consistency:** `core_mi`/`optional_mi`/`core_planned_count`/`core_done_count` consistent across schema (T4), API (T5/T7), and mobile (T7/T10/T11). `optional: bool` consistent across model (T1), schema (T5), mobile types (T7), UI (T8/T9).
- **Open content detail:** exact per-week distances/paces in T6 are the athlete's to finalize in PLAN.md; the parser/seed/UI are agnostic to the values.
