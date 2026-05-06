# Workout Edit + NES Retro Polish — Design

**Status:** approved (pending user review of this doc)
**Date:** 2026-05-05
**Owner:** session lead (CBell)
**Branch target:** new feature branch off `master` after current Session 2 work merges

## 1. Goal

Let the athlete edit a planned workout when reality diverges from the plan
("today says Strength A, I actually ran"), without losing the original or
breaking reconciliation. Ship it on a full NES-classic retro restyle of the
mobile app so the product feels distinct and "ready to start using."

## 2. User story

> As the athlete, I open Today and see Strength A planned. I tap **EDIT**,
> pick **Easy run**, optionally tweak distance/duration, and confirm.
> Today now shows Easy run with a small "was: STRENGTH A" tag. The app
> immediately asks: "Where should the original Strength A go?" — I pick
> Friday or tap **DROP IT**. If I picked a day, the AI rebalance
> proposal opens to optionally rearrange the rest of the week.

## 3. Scope

### In scope

- Edit any **planned** or **moved** workout (today or future).
- Editable fields via quick-pick: `type`, with auto-fill of `family`,
  `distance_mi`, `duration_min`, `title` from per-type defaults.
- Override of those auto-fills via an expandable "Tweak stats" section.
- Single-shot displaced-original flow: pick a day this week or drop it.
  Day-pick triggers the existing AI rebalance (`/move` proposal flow).
- Full NES-classic retro restyle of the mobile app: login, today, week,
  workout-detail, settings, all sheets (Why / Edit / Displaced / Proposal).

### Out of scope (deferred)

- Editing past, completed, or skipped workouts.
- Edit-history audit trail beyond the *very first* original snapshot.
- Bulk edits across multiple days.
- Editing AI-authored `intent_md` or `description_md`.
- Calendar (month) view — already on the backlog.
- Sound effects / chiptune (skip for now; haptics carry the feel).

## 4. Data model

Single additive change to `planned_workouts`:

| Field | Type | Notes |
|---|---|---|
| `original_snapshot_json` | JSONB nullable | Captures `{type, family, distance_mi, duration_min, title, target_pace, target_hr_zone}` from before the *very first* edit. Set on the first PATCH that mutates any of those fields. **Never overwritten** on subsequent edits. |

No new statuses, no displaced rows. "Displaced" is a UX concept; if the
user picks a day in the displaced flow, a fresh `planned_workouts` row is
created on the spot (cloned from the snapshot). If the user drops it, no
extra row exists.

The Garmin reconciler is unaffected — it still matches completed
workouts against the *current* planned values, which now reflect what
actually happened.

### Pydantic / API surface

Extend `PlannedWorkoutOut` with an optional `original_snapshot` field
that exposes the JSONB content (or `null`).

## 5. Backend endpoints

### `PATCH /workouts/{id}` (new)

```
Body:
{
  "type"?: string,           // one of the allowed quick-pick types
  "distance_mi"?: number | null,
  "duration_min"?: number | null,
  "title"?: string
}
Response: PlannedWorkoutOut  (with original_snapshot populated)
Errors:
  400 — unknown type, distance/duration out of range
  401 — no auth
  403 — workout not owned by athlete
  404 — workout not found
  409 — workout status is `done` or `skipped`
```

Server logic:

1. Load workout, verify athlete ownership.
2. Reject if `status` ∈ {`done`, `skipped`}.
3. If `original_snapshot_json` is NULL **and** any of `type / distance_mi
   / duration_min / title` differs from current value, snapshot current
   values into the JSONB column.
4. Validate `type` against the allowed set; recompute `family` from
   `type` (single source of truth — existing `app/lib` mapping).
5. Apply only fields present in the request body (Pydantic
   `exclude_unset` semantics — keys not in the JSON body don't change).
6. Commit, return the updated row.

The response uses `PlannedWorkoutOut` extended with one new optional
field `original_snapshot: dict | None` exposing the JSONB content. This
schema change ships with the migration.

### `POST /workouts/{id}/reschedule-original` (new)

```
Body: { "new_date": "YYYY-MM-DD" }
Response: { new_workout_id: UUID, proposal: ProposalOut }
Errors:
  400 — workout has no original_snapshot_json (never edited)
  400 — new_date outside parent's cycle
  401 / 403 / 404 as above
```

Server logic:

1. Load source workout; require `original_snapshot_json` non-null.
2. Insert a new `planned_workouts` row at `new_date` with fields cloned
   from the snapshot. Carry `cycle_id`, `week_number` from source.
   `original_date = new_date`. `description_md = source.description_md`,
   `intent_md = source.intent_md` (these aren't in the snapshot but are
   on the source; we keep the original prescription text).
   `status = planned`.
3. Run the existing Plan Adapter agent (same as `/move`) over the new
   placement, persist to `agent_messages`, return the proposal.
4. Cancellation: handled via the existing
   `POST /workouts/{newId}/apply-move` with `choice: "cancel"`.
   Cancel must additionally **delete the just-created row** so a
   discarded reschedule doesn't leave an orphan. (This is a small
   extension to the existing apply-move endpoint — when the proposal's
   workout was created by reschedule-original, cancel deletes it.)

