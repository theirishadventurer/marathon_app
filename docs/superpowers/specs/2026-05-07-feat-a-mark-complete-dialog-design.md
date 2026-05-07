# Feat A — Manual mark-complete + workout-data dialog — Design

**Status:** Draft for review
**Date:** 2026-05-07
**Owner:** session lead (CBell)
**Branch:** `session-2/backend-move-endpoints` (doc only)
**Sibling features:** Feat B (sync surfacing — see §7), Feat C (start-date picker), Feat D (visual polish)

---

## 1. Goal & user story

> As the athlete, I just finished a 5-mile easy run without my Garmin. I tap
> **MARK DONE** on today's workout, fill in 5.0 mi / 50 min / target pace,
> save. The plan now shows it as completed.

Today the only path to "done" is `POST /admin/sync` reading from Garmin
(`app/routes/admin.py:12`, `app/services/garmin_sync.py:107`). The
reconciler then pairs the Garmin activity to a planned row by date+family
(`app/services/reconciler.py:52-89`). When the athlete runs without a watch
or rides a stationary bike no path exists — the workout sits as `planned`
forever and eventually flips to `skipped` after the day passes
(`app/services/reconciler.py:106-132`).

**Outcome of Feat A:** the athlete can mark any planned workout as
completed in one tap + one short form, and the system records a real
`CompletedWorkout` + `Reconciliation` so analytics, comparison panels, and
future agent reviews work the same as Garmin-sourced completions.

---

## 2. UX placement

Three candidates for where the **MARK DONE** button lives.

| Option | Where | Pros | Cons |
|--------|-------|------|------|
| (a) Card-only | Inline on every `WorkoutCard`, third button next to `WHY?` and `EDIT` (`mobile/src/components/WorkoutCard.tsx:97-118`) | Fast — one tap from Today / Week | Card already crowded; encourages logging on stale cards mid-week |
| (b) Detail-only | Footer of `WorkoutDetailScreen` next to `Skip workout` (`mobile/src/screens/WorkoutDetailScreen.tsx:250-263`) | Card stays clean; full prescription visible while logging — reduces "wrong workout" mis-logs | Two taps from Today (open card → detail → mark done) |
| (c) Both | Primary on detail, secondary on card | Best of both | Doubles the affordance the user has to learn; tempting to make the card button the primary tap target and skip detail entirely |

**Recommendation: (b) Detail-only for v1.**
Rationale:

1. The detail screen already owns the "this workout is done" affordance —
   `Skip workout` lives there (`WorkoutDetailScreen.tsx:257-262`). Pairing
   `MARK DONE` next to it gives a clean dual choice: did it / didn't do it.
2. The user sees the full prescription (distance, pace target, intent) on
   the same screen they're filling in actuals, which makes the comparison
   meaningful and reduces "I marked the wrong workout done" errors.
3. The card already has 3 buttons (`WHY?`, `EDIT`, status pill); adding a
   fourth pushes it past the one-thumb-glance budget.
4. We can revisit (c) once Feat D's visual polish lands and we know how
   much room a fourth button on the card actually costs.

**Trigger row** in `WorkoutDetailScreen` becomes (left to right): `MARK DONE`
(primary tone) · `Skip workout` (danger tone). Both are hidden /
disabled when `planned.status` is already `done` or `skipped`.

---

## 3. Dialog form — `LogCompletedSheet` fields

Bottom-sheet pattern, mirrors `EditQuestSheet` (`mobile/src/components/EditQuestSheet.tsx:66-149`).
Snap points `['55%', '90%']` — shorter than EditQuestSheet because there's
no quick-pick grid.

### Fields by family

| Field | running | strength / cross / rest | Notes |
|-------|---------|--------------------------|-------|
| Distance (mi) | **required** | hidden | Decimal-pad input; pre-filled from `planned.distance_mi` |
| Duration (min) | **required** | **required** | Number-pad; pre-filled from `planned.duration_min` |
| Avg pace (mm:ss / mi) | optional | n/a | If blank, server derives from distance ÷ duration |
| Avg HR (bpm) | optional | optional | "more" expander |
| Notes (markdown) | optional | optional | "more" expander; multi-line |

### Visual default vs. expander

By default the sheet shows **only the two required fields** for the family,
pre-filled from the planned row. Everything else lives behind a single
collapsible row labelled `▸ MORE STATS` (matching the `▸ TWEAK STATS`
pattern in `EditQuestSheet.tsx:117-121`). This keeps the "I just finished,
log it fast" path to: open sheet → glance at pre-fill → tap **DONE**.

### Non-running workouts

