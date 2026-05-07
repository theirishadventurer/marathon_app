# Feat C — Start-date Picker with Auto-Recalculate Program

**Status:** design (no code)
**Date:** 2026-05-07
**Owner:** session lead (CBell)
**Branch target:** `session-2/backend-move-endpoints` (design doc only) → followed by an implementation branch

## 1. Goal & user story

The plan was seeded with a hardcoded Phase 1 start of `2026-04-13` and races at
`2026-10-25 / 2027-01-10 / 2027-04-11` (`app/seed/plan_parser.py:11-36`). Real
life intervened. The athlete needs to set "the day my plan starts" without
tearing the database down. **Race dates do not move** — the marathons happen
when they happen. **Plan start moves**, and everything between today and the
first race re-anchors.

### Scenario A — "Reset to today"

> "I'm starting fresh today. Make today week 1 day 1 of Phase 1."

Tap **Settings → Program → Reset Start Date**, pick today (`2026-05-06`), confirm.
The 28-week MCM block compresses (or shifts) so week 1 Mon = the Monday on or
before today. MCM stays on `2026-10-25`. Disney week 1 still starts day after
MCM. Delaware unchanged.

### Scenario B — "Push by N weeks"

> "I'm three weeks behind the seed. Shift everything 3 weeks later."

Tap **Settings → Program → Reset Start Date**, pick `2026-05-04` (3 weeks past
the seed `2026-04-13`), confirm. Every planned date moves +21 days. Race dates
unchanged.

### The hard question: what if the new start makes the plan too short?

If `new_start + cycle_weeks * 7 > race_date`, peak week (W23 in MCM) would land
**after** race day. We **refuse** in v1 with a 400 error explaining the minimum
viable start date for the active cycle. Compress-on-shift is rejected as
out-of-scope: silently shrinking the taper or clipping peak is a coaching
decision the app should not make automatically. The user must explicitly accept
a different remediation (covered in §9 deferred: "compressed taper mode").

The minimum check uses a per-cycle constant `MIN_WEEKS_TO_RACE`:

| Cycle | Total weeks (PLAN.md) | Minimum to race |
|---|---|---|
| MCM | 28 | 16 (cuts pre-peak base, keeps peak + taper) |
| Disney | 11 | 8 |
| Delaware | 13 | 9 |

These thresholds become `app/lib/cycle_constants.py` (new) but for v1 we can
hardcode 16 / 8 / 9 in `plan_parser.CYCLES`.

## 2. Data model — what changes

### Tables affected by a start-date reset

| Table | Field | Change rule |
|---|---|---|
| `plans` | `start_date` | Set to new_start (Mon-aligned). |
| `plans` | `end_date` | Unchanged (last race date stays). |
| `cycles` | `start_date` | Cycle 1 = new_start. Cycle 2 = day-after MCM. Cycle 3 = day-after Disney. |
| `cycles` | `end_date` | Unchanged (= race_date). |
| `cycles` | `race_date` | Unchanged. Race dates are immutable. |
| `cycles` | `peak_week_target` | Unchanged in shift mode; recomputed in reseed mode. |
| `planned_workouts` | `scheduled_date` | Shift by `delta_days` for status='planned' rows. Other statuses preserved. |
| `planned_workouts` | `original_date` | **Unchanged** — preserves the "where it was originally" reference for the audit story. |
| `planned_workouts` | `week_number` | Unchanged in shift mode (week 1 is week 1 in the new anchor). |
| `planned_workouts` | `original_snapshot_json` | Unchanged. User edits preserved. |
| `agent_messages` | `proposal_state_json` | Pending proposals (`state == "pending"`) marked `discarded` with reason `"plan_shifted"`. Already-applied proposals untouched. |
| `completed_workouts` | (all) | Untouched. They're real history. |
| `reconciliations` | (all) | Untouched. The planned row they point to is the same UUID; only its `scheduled_date` changed. |

### New table: `plan_history`

Audit trail for start-date changes (and future plan-level mutations).

| Column | Type | Notes |
|---|---|---|
| `id` | UUID PK | |
| `plan_id` | UUID FK → plans | |
| `athlete_id` | UUID FK → athletes | (denormalized for fast lookup) |
| `action` | TEXT | `"start_date_reset"` for v1; future: `"deactivated"`, `"cloned"`, etc. |
| `before_json` | JSONB | `{"start_date": "...", "cycle_starts": {...}}` |
| `after_json` | JSONB | Same shape, post-change. |
| `summary_json` | JSONB | `{"shifted_workouts": N, "dropped_proposals": N, "skipped_completed": N, "mode": "shift"}` |
| `created_at` | TIMESTAMPTZ | |

