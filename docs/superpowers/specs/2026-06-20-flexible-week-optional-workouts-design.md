# Flexible Week + Optional Workouts — Design Spec

**Date:** 2026-06-20
**Status:** Draft for review
**Author:** Chris Bell (with Claude)

## Problem

The current plan (v3.2 "Marathon Trilogy") preaches "flexibility is structural"
but in practice **pins every workout to a fixed day** and prescribes **two**
strength days (Mon/Fri) plus a clean Tue/Wed/Thu trail block. Real life (family
commitments) breaks those assumptions: weekdays are unpredictable, Mon/Fri have
become "makeup run" days, two strength days is too much, and the athlete reliably
lands **4–5 runs/week, not 6**. The rigid day-pinning + the "partial week" mileage
math make a sustainable 4–5 day week read as falling behind.

This is not expected to ease up — the plan should fit the life, not the reverse.

## Goal

Make a 4–5 run week the **intended floor**, not a failure state:

1. Add a per-workout **`optional`** flag. Optional workouts are upside — skipping
   them never makes a week look partial/behind.
2. Collapse **2 strength days → 1** combined strength/cross day (core).
3. The mileage tracker treats **core miles as the goal** and **optional miles as
   bonus** (week/program).
4. The athlete can **re-tag any workout** core↔optional in the app.

Non-goal: a full "weekly target / no day assignment" rebuild. We keep the existing
day-pinned plan and existing screens; we add one flag and adjust the math + visuals.

## Weekly structure (the new core/optional split)

Only **Saturday long run** stays day-pinned (slides to Sun if needed). Everything
else is "any day."

| Workout | Core/Optional | Default day |
|---|---|---|
| Long run | **Core** | Sat (slider → Sun) |
| Quality run (tempo / MP / steady) | **Core** | any weekday |
| Easy run #1 | **Core** | any weekday |
| Easy run #2 | **Core** | any weekday |
| Strength / cross ("The King", 1×, was 2) | **Core** | any day |
| Easy/recovery run #3 (the 5th run) | **Optional** | any day |
| Sunday recovery run | **Optional** | Sun |

**Floor = 4 core runs + 1 strength. Target = 5 runs** (the optional 5th).

### The single strength/cross day — "The King"
~45–60 min, **core**, any day, replaces the old Strength A (Mon) + Strength B (Fri):

- Warm-up / prehab: glute-med + hip-stability work (retained from the current
  knee-protection focus — IT-band / lateral-knee history past mile 14).
- Main lifts **3×5**: Squat, Deadlift, Bench, Pull-ups.
- Finisher: **15-min metcon (WOD)**.

The freed second strength day becomes an easy run slot (one of the core easies or
the optional 5th).

## Data model

- Add `optional: bool` to `PlannedWorkout`, `nullable=False`, server default `false`.
- Alembic migration (`down_revision` = current head); add column with default so
  existing rows backfill to `false` (core).
- No change to `CompletedWorkout` / `Reconciliation`.

## Plan content (`PLAN.md`) + parser

The seed reads `PLAN.md`. Changes:

1. **Weekly Template** section: rewrite to the core/optional structure above; one
   strength/cross day; mark the 5th run + Sunday recovery optional.
2. **Strength Sessions** section: replace A/B with the single "The King" session.
3. **Every `WEEK N` block**: change the two strength rows to one; ensure each day
   maps to a real workout (see Rollout); add the optional marker to the 5th run +
   Sunday recovery rows.
4. **Parser change** (`app/seed/plan_parser.py`): the pipe-row format
   `Day | type | dist | dur | description | intent` gains an **optional trailing
   `flags` cell**. Convention: a cell containing `opt` (case-insensitive) marks the
   row `optional=true`; absent/blank = core. Backward compatible — rows without the
   cell parse as core. The parser stays format-agnostic otherwise (per the existing
   CLAUDE.md note).
5. `app/seed/load_plan.py`: pass `optional` through to the `PlannedWorkout` upsert.

## Backend aggregation + status (`plan_aggregator.py`, `schemas/plan.py`)

- **WeekRollup** gains: `core_mi: Decimal` and `optional_mi: Decimal`
  (sum of `distance_mi` where `optional` is false / true respectively).
  Keep `planned_mi` = total (core+optional) for backward-compat, but the UI goal
  line uses `core_mi`. `long_run_mi` (already added) unchanged.