### Allowed quick-pick types

Defined as a frozen set on the backend so unknown types are rejected and
the type→family mapping stays deterministic:

| `type` | `family` | default `distance_mi` | default `duration_min` |
|---|---|---|---|
| `easy_run` | `running` | 5.0 | 50 |
| `tempo` | `running` | 6.0 | 55 |
| `long_run` | `running` | 12.0 | 120 |
| `intervals` | `running` | 6.0 | 50 |
| `strength_a` | `strength` | null | 45 |
| `strength_b` | `strength` | null | 45 |
| `cross` | `other` | null | 45 |
| `rest` | `other` | null | 0 |

Defaults are *suggestions* the mobile sheet pre-populates when a user
taps a quick-pick; the user can override before confirming. The backend
trusts whatever the client sends.

### Tests

- Edit Strength A → Easy Run: snapshot captured, family flips, second
  edit doesn't overwrite snapshot.
- Edit a workout with `status = done` → 409.
- Reschedule-original creates a new row + returns proposal.
- Apply-move with `choice: "cancel"` on a reschedule-created row deletes
  the row.
- Reschedule-original on a row with no snapshot → 400.
- Edit with unknown type → 400.

## 6. Mobile UX

### NES retro tokens

Replace / extend `theme/tokens.ts`:

| Token | Value | Use |
|---|---|---|
| `bg` | `#0d0d12` | Screen background |
| `bgPanel` | `#11142a` | Card / sheet background (deep-navy) |
| `bgPanelAlt` | `#1a1d3d` | Alternating rows |
| `ink` | `#f4f4ec` | Primary text (cream) |
| `inkDim` | `#9a9aab` | Secondary text |
| `accentRun` | `#5cd86c` | Running family — green |
| `accentStrength` | `#e8a23a` | Strength family — mustard |
| `accentRest` | `#5b8cff` | Rest / cross — blue |
| `accentDanger` | `#e84a4a` | Skip / destructive — red |
| `accentHi` | `#f7d51d` | Selection / today highlight — yellow |
| `line` | `#000000` | All borders, hard 2px solid |

Typography (loaded via `expo-font`):
- `PressStart2P-Regular` for headings, button labels, status pills.
- `VT323-Regular` for body copy, descriptions, numeric values.

Helpers:
- `nesShadow` — adds `box-shadow: 2px 2px 0 #000` (web) and Android
  `elevation` 0 + iOS `shadow*` for the offset hard shadow.
- `pressable` — wrapper that translates content `(1px, 1px)` and removes
  shadow on press to mimic a mechanical click.
- `Easing.steps(4)` baked into a `stepEasing` helper for any animations.

### Components — new

- `EditQuestSheet.tsx` — bottom sheet with quick-pick grid + expandable
  "Tweak stats" form.
- `DisplacedSheet.tsx` — chained sheet that opens after EditQuest
  succeeds, showing 7 day buttons + DROP IT.
- `RetroButton.tsx`, `RetroPill.tsx`, `RetroCard.tsx`, `RetroBorder.tsx`
  — primitives every screen uses, so the look is one place.
- `theme/retro.ts` — token + font + helper exports.

### Components — restyled (full app, flavor 1)

- `LoginScreen.tsx` — pixel logo, monospace inputs, NES dialog buttons.
- `TodayScreen.tsx` — header reads `▸ TODAY  05/05`. Coach brief panel
  styled like an in-game tip box. Recent runs strip becomes a "RECENT
  QUESTS" rail.
- `WeekScreen.tsx` — week header with cursor caret on today. Day cards
  re-bordered, type icons on each WorkoutCard.
- `WorkoutDetailScreen.tsx` — quest-sheet aesthetic; planned-vs-actual
  becomes a stat block.
- `SettingsScreen.tsx` — menu list with `>` cursor on hover/focus.
- `WorkoutCard.tsx` — square corners, hard shadow, type icon (8x8
  pixel SVG), brackets around status pill (`[ PLANNED ]`).
- `WhySheet.tsx`, `ProposalSheet.tsx` — restyled to match
  EditQuest/Displaced.

### Hooks — new

- `useEditWorkout` — wraps PATCH. Compares `original_snapshot` on the
  pre-edit row vs the post-edit response: if it was `null` before and
  non-`null` after, this edit was the *first* one and DisplacedSheet
  should open. Otherwise (subsequent edits) no DisplacedSheet.
- `useRescheduleOriginal` — wraps POST `/reschedule-original`; returns
  `{ new_workout_id, proposal }` so ProposalSheet can drive the existing
  apply-move flow against `new_workout_id`.

### Edit flow (mockup)