Index: `(plan_id, created_at DESC)`.

This is purely append-only. Restore/undo is out of scope (§9).

## 3. Three approaches with tradeoffs

### Option α — Date delta migration (single shift)

Compute `delta_days = new_start - plan.start_date`. Update every
`planned_workouts.scheduled_date` (status='planned' only) by adding delta. Update
`cycles.start_date` for each cycle (cycle 1 = new_start; cycles 2/3 unchanged
because they anchor off the previous race, not off plan start, per
`app/seed/plan_parser.py:11-36`). Update `plans.start_date`.

| Complication | Behavior |
|---|---|
| 1. User-edited workouts (`original_snapshot_json` set) | **Preserved.** Edit content untouched; only date shifts. |
| 2. Completed/skipped/moved (status != planned) | **Skipped.** History stays put on its actual dates. The plan now has a "hole" at the shifted-from spot for those rows, but reconciliations remain valid because they reference UUIDs. |
| 3. Reconciliations | **Untouched.** They reference planned UUID; the planned row's date moved but its identity didn't. Reconciliations to non-planned (done/skipped) workouts are still consistent. |
| 4. Cycle.start_date / end_date / race_date | Cycle 1 start = new_start. Cycle 2 + 3 unchanged (their start = day after previous race, immutable). race_date never changes. |
| 5. Active proposals | Pending proposals (`state == "pending"`) marked `discarded` with `discard_reason = "plan_shifted"`. Their referenced dates would be stale after the shift. Already-applied or discarded proposals untouched. |

**Pros:** simplest mental model, fast (3 UPDATEs), preserves all user
customizations and history, idempotent.
**Cons:** if cycle 1 has had heavy editing of weeks 1-4 and the user shifts
forward 3 weeks, those edits move with the new dates rather than staying on
their original calendar dates — but that's actually what the user wants
("everything I planned shifts together"). Edge case: if delta is negative (user
picks an earlier start than the seed) and that pushes any `status=done` workout
into the future relative to the new plan structure, we have a date paradox. We
guard with **"new_start >= today"** validation.

### Option β — Re-seed cycles + plan from a new anchor

Wipe all `planned_workouts` rows where `status == 'planned'`, regenerate them by
re-running `plan_parser.parse_plan(...)` with cycle 1 start = new_start.

| Complication | Behavior |
|---|---|
| 1. User-edited workouts | **LOST** if the row was status='planned'. The point of `original_snapshot_json` is a one-shot edit history; reseeding throws that away. Bad. |
| 2. Completed/skipped/moved | **Preserved.** We only delete planned rows. |
| 3. Reconciliations | Some reconciliations point at planned UUIDs we just deleted → ON DELETE SET NULL kicks in (per `app/models/reconciliation.py:30`), reconciliations become orphaned to a NULL planned_id. Recoverable but lossy. |
| 4. Cycle / race | Cycle 1 start = new_start; race dates fixed; cycle 2/3 unchanged. |
| 5. Active proposals | Discarded as in α (their planned-row references are stale or dead). |

**Pros:** cleanest re-anchor; gives you back a plan that exactly matches
PLAN.md's structure for the new dates. Useful if user has been editing wildly
and wants to "start over."
**Cons:** destroys user edits silently. Orphans reconciliations. High blast
radius. Should be opt-in, not default.

### Option γ — Per-cycle re-anchor

Only shift the FIRST cycle. Keep cycle 2 / 3 anchored to their respective
race-date-minus-N-weeks calculation working backwards from `race_date`. (Today
the parser hardcodes cycle 2/3 start dates. This option would shift to a
*derived* model.)

| Complication | Behavior |
|---|---|
| 1. User edits | **Preserved** (same as α). |
| 2. Completed/skipped/moved | Preserved. |
| 3. Reconciliations | Untouched. |
| 4. Cycle / race | Cycle 1 = new_start. Cycle 2 = MCM_race + 1d. Cycle 3 = Disney_race + 1d. (Identical to α.) |
| 5. Active proposals | Discarded. |

**Pros:** more "correct" mathematically — you could in future allow per-cycle
overrides ("I want to start the Disney prep block earlier"). Sets up the
pattern for v2 per-cycle picker.
**Cons:** more code, more edge cases (what if cycle 1 shifts forward and the
new start is *after* the seeded cycle 2 start? — can't happen in practice
because cycle 2 is anchored to MCM-day+1, and MCM is fixed). Marginally more
complex than α with no v1 user-visible benefit.