- **Core-only counts** for status: add `core_planned_count` / `core_done_count`
  (count only non-optional). `_week_status` uses the **core** counts — a week is
  `done` when all core workouts are done; optional workouts never force `partial`
  or `skipped`. `current`/`upcoming` unchanged (date-based).
- **PlanStats** (`build_plan_stats`): split planned mileage into `core_mi` /
  `optional_mi`; `on_plan_pct` uses core counts only. `actual_mi` still sums **all**
  completed miles (you get credit for optional + makeup runs you actually do).
- Cache invalidation unchanged (already busts on plan-mutating actions; the
  optional toggle must call `invalidate_plan_cache`).

## API

- `GET /plan/full` → WeekRollup now includes `core_mi`, `optional_mi`,
  `core_planned_count`, `core_done_count` (+ existing `long_run_mi`).
- `GET /plan/stats` → includes `core_mi` / `optional_mi`.
- **Toggle:** extend the existing in-place workout edit `PATCH /workouts/{id}`
  (`WorkoutEdit` schema) with `optional: bool | None`. Re-validates ownership
  (`Plan.athlete_id`) like the rest of that route; busts the plan cache.

## Mobile

- **Types** (`api/types.ts`): add `optional` to the workout types; add `core_mi`,
  `optional_mi`, `core_planned_count`, `core_done_count` to `WeekRollup`;
  `core_mi`/`optional_mi` to stats.
- **Tag toggle:** a core↔optional control on `WorkoutDetailScreen` (reuses the
  workout-edit mutation). Optimistic + invalidate `['plan']`/`['workout']`.
- **Optional visual treatment:** optional workouts render dim with an `OPT` badge
  on `WeekScreen` (WorkoutCard), `TodayScreen`, and the Program views. They read as
  "nice to do," not "owed."
- **Weekly card** (`program/WeekTile.tsx`): show core progress + optional bonus,
  e.g. `✓ 24/28 core  +3 opt`, beside the existing `LR Nmi`. Reuse the dim style.
- **Weekly mileage tracker** (`program/WeeklyMileageTracker.tsx`): goal line =
  `core_mi`; faint band above to `core_mi + optional_mi`; actual plotted vs core.
- **Program chart:** cumulative **core** target as the solid line; faint optional
  band above; actual vs core.

## Rollout / reseed (the risk)

The seed upserts by `(cycle_id, week_number, day)` and **does not delete** rows no
longer in `PLAN.md` (documented ghost-row gotcha). Dropping a strength day must not
strand a ghost:

- **Every freed day maps to a real workout** in the new `PLAN.md` (the old 2nd
  strength day → an easy/optional run), so the upsert overwrites in place — no
  orphan. Verify no `(cycle, week, day)` key is *removed* vs. the old plan; only
  changed.
- Local: `docker compose down -v` → `alembic upgrade head` →
  `python -m app.seed.load_plan` for a clean structural reseed.
- **Prod (Railway):** the idempotent seed runs on deploy and will upsert the new
  content. Because no day-keys are removed (only retyped/retagged), no ghost rows
  result. The `optional` column backfills `false`, then the seed sets the tagged
  rows `true`. **Confirm against live data** that the athlete's already-completed /
  reconciled workouts (status, links) are preserved (upsert must not reset
  `status`/reconciliation on existing rows — match current seed behavior).

## Testing

- Parser: a row with `opt` flag → `optional=true`; without → `false` (+ existing
  format-agnostic cases stay green).
- Aggregator: a seeded week with 1 optional run → `core_mi` excludes it,
  `optional_mi` includes it; week with all **core** done but optional skipped →
  status `done` (not `partial`); `actual_mi` still counts a completed optional run.
- API: `PATCH /workouts/{id}` with `optional` flips the flag + busts cache;
  ownership re-validated (foreign id rejected).
- Mobile: `tsc --noEmit` clean; visual smoke of the dim/badge + tracker band on web.

## Out of scope (future)

- No "assign workout to a day from a weekly menu" UI — days stay editable via the
  existing drag/move.
- No auto-reconcile changes (separate decision).
- Cross-training variety (bike/swim) beyond the metcon — future.

## Open questions

1. Keep glute-med/hip **prehab** as the strength-day warm-up (recommended, given
   injury history) — confirm, or drop for time.
2. Does the **optional 5th run** have a default type/distance, or is it a generic
   "easy, your call" placeholder?