For `family == "strength"` or `family == "other"` the sheet hides the
Distance row entirely and pre-fills Duration from `planned.duration_min`.
If the planned row is `rest` we should not surface MARK DONE at all (rest
= absence of activity; nothing to log).

### Notes destination

Notes live on `reconciliations.deviation_notes_md` rather than on
`completed_workouts`. Three reasons:

1. The reconciliation row is the "what happened vs. what was planned"
   record (`app/models/reconciliation.py:39`). User commentary fits there.
2. The reconciler already populates `deviation_notes_md` for Garmin
   matches in session 3 (per `WorkoutDetailScreen.tsx:108-115` rendering it).
   Reusing the same field keeps the UI rendering path one-branched.
3. `completed_workouts` is the activity record — keeping it free of
   user-typed prose preserves it for objective summaries (raw_summary_json
   stays the source-of-truth for Garmin-side data).

---

## 4. Backend endpoint — `POST /workouts/{id}/log-completed`

### Request body

```jsonc
{
  "distance_mi": 5.0,        // required for running, omitted otherwise
  "duration_min": 50,        // always required
  "avg_pace_s_per_km": 415,  // optional; omit if mobile didn't compute
  "avg_hr": 148,             // optional
  "notes": "felt sluggish"   // optional, markdown
}
```

Schema lives in `app/schemas/workout.py` next to `CompletedWorkoutOut`:

```python
class LogCompletedRequest(BaseModel):
    distance_mi: Decimal | None = None
    duration_min: int                        # required
    avg_pace_s_per_km: int | None = None
    avg_hr: int | None = None
    notes: str | None = None
```

Validate `duration_min > 0`; validate `distance_mi >= 0` if provided;
validate `len(notes) <= 4000` to bound markdown payload.

### Server logic

Pattern is a hybrid of `skip_workout` (`app/routes/workouts.py:80-99`) and
the reconciler's "exact match" path (`app/services/reconciler.py:78-89`):

1. **Look up + auth** — same join as every other route in the file:
   `select(PlannedWorkout).join(Cycle).join(Plan).where(id == workout_id, athlete_id == athlete.id)`.
   404 if not found.
2. **State guard** — if `planned.status in (done, skipped)`, raise 409
   with `detail="Cannot log completion for a {status} workout"` (mirrors
   the edit_workout guard at `app/routes/workouts.py:141-145`).
3. **Family guard** — if `planned.type == WorkoutType.rest`, raise 400.
4. **Family-specific input check** — if `planned.family == running` and
   `distance_mi is None`, 400.
5. **Build `CompletedWorkout`** with:
   - `athlete_id = athlete.id`
   - `garmin_activity_id = <see §4.1>`
   - `activity_date = planned.scheduled_date`
   - `started_at = datetime.combine(planned.scheduled_date, time.min, tzinfo=UTC)` — midnight on the scheduled day
   - `activity_type = _activity_type_for_planned(planned.type)` (e.g. `easy → "running"`, `strength_a → "strength_training"`)
   - `family = planned.family`
   - `duration_s = body.duration_min * 60`
   - `distance_m = body.distance_mi * MI_TO_M` if provided, else `None`
   - `avg_hr = body.avg_hr`
   - `avg_pace_s_per_km = body.avg_pace_s_per_km` if provided; else if both distance and duration present, derive `(duration_s / (distance_m / 1000))`
   - `raw_summary_json = {"source": "manual", "logged_at": "...", "input": <body>}`
6. **Build `Reconciliation`** with:
   - `athlete_id = athlete.id`
   - `planned_id = planned.id`
   - `completed_id = completed.id`
   - `match_confidence = Decimal("1.00")`
   - `deviation_notes_md = body.notes or ""`
7. `planned.status = WorkoutStatus.done`
8. `await db.commit()` then `invalidate_plan_cache(athlete.id)`
   (`app/services/plan_aggregator.py`, used by every other workouts route).

### Response

```python
class LogCompletedResponse(BaseModel):
    planned: PlannedWorkoutOut
    completed: CompletedWorkoutOut
    reconciliation: ReconciliationOut
```

This shape is symmetric with `WorkoutDetailOut`
(`app/schemas/workout.py:42-46`) so the mobile client can drop it into the
detail-screen state directly without a re-fetch.

### 4.1 The `garmin_activity_id` problem

`completed_workouts.garmin_activity_id` is `BigInteger NOT NULL UNIQUE`
(`app/models/workout.py:105`). Three options:

| Option | What it is | Risk |
|--------|------------|------|
| **A — Make nullable** | `nullable=True`; manual logs store `NULL`. Drop unique constraint or allow many NULLs. | Postgres allows multiple NULLs in a UNIQUE column by default, so the constraint stays mostly intact. Tiny migration. Cleanest semantic. |
| B — Negative sentinel | Reserve `id < 0` for manual logs, e.g. `-int(uuid4().int >> 96)` to dodge collisions. | Bit-twiddling hack; future readers will be confused; fragile if Garmin ever returns negative IDs. |
| C — Sentinel `0` | Single shared sentinel. | Breaks the UNIQUE constraint immediately — can't have two manual logs. Non-starter. |

**Recommendation: Option A (make nullable).** New alembic migration:

```python
# alembic/versions/<rev>_completed_workouts_nullable_garmin_id.py
def upgrade() -> None:
    op.alter_column(
        "completed_workouts",
        "garmin_activity_id",
        existing_type=sa.BigInteger(),
        nullable=True,
    )

def downgrade() -> None:
    # Best-effort; will fail if any NULL rows exist
    op.alter_column(
        "completed_workouts",
        "garmin_activity_id",
        existing_type=sa.BigInteger(),
        nullable=False,
    )
```

Update `CompletedWorkout.garmin_activity_id` to `Mapped[int | None]` and
`CompletedWorkoutOut.garmin_activity_id: int | None`. The Garmin-sync path
(`app/services/garmin_sync.py:135-162`) still always populates it.

The `existing_ids` lookup at `garmin_sync.py:127-132` is unaffected — it
filters by `garmin_activity_id.in_(garmin_ids)` and `NULL` rows simply
don't match.

---

## 5. Reconciler interaction

**Scenario:** athlete logs 5-mi easy manually at 6 PM. Next morning they
remember to plug in their Garmin and `POST /admin/sync` pulls the same
run.

The `reconcile()` function only touches `unmatched_completed`
(`app/services/reconciler.py:31-42`) and `unreconciled_planned`
(`app/services/reconciler.py:60-62`). After Feat A's manual log, the
planned row is already `status = done` and is already referenced by a
`Reconciliation`. So:

1. The new Garmin `CompletedWorkout` row is in `unmatched_completed`.
2. The candidates query filters
   `PlannedWorkout.status.in_([planned, moved])`
   (`app/services/reconciler.py:60`) — our manually-completed planned row
   is `done`, so it's **excluded**.
3. The Garmin row hits the "0 candidates" branch
   (`app/services/reconciler.py:66-77`) and is recorded as a **bonus**
   (unscheduled run): `Reconciliation(planned_id=NULL, completed_id=garmin_row.id)`.

Net behaviour for v1: **manual log wins; Garmin activity becomes a bonus
run.** This is the simplest behaviour, falls out of the existing reconciler
with zero code changes, and is correct in spirit: if the user logged
manually they presumably wanted that data shown, and the Garmin import is
extra/duplicate.

The three options framed in the brief, evaluated:

| Option | Fits today | Verdict |
|--------|------------|---------|
| **Manual wins; Garmin is bonus** | Yes — current reconciler does this for free | ✅ ship in v1 |
| Garmin replaces manual | Requires deleting the manual `CompletedWorkout` + `Reconciliation` and re-creating; non-trivial; loses user notes | Defer |
| Prompt user to merge | Needs new UI + state machine + offline merge resolution | Defer |

**Caveat documented as a v2 task:** if a user manually logs and then
syncs, they'll see a bonus run that's actually a duplicate. We'll add a
"merge / dismiss" affordance in a later session once the Reconciliation
review surface lands. Tracked in §9.

---

## 6. ASCII mockup — `LogCompletedSheet`

```
+-------------------------------------------+
|       LOG COMPLETED                       |
|       was planned: easy run 5.0mi 50min   |
|                                           |
|  +-------------------+ +----------------+ |
|  |  DISTANCE (MI)    | |  DURATION (MIN)| |
|  |  +-------------+  | |  +-----------+ | |
|  |  |  5.0        |  | |  |  50       | | |
|  |  +-------------+  | |  +-----------+ | |
|  +-------------------+ +----------------+ |
|                                           |
|  > MORE STATS                             |
|                                           |
|  +-----------+              +-----------+ |
|  |  CANCEL   |              |   DONE    | |
|  +-----------+              +===========+ |
+-------------------------------------------+
```

Expanded state (after tapping `▾ MORE STATS`):