## 4. Recommendation

**Ship Option α (date delta migration) as the v1 default.** Expose `mode` in
the API as a forward-looking hook (`"shift"` | `"reseed"`), but only implement
`"shift"` for v1. `"reseed"` returns 501 Not Implemented in v1; we'll wire it
in v1.1 when we have the user-facing "wipe my edits and start over" flow.

**Why α over β:** the user almost always wants their edits to come along for
the ride. The brief explicitly flags "Already-edited workouts" as a critical
complication; α preserves them, β nukes them. Reseed is a power-user "factory
reset" feature that deserves its own UX path with explicit warnings.

**Why α over γ:** zero user-visible difference today (cycle 2/3 anchor to
race-day in both); γ adds code surface for a v2 feature. Build γ when we ship
per-cycle reanchor.

### What gets lost (be honest)

- **Pending proposals are dropped.** If the user has a Plan Adapter rebalance
  pending for a Tue→Fri move, the proposal references stale dates and gets
  discarded. The user must re-trigger the move. Acceptable: pending proposals
  are short-lived by design.
- **Symbolic awkwardness for completed history.** Completed workouts stay on
  their real calendar dates, but the planned-week structure now wraps around
  them. So week 1 of the *new* plan and week 4 of the *old* plan can both have
  workouts in the same calendar week. This is acceptable because
  `plan/full` and `plan/stats` filter by status — completed/skipped/moved are
  shown in their historical week, planned are shown in the new structure.
