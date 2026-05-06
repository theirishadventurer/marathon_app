# Marathon App — Project Tracker

## Current Sprint

| Sprint | Status | Branch | Notes |
|---|---|---|---|
| Session 1 — Backend foundation + Garmin sync | ✅ Done | merged | JWT auth, plan parser, reconciler, Garmin service |
| Session 2 — Mobile app + drag-to-move + Plan Adapter | ✅ Done | `session-2/backend-move-endpoints` | Backend move endpoints + Expo TS scaffold + drag-to-move |
| Session 2.5 — Workout edit + NES retro polish | ✅ Done | `session-2/backend-move-endpoints` | In-place workout edit, displaced-original flow, full NES restyle |
| Session 3 — Daily Coach, Run Analyst, free-form chat | ⏳ Backlog | — | See `SESSION_3.md` |

## Sprint History

### Session 2.5 — Workout Edit + NES Retro Polish (2026-05-05 → 2026-05-06)

**Goal:** Let the athlete edit a planned workout in place when reality diverges from the plan ("today says Strength A, I actually ran"), with a chained "displaced original" prompt and AI rebalance. Ship on a full NES-classic retro restyle of the mobile app.

**Status:** ✅ Complete. 33/33 plan tasks shipped, 37 commits, 47/47 backend tests green, mobile typecheck clean.

**Key deliverables:**

Backend (`app/`):
- `original_snapshot_json` JSONB column on `planned_workouts`
- `PATCH /workouts/{id}` (snapshots first edit, recomputes family)
- `POST /workouts/{id}/reschedule-original` (clones snapshot, fires AI rebalance)
- Apply-move cancel deletes reschedule-created rows via `proposal_state_json.created_by` sentinel
- `propose_rebalance()` accepts `created_by` kwarg
- `PlannedWorkoutOut.original_snapshot` field

Mobile (`mobile/`):
- Press Start 2P + VT323 fonts via `expo-font`
- NES classic palette (navy bg, cream ink, color-coded family accents)
- Retro primitives: `RetroBorder`, `RetroButton`, `RetroPill`, `RetroCard`, `theme/retro.ts`
- Full app restyle: Login, Today, Week, WorkoutDetail, Settings, all sheets, bottom tabs
- New: `EditQuestSheet`, `DisplacedSheet`
- New: `useEditWorkout`, `useRescheduleOriginal`, `useEditFlow` hooks
- EDIT button on every WorkoutCard, wired into Today/Week/WorkoutDetail

**Spec:** `docs/superpowers/specs/2026-05-05-workout-edit-and-retro-polish-design.md`
**Plan:** `docs/superpowers/plans/2026-05-05-workout-edit-and-retro-polish.md`

**Commit range:** `c3db0c8..b4b3a73` (37 commits on `session-2/backend-move-endpoints`)

**Notable lessons:**
- Pydantic v2 `Field(alias=...)` makes the alias the OUTPUT key when FastAPI serializes via `response_model`. Use `Field(validation_alias=...)` if you want input mapping but output to use the field name. (Caught by B1's first integration test.)
- Test ergonomic gotcha: shared `AsyncSession` between test client and route returns the raw `str` you set on an enum-typed column, not the coerced enum. Use `WorkoutStatus.done` not `"done"` when mutating fixtures.
- Plan's `Append to file` pattern can introduce ruff E402 (module-level import not at top) — hoist imports up after each "append" task.
- `react-native@0.81` `EasingStatic` doesn't expose `steps`; use `react-native-reanimated`'s `Easing.steps` instead.
- Docker compose `down` wipes the named volume on Windows/WSL backend — re-migrate + re-seed after each restart.

### Session 2 — Mobile App + Drag-to-Move (2026-05-04)

Backend move endpoints + Plan Adapter agent (commits `333e602..884d8c8`), mobile B1–B12 (commits `3ebb444..dc47483`), auto session-log hook (commit `f15cc79`). Drag-to-move on Week tab with AI rebalance proposal.

### Session 1 — Foundation (earlier)

JWT auth, plan parser/seeder, reconciler matching completed→planned, Garmin sync service with reauth/status/admin endpoints. See git log under `7acf367..91f08ab`.