```
+-------------------------------------------+
|       LOG COMPLETED                       |
|       was planned: easy run 5.0mi 50min   |
|                                           |
|  DISTANCE (MI)        DURATION (MIN)      |
|  [ 5.0 ]              [ 50 ]              |
|                                           |
|  v MORE STATS                             |
|  AVG PACE (MM:SS / MI)                    |
|  [ 10:00            ]                     |
|  AVG HR (BPM)                             |
|  [ 148              ]                     |
|  NOTES                                    |
|  +---------------------------------------+|
|  | felt sluggish; wind from the east     ||
|  +---------------------------------------+|
|                                           |
|  [  CANCEL  ]            [    DONE    ]   |
+-------------------------------------------+
```

Tokens come from `colors`/`fontFamily` already used by `EditQuestSheet`
(`PressStart2P` 8pt for labels, `VT323` 18pt for inputs, `colors.line`
2 px borders). Will adopt Feat D polish in parallel without code changes
to this sheet.

For strength / cross workouts the Distance row is omitted; everything
else is identical.

---

## 7. "Sync" button surfacing

Right now Garmin sync is a button buried in `mobile/src/screens/SettingsScreen.tsx`
(reachable from the gear tab). Two complementary surfaces are warranted:

1. **Today screen header** — small `SYNC` icon-button in the top-right of
   `TodayScreen`, alongside the date. Pulls Garmin once; shows a toast
   `Synced N activities`. Triggers `POST /admin/sync` (existing endpoint;
   `app/routes/admin.py:12`). This is the right placement because "I just
   finished a run with my watch and want it to show up" is a Today-screen
   intent.
2. **Inside `LogCompletedSheet`** — secondary text link
   `or sync from Garmin →` under the form. Tapping closes the sheet and
   fires the same `/admin/sync` mutation. This satisfies the brief's "sync
   button as an alternative to MARK DONE" requirement and gives a graceful
   exit if the user opens the sheet then realises they had their watch on.

We do **not** put a sync button on every `WorkoutCard` — that's noise.
Settings keeps its sync button as the canonical "sync now + see last sync
status" affordance.

### Backend impact

Zero. The existing `POST /admin/sync` (and `SyncReportOut` schema) are
sufficient. Mobile gets a `useSync` mutation hook in
`mobile/src/api/hooks/useSync.ts` (new file).

---

## 8. Component plan

### Mobile

**New**

- `mobile/src/components/LogCompletedSheet.tsx` — bottom sheet, snap
  `['55%', '90%']`, fields per §3, ref-forwarded like
  `EditQuestSheet.tsx:37`.
- `mobile/src/api/hooks/useLogCompleted.ts` —
  `useLogCompleted()` mutation; on success invalidates `['plan']` and
  `['workout', workoutId]` (mirrors `useSkipWorkout` at
  `mobile/src/api/hooks/useWorkouts.ts:20-31`). Posts to
  `/workouts/{id}/log-completed`.
- `mobile/src/api/hooks/useSync.ts` — wraps `POST /admin/sync`; surfaces
  loading state for header pill.

**Modify**

- `mobile/src/screens/WorkoutDetailScreen.tsx` — add `MARK DONE` button
  to the footer alongside `Skip workout` (`WorkoutDetailScreen.tsx:250-263`).
  Wire to `LogCompletedSheet` ref via a small extension to `useEditFlow`
  *or* a separate `useLogFlow` hook (lean toward the latter — Feat A is
  scoped enough to warrant its own hook rather than bloating
  `useEditFlow`).
- `mobile/src/screens/TodayScreen.tsx` — header `SYNC` pill calling
  `useSync` (§7).
- `mobile/src/api/types.ts` — add
  `LogCompletedRequest`, `LogCompletedResponse`. These will land
  automatically once `scripts/export_openapi.py` is re-run after the
  backend route exists (per session 2's mobile-types pipeline; see
  recent commit `c23d70f`).

**Untouched**

- `WorkoutCard.tsx` — no new buttons in v1.
- `EditQuestSheet.tsx`, `useEditFlow.ts` — different flow.

### Backend

**New**

- `app/routes/workouts.py` — append `POST /workouts/{id}/log-completed`
  handler per §4. ~70 lines, fits the file's existing pattern.
- `app/schemas/workout.py` — `LogCompletedRequest`, `LogCompletedResponse`.
- `alembic/versions/<rev>_completed_workouts_nullable_garmin_id.py` — see
  §4.1.
- `app/lib/activity_type.py` (or extend
  `app/lib/workout_family.py`) — small `activity_type_for_planned(t: WorkoutType) -> str`
  helper that mirrors how Garmin's `typeKey` would have populated
  `CompletedWorkout.activity_type` for the same family.

**Modify**