- **The "plan history" before the cutover is gone visually.** The Program tab
  will show today as week 1; the seven weeks before that (where the user was
  on the old anchor) become orphaned past data. We surface this in the
  confirmation dialog ("X past planned workouts that were never started will
  be skipped to keep history clean" — see §6).

## 5. Backend API

### `POST /plan/start-date`

```
Body:
{
  "new_start_date": "2026-05-11",   // ISO date, must be a Monday OR will be snapped to Mon
  "mode": "shift"                    // "shift" (v1) | "reseed" (v1.1, returns 501)
}

Response (200):
PlanStartDateResetOut {
  plan: PlanCurrentOut,              // refreshed view of the plan
  summary: {
    mode: "shift",
    delta_days: int,                 // signed
    shifted_workouts: int,           // planned rows that moved
    skipped_workouts: int,           // non-planned rows untouched
    dropped_proposals: int,          // pending proposals discarded
    abandoned_planned_workouts: int  // planned rows in the past (pre-new_start) marked skipped
  }
}
```

### Validations (in order — first failure returns)

1. **Date parse / is Monday.** If not Monday, snap to the Monday on or before
   `new_start_date` and continue. (Why: PLAN.md weeks start on Monday;
   `app/seed/plan_parser.py:38-46`.)
2. **`new_start_date >= today`.** Refuse past dates → `400 {"detail":
   "new_start_date cannot be in the past"}`. (Past-shift is §9 deferred.)
3. **Active plan exists.** If no `is_active=true` plan, `404`.
4. **Mode supported.** `"reseed"` → `501 {"detail": "reseed mode not yet
   implemented"}`.
5. **Minimum cycle weeks before active race.** Compute the active cycle
   (`Cycle.start_date <= today <= end_date`, or earliest unfinished). For that
   cycle, weeks-to-race = `(race_date - new_start_date).days // 7`. If <
   `MIN_WEEKS_TO_RACE[cycle.sequence]`, refuse → `400 {"detail": "new_start
   would compress <name> to N weeks; minimum is M"}`.
6. **No half-shift allowed.** If any cycle other than the active one would be
   pushed past its race, refuse `400`. (In practice α never causes this
   because cycle 2/3 don't move.)
7. **Concurrency.** If a Plan Adapter proposal is mid-application
   (state == "applied" but `created_at` within last 30s), refuse `409
   {"detail": "plan is mutating; retry"}`.

### Side effects on success (single transaction)

1. UPDATE `planned_workouts.scheduled_date += delta_days` WHERE
   `cycle_id IN (...)` AND `status = 'planned'` AND `scheduled_date >= today`.
2. Mark `planned_workouts.status = 'skipped'` WHERE
   `status = 'planned'` AND `scheduled_date < new_start_date` (these are the
   "abandoned past planned" rows — they sit in the calendar pre-cutover and
   will never be done).
3. UPDATE `cycles.start_date` for cycle 1 (only).
4. UPDATE `plans.start_date`.
5. UPDATE `agent_messages SET proposal_state_json = jsonb_set(..., 'state',
   '"discarded"', 'discard_reason', '"plan_shifted"')` WHERE
   `proposal_state_json->>'state' = 'pending'` AND athlete_id = ...
6. INSERT `plan_history` row.
7. `invalidate_plan_cache(athlete.id)` (per `app/services/plan_aggregator.py:36`).

### Errors

- `400` — invalid date, past date, would-compress-below-min, snapped date
  already equals current start (no-op → return existing plan with
  `shifted_workouts: 0`).
- `404` — no active plan.
- `409` — concurrent mutation in flight.
- `501` — `mode == "reseed"`.

### Audit trail

`plan_history` table (§2) is the canonical audit. We do **not** add columns to
`plans` itself — keeping `plans` the canonical "current state" and history as a
separate append-only ledger is cleaner.

## 6. UX placement

**Settings → Program section** is the natural home. The settings screen
already exists for athlete profile; adding a "Program" subsection keeps
plan-level controls discoverable without polluting the Today / Week / Program
tabs.

```
SETTINGS
├── Profile (existing)
├── HR Zones (existing)
├── Pace Targets (existing)
├── Program  ← NEW
│   ├── Plan: Marathon Trilogy 2026-2027
│   ├── Start date: Apr 13, 2026
│   ├── Active cycle: Phase 1 — MCM (Week 4)
│   ├── [RESET START DATE]   ← button
│   └── Plan history (last 5 changes)
└── Sign out
```

Tapping **RESET START DATE** opens a sheet (`StartDateSheet.tsx`) with:

1. A date picker (anchor: current Mon, range: today → today+12 weeks).
2. **Live impact preview** that fires `POST /plan/start-date/preview`
   (a dry-run sibling endpoint — same handler, returns the summary without
   committing). Updates as the user changes the date.
3. **Two buttons:** `CANCEL` and `CONFIRM RESET`.
4. Confirm pops a second NES-style modal: "PRESS A TO CONFIRM. Y workouts
   shift, Z proposals dropped, W abandoned. NO UNDO."

## 7. Mockup

### Settings → Program panel

```
+--------------------------------------------------+
| ◄ SETTINGS                                       |
+--------------------------------------------------+
|                                                  |
|  PROGRAM                                         |
|  ─────────────────────────                       |
|                                                  |
|  PLAN          Marathon Trilogy 2026-27          |
|  STARTED       APR 13 2026  (3w 4d ago)          |
|  ACTIVE CYCLE  PHASE 1 — MCM                     |
|  CURRENT WEEK  4 of 28                           |
|  NEXT RACE     OCT 25 2026  (172d)               |
|                                                  |
|  ┌──────────────────────────────────────────┐    |
|  │     [ ⟳  RESET START DATE  ]              │    |
|  └──────────────────────────────────────────┘    |
|                                                  |
|  HISTORY                                         |
|  ─────────────────────────                       |
|  (none yet)                                      |
|                                                  |
+--------------------------------------------------+
```

### StartDateSheet — picker + impact preview

```
+--------------------------------------------------+
| RESET START DATE                          [✕]    |
+--------------------------------------------------+
|                                                  |
|  PICK A NEW START (Mondays only)                 |
|                                                  |
|  ◄ MAY 2026 ►                                    |
|  Mo Tu We Th Fr Sa Su                            |
|        1  2  3  4  5                             |
|   6  7  8  9 10 11 12   ← W11 selected           |
|  13 14 15 16 17 18 19                            |
|  20 21 22 23 24 25 26                            |
|  27 28 29 30 31                                  |
|                                                  |
|  ─────────────────────────                       |
|  IMPACT                                          |
|                                                  |
|  ▸ Shift +28 days (was Apr 13 → May 11)          |
|  ▸ 174 planned workouts will move                |
|  ▸ 12 already-completed workouts unchanged       |
|  ▸ 8 already-skipped/moved workouts unchanged    |
|  ▸ 3 abandoned past planned will be marked       |
|    SKIPPED                                       |
|  ▸ 1 pending coach proposal will be discarded    |
|  ▸ Phase 1 will be 24 weeks (min 16) ✓           |
|                                                  |
|  ┌─────────────┐  ┌─────────────────────────┐    |
|  │   CANCEL    │  │   CONFIRM RESET   ►     │    |
|  └─────────────┘  └─────────────────────────┘    |
|                                                  |
+--------------------------------------------------+
```

### Confirmation modal

```
+--------------------------------------------------+
|  ⚠   ARE YOU SURE?                               |
+--------------------------------------------------+
|                                                  |
|  THIS CANNOT BE UNDONE.                          |
|                                                  |
|  • PLAN START   APR 13 → MAY 11, 2026            |
|  • 174 WORKOUTS WILL SHIFT                       |
|  • 1 OPEN COACH PROPOSAL WILL BE DROPPED         |
|                                                  |
|  YOUR EDITS, COMPLETIONS, AND HISTORY            |
|  WILL BE PRESERVED.                              |
|                                                  |
|  ┌─────────────┐  ┌─────────────────────────┐    |
|  │   GO BACK   │  │    YES, RESET (B)       │    |
|  └─────────────┘  └─────────────────────────┘    |
|                                                  |
+--------------------------------------------------+
```

## 8. Component plan

### Mobile (React Native)

- **NEW** `mobile/src/components/StartDateSheet.tsx`
  - Props: `currentStart: ISODate`, `onClose: () => void`, `onConfirmed:
    (summary) => void`.
  - Internal state: `selectedDate`, `previewSummary`, `loading`, `error`.
  - Fires `POST /plan/start-date?dry_run=true` on date change (debounced 250ms).
  - On confirm → second modal → `POST /plan/start-date` (no dry_run) →
    propagate `onConfirmed`.
- **MODIFY** `mobile/src/screens/SettingsScreen.tsx`
  - Add Program section block (new component
    `mobile/src/components/ProgramSettingsBlock.tsx` or inline).
  - Wire RESET button → opens `StartDateSheet`.
  - On `onConfirmed`: show toast, refresh `usePlan()` query, close sheet.
- **MODIFY** `mobile/src/hooks/usePlan.ts` (or create
  `mobile/src/hooks/useResetStartDate.ts`)
  - Add `useResetStartDateMutation` that wraps the POST and invalidates the
    `plan/current`, `plan/full`, `plan/stats`, `plan/today`, `plan/week`
    react-query keys.
  - Add `usePreviewStartDate` for the dry-run preview.
- **NEW** `mobile/src/lib/dates.ts` (if it doesn't exist) with `snapToMonday`,
  `weeksBetween`.

### Backend (FastAPI)

- **NEW** `app/routes/plan.py` additions:
  - `POST /plan/start-date` — body model `PlanStartDateResetIn`, response model
    `PlanStartDateResetOut`. Accepts `?dry_run=true` for preview.
- **NEW** `app/services/plan_shift.py`:
  - `compute_shift_summary(db, athlete_id, new_start_date) -> ShiftSummary`
    (read-only, used for both dry-run and validation).
  - `apply_shift(db, athlete_id, new_start_date) -> ShiftSummary` (writes,
    transactional).
- **NEW** `app/lib/cycle_constants.py`:
  - `MIN_WEEKS_TO_RACE = {1: 16, 2: 8, 3: 9}`.
- **NEW** `app/models/plan_history.py`:
  - `PlanHistory` model per §2.
- **NEW** Alembic migration creating `plan_history`. (Project currently has no
  `migrations/` dir; either start one or extend `schema.sql`.)
- **MODIFY** `app/schemas/plan.py`:
  - Add `PlanStartDateResetIn`, `PlanStartDateResetOut`, `ShiftSummary`.
- **MODIFY** `app/services/plan_aggregator.py`:
  - No code change strictly required; but verify `_active_cycle` still picks
    the right cycle after a shift (it does — it queries by start_date <= today).
- **TESTS** `tests/routes/test_plan_start_date.py`:
  - Happy path shift forward 3 weeks: 174 workouts shift, history row written,
    cache busted.
  - Refuse past date.
  - Refuse compression below min.
  - Pending proposal gets discarded; applied proposal untouched.
  - User-edited workout (with `original_snapshot_json`) shifts but content
    preserved.
  - Completed workout untouched.
  - Reconciliation still resolves to the same planned UUID after shift.
  - Dry-run mode returns identical summary without writing.
  - `mode=reseed` returns 501.
  - Idempotent: same start twice = no-op summary.

## 9. Out of scope (deferred)

- **Per-cycle date adjustment.** Only plan-level start in v1. v2 lets you
  shift cycle 2 or 3 independently (e.g., "I want extra recovery between MCM
  and Disney").
- **Undo / rollback.** `plan_history` records the change but no restore button
  in v1. Manual SQL only.
- **`mode = "reseed"`.** Wipes user edits, returns plan to PLAN.md defaults at
  the new anchor. Returns 501 in v1.
- **Past-date shift.** New start must be `>= today`. v2 may allow shifting
  back when reconciling a missed seed.
- **Compressed taper / peak mode.** If user picks a date that compresses below
  min, v1 refuses. v2 could offer "compressed plan" with explicit acceptance.
- **Bulk re-edit after shift.** User edits travel with their workouts; no
  prompt to revisit them. v2 might surface "your week-3 tempo edit is now in
  week 6 of the new structure — review?".
- **Race-date editing.** Race dates are immutable in v1. (If a marathon gets
  cancelled, that's a different feature.)
- **Multiple plans.** v1 assumes one active plan per athlete. The endpoint
  scopes by `is_active=true`.

## 10. Done criteria

1. `POST /plan/start-date` ships with the validations in §5 and the side
   effects in the same order, in a single transaction.
2. `POST /plan/start-date?dry_run=true` returns the same summary shape without
   writing.
3. All seven happy-path + edge-case tests in §8 pass.
4. After a shift:
   - `GET /plan/current.cycle_progress.week` reflects the new week numbering.
   - `GET /plan/today` returns the workouts that landed on today by the new
     anchor.
   - `GET /plan/full` shows planned workouts on shifted dates and historical
     workouts in their original calendar weeks.
   - `GET /plan/stats` recomputes (cache was busted).
5. `plan_history` has one row per successful reset with full
   before/after/summary JSON.
6. Pending proposals are marked `discarded` with `discard_reason =
   "plan_shifted"`; applied proposals untouched.
7. Mobile Settings → Program panel renders, opens `StartDateSheet`, shows live
   impact preview, and on confirm completes the round-trip with toast +
   refreshed views.
8. NES retro styling consistent with `2026-05-05-workout-edit-and-retro-polish-design.md`
   (block borders, monospace headers, A/B button affordances).
9. Lint (`ruff check && ruff format`) clean. All existing tests still pass.

---

## Open questions for the user

1. **Does shift always travel user edits with the date, or stick edits to the
   calendar?** v1 default: edits travel with the workout (the workout's
   identity moves; its date moves; its edited content moves with it). The
   alternative (edits stick to the calendar) would mean week 3's tempo edit
   stays on the 2026-05-04 Wednesday regardless of which "week" that becomes.
   Travel-with-workout is cleaner; confirm.

2. **Abandoned-past-planned policy.** When new_start is later than today and
   there are planned (never-touched) workouts in the gap between
   today and new_start, do we (a) mark them `skipped` automatically, (b) leave
   them `planned` and let them rot, or (c) hard-delete them? Recommendation:
   (a) `skipped` — keeps `plan/stats` clean and preserves the audit trail. But
   "skipped" implies user choice, which feels wrong; we may want a new status
   `abandoned`. Confirm preference.

3. **Should peak_week_target recompute on shift?** In Option α, week_number
   doesn't change so peak_week_target stays correct. But if we ever ship
   reseed mode, peak_week_target gets re-derived. Confirm: preserve v1, recompute
   v1.1.

4. **Reconciliations to `status='moved'` planned rows.** After a shift, the
   moved workouts stay on their actual calendar dates, but the "planned"
   workouts around them have new dates. A reconciliation that pointed
   completed_X to planned_Y (status=moved) is fine. But the *gap* in the
   planned schedule on the day where status=moved sits could leave
   `plan/today` showing nothing for that day if the moved workout's
   `scheduled_date` is no longer "today". Verify this is the desired UX.

5. **MIN_WEEKS_TO_RACE values (16 / 8 / 9).** These are guesses based on
   PLAN.md's structure (16 ≈ peak + taper for MCM; 8 ≈ Disney peak+taper; 9 ≈
   Delaware peak+taper). Confirm with the coach (or the human running the
   trilogy) before locking in.

6. **Day-of-week alignment.** v1 snaps non-Monday picks to the prior Monday.
   Alternative: snap to the *nearest* Monday (forward or back) to minimize
   delta. Recommendation: prior-Monday because forward-snap could push past
   the user's intent. Confirm.

7. **Reseed mode timeline.** v1.1 ETA — is this needed before any user is
   onboarded, or can it wait until someone actually requests a wipe?