```
┌─ EDIT QUEST ─────── [X] ─┐
│                            │
│ QUICK PICK                 │
│ [🏃 EASY ] [🏃 TEMPO ]     │
│ [🏃 LONG ] [⚡ INTERVAL ]  │
│ [💪 STR-A] [💪 STR-B  ]    │
│ [🤸 CROSS] [😴 REST   ]    │
│                            │
│ ▸ TWEAK STATS         [+]  │
│   distance:  [ 5.0 ] mi    │
│   duration:  [ 50  ] min   │
│   title:     [ Easy run  ] │
│                            │
│ [   CANCEL   ] [ CONFIRM ] │
└────────────────────────────┘
```

### Displaced prompt (mockup)

```
┌─ DISPLACED: STRENGTH A ───┐
│ Where should it go?        │
│                            │
│ [MON][TUE][WED][THU]       │
│ [FRI][SAT][SUN]            │
│                            │
│ [   DROP IT   ]            │
└────────────────────────────┘
```

After a day-pick, the existing ProposalSheet (now NES-styled) opens
with the AI rebalance options.

### WorkoutCard with snapshot

```
▸ EASY RUN · 5MI                ↻
  was: STRENGTH A
  [ PLANNED ]  5.0mi  50min
```

The `↻` is a pixel "swapped" badge. Tap → small popover showing the
full snapshot (type / distance / duration).

## 7. Build sequence

Run backend + mobile in parallel via the SendMessage-First Coordination
pattern from `CLAUDE.md`. Three named workers:

1. **`backend-dev`** —
   a. Alembic migration adding `original_snapshot_json`.
   b. Extend `PlannedWorkoutOut` with `original_snapshot` field;
      regenerate `mobile/openapi.json`.
   c. PATCH endpoint + tests.
   d. POST reschedule-original endpoint + tests.
   e. Mark reschedule-created rows (cheapest tag: a sentinel in the
      proposal's `proposal_state_json`, e.g. `"created_by":
      "reschedule_original"`); extend apply-move cancel to look up that
      sentinel and delete the new row when present.
   f. Update `app/schemas/plan.py` exports.

2. **`mobile-dev`** —
   a. `theme/retro.ts` + `expo-font` setup.
   b. `RetroButton/Pill/Card/Border` primitives.
   c. Restyle existing screens & cards (TodayScreen, WeekScreen,
      WorkoutDetailScreen, SettingsScreen, LoginScreen, WorkoutCard,
      WhySheet, ProposalSheet).
   d. New `EditQuestSheet`, `DisplacedSheet`.
   e. New `useEditWorkout`, `useRescheduleOriginal` hooks.
   f. Wire EDIT button onto WorkoutCard + WorkoutDetail.

3. **`tester`** — backend pytest run + mobile typecheck after each
   slice; integration smoke test of the full edit→displaced→proposal
   flow once both sides are green.

Reviewer pass at the end before merge.

## 8. Risks / open items

- **Reanimated 4 web stability** — drag-to-move on web has
  not been smoke-tested; if it's flaky, we accept and move on (native
  iOS/Expo Go is the canonical target).
- **Font loading on web** — `expo-font` web support is solid but worth
  validating the `Press Start 2P` bundle size. Fallback is system mono.
- **Cancel-deletes-row** behavior on apply-move is a behavior shift
  for the existing endpoint. Backend tests must cover both paths
  (existing-workout cancel — preserves; new-workout cancel — deletes)
  to avoid regressing the drag-move flow.
- **Auto-fill defaults** are the backend's table — if the user wants
  different per-type defaults (e.g. easy_run = 4mi not 5), it's a
  one-line table edit, no schema change.

## 9. Done criteria

Backend:
- [ ] Migration applied, `original_snapshot_json` column exists.
- [ ] `PATCH /workouts/{id}` works for all editable fields and snapshots
      first edit only.
- [ ] `POST /workouts/{id}/reschedule-original` creates a row + returns
      a proposal that integrates with the existing apply-move flow,
      including cancel-deletes-row.
- [ ] All existing Session 1 + Session 2 tests still pass.
- [ ] `ruff check` + `ruff format --check` pass.

Mobile:
- [ ] `tsc --noEmit` clean.
- [ ] EditQuestSheet quick-pick changes the workout with one tap;
      "Tweak stats" overrides distance/duration/title.
- [ ] After confirm, DisplacedSheet appears (only when a snapshot was
      populated by this edit) with day picker + DROP IT.
- [ ] Day-pick → ProposalSheet → all four choices (option_a/b,
      just_move, cancel) work and the cancel path deletes the
      auto-created row.
- [ ] DROP IT and dismiss leave no orphan rows.
- [ ] WorkoutCard shows "was: X" tag whenever `original_snapshot` is
      set.
- [ ] Full app NES restyle visible on every screen and sheet.

Quality:
- [ ] Manual smoke test: login → edit today's workout → displaced flow
      → cancel; second pass with apply-rebalance; third pass with
      drop-it.
- [ ] App still works on iPhone via Expo Go (the canonical target,
      since web has Reanimated quirks).