- `app/models/workout.py:105` — `garmin_activity_id` → `Mapped[int | None]`,
  `nullable=True`.
- `app/schemas/workout.py:17` — `garmin_activity_id: int | None`.

**Tests** (`tests/routes/test_workouts.py` — extend existing file)

- Happy path: log running workout → 200, `planned.status == done`,
  `Reconciliation` exists with `match_confidence == 1.00`.
- 409 when planned is already `done`.
- 409 when planned is already `skipped`.
- 400 when running workout has no `distance_mi`.
- 400 when planned is `rest`.
- 404 when workout id belongs to another athlete.
- Notes round-trip into `reconciliations.deviation_notes_md`.
- Cache invalidation called.
- Reconciler integration: after manual log + later Garmin sync of same
  date, the Garmin row becomes a bonus (not re-attributed).

---

## 9. Out of scope (deferred)

- **Logging completions for past dates** — v1 only handles "log today's
  done". The route accepts any planned id but mobile only surfaces the
  button for today / future-but-not-too-future. Past-date logging is a
  v2 nice-to-have (rationale: easier to reason about reconciler
  interactions if the manual-log flow only operates on still-`planned`
  workouts the user expected to do today).
- **Editing an already-logged completion** — needs a PATCH endpoint and a
  separate edit sheet. v1 forces user to skip-and-relog if they fat-finger.
- **Bulk-log** ("I missed a week, mark these all skipped/done") — out.
- **Manual-vs-Garmin merge UI** — see §5; deferred to the same session
  that ships the reconciliation review surface.
- **Strava / Apple Health import** — separate session.

---

## 10. Done criteria

For an engineer picking this up:

- [ ] Alembic migration adds `nullable=True` to
  `completed_workouts.garmin_activity_id`; `alembic upgrade head` clean
  on a fresh DB and on a DB with existing Garmin rows.
- [ ] `CompletedWorkout.garmin_activity_id` typed `int | None` in the model.
- [ ] `CompletedWorkoutOut.garmin_activity_id` typed `int | None` in the
  schema.
- [ ] New schemas `LogCompletedRequest`, `LogCompletedResponse` in
  `app/schemas/workout.py`.
- [ ] New `POST /workouts/{id}/log-completed` route in
  `app/routes/workouts.py` implementing §4.
- [ ] `app/lib/activity_type.py` (or equivalent helper) maps
  `WorkoutType` → string used in `CompletedWorkout.activity_type`.
- [ ] Tests in `tests/routes/test_workouts.py` cover all 8 cases listed
  in §8.
- [ ] `scripts/export_openapi.py` re-run; `mobile/src/api/types.ts` shows
  the two new types.
- [ ] `LogCompletedSheet.tsx` renders per §3 / §6, behaves correctly for
  running vs. strength vs. cross.
- [ ] `useLogCompleted` mutation invalidates `['plan']` and
  `['workout', id]`.
- [ ] `WorkoutDetailScreen` exposes `MARK DONE` next to `Skip workout`,
  hidden when status is `done` or `skipped`.
- [ ] `TodayScreen` exposes a header `SYNC` pill driving
  `POST /admin/sync` via `useSync`.
- [ ] `LogCompletedSheet` shows "or sync from Garmin →" link that closes
  the sheet and fires `useSync`.
- [ ] Manual log + subsequent Garmin sync of same date results in: planned
  stays `done` linked to manual completion, Garmin row reconciled as
  bonus (verified by reconciler integration test).
- [ ] `ruff check` + `ruff format` clean; mobile `tsc --noEmit` clean;
  `pytest` green.

---

## Open questions

1. **Pace input format on the form** — the brief lists pace as a string
   like `"10:45"` (mm:ss / mi) but the API stores `avg_pace_s_per_km`. We
   should accept the user's mm:ss string in mobile, parse to s/km, and
   send the integer. Confirm the user-facing unit is min/mile (US) and
   not min/km.
2. **`started_at` precision** — using midnight on `scheduled_date` is
   honest ("we don't know when") but leaks into the comparison panel
   (`WorkoutDetailScreen.tsx:57-93`) which doesn't surface start time
   anyway. If we ever do, we should reconsider.
3. **Should `TodayScreen` SYNC pill auto-fire on screen focus?** Probably
   not in v1 (cost, rate-limit risk), but worth a discussion with Feat B.
4. **Is "MARK DONE" the right copy?** The retro tone in the rest of the
   app (`EDIT QUEST`, `PROGRAM`, `LOADING…`) suggests `LOG QUEST` or
   `MARK COMPLETE`. Recommend deferring to the visual-language pass in
   Feat D.
