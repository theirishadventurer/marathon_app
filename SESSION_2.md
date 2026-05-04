# Session 2 — Mobile App + Drag-to-Move + Plan Adapter

> **Paste this entire file into Claude Code as the opening message.**
> Read `SPEC.md`, `PLAN.md`, and re-skim `SESSION_1.md` for context on
> what's already built. Then propose your build order and **stop for
> confirmation before writing code.**
>
> **Prerequisite:** Session 1 done. Backend running locally via
> `docker compose up`. Plan loaded. Reconciler working.

---

## Goal

By the end of this session I should be able to:

1. Open the app on my iPhone via Expo Go
2. Log in and see today's workout
3. Tap the "Why?" button on a workout and read its `intent_md` rationale
4. Open the Week view and see all 7 days of the current week with
   planned + completed runs inline
5. **Long-press a planned workout, drag it to a new day, drop it.** Feel
   haptics. See the AI propose 2-3 rebalance options in a sheet. Pick one.
   See it commit and the week re-render.
6. Hit "Just move it" to override the AI and move without rebalancing
7. Hit "Cancel" and see the visual revert

---

## Scope: what you build

### Part A — Backend additions

#### A1. Move endpoints
- `PATCH /workouts/{id}/move`
  - Body: `{new_date: "YYYY-MM-DD"}`
  - Response: `{proposal_id: UUID, options: [AdapterOption], summary: str}`
  - **Does not commit the move yet.** Stores the proposal in
    `agent_messages` (`agent='plan_adapter'`, `proposal_state_json`
    contains the original date, new date, and options).
- `POST /workouts/{id}/apply-move`
  - Body: `{proposal_id: UUID, choice: "option_a" | "option_b" | "just_move" | "cancel"}`
  - Behavior:
    - `cancel` → no DB changes, mark proposal as `discarded` in
      `proposal_state_json`
    - `just_move` → update workout's `scheduled_date` to the proposed
      new_date, set `status='moved'`, no other changes
    - `option_a` / `option_b` → apply the structured edits described in
      that option (see "Plan Adapter contract" below)
- `PATCH /workouts/{id}/skip` → set `status='skipped'`

#### A2. Plan Adapter agent (real, not stubbed)

This is the first real agent. It does *not* use `build_athlete_context()`
yet (that's session 3). For session 2, build a focused context:

```python
class PlanAdapterContext(TypedDict):
    workout: PlannedWorkoutDict        # the one being moved
    proposed_new_date: date
    week_workouts: list[PlannedWorkoutDict]    # all workouts in the affected week(s)
    cycle_info: dict                   # name, race_date, week of cycle
    plan_philosophy: str
    decision_rules: list[str]          # from PLAN.md
    recent_completed: list[dict]       # last 7 days
```

Anthropic call:
- Model: `claude-sonnet-4-5` or current Sonnet
- System prompt: coach persona + the philosophy + the decision rules
- User message: structured description of the move, ask for 2-3 rebalance
  options
- **Response format: structured JSON via tool use.** Define a tool
  `propose_rebalance` with this schema:
  ```json
  {
    "summary": "string — 1-2 sentence read on the move",
    "options": [
      {
        "id": "option_a",
        "label": "string — short name",
        "tradeoff": "string — what this prioritizes",
        "edits": [
          {"workout_id": "...", "field": "scheduled_date", "new_value": "..."},
          {"workout_id": "...", "field": "status", "new_value": "skipped"}
        ],
        "rationale": "string — why this works"
      }
    ]
  }
  ```
- The "just move it" option is always synthesized client-side; the agent
  only proposes A and B.
- Persist the full request/response in `agent_messages` with the schema.

#### A3. Plan Adapter contract (apply logic)
- An option's `edits` are a list of structured field mutations
- Server validates each edit:
  - `field` must be one of `scheduled_date`, `status`
  - `workout_id` must belong to the same athlete
  - `new_value` for `scheduled_date` must be a valid date string
  - `new_value` for `status` must be `planned | moved | skipped`
- All edits in an option apply atomically in a transaction
- Each moved workout sets `status='moved'`; `original_date` never changes

#### A4. OpenAPI export
- Add a script `scripts/export_openapi.sh` that writes the FastAPI OpenAPI
  spec to `mobile/openapi.json` so the RN app can generate types from it

---

### Part B — Mobile app

#### B1. Project skeleton
```
mobile/
├── app.json
├── package.json
├── tsconfig.json              (strict mode)
├── babel.config.js
├── tailwind.config.js
├── App.tsx
├── openapi.json               (committed; refreshed via script)
└── src/
    ├── api/
    │   ├── client.ts          (axios + JWT interceptor)
    │   ├── types.ts           (generated from openapi.json via openapi-typescript)
    │   └── hooks/             (one file per resource: usePlan, useWorkouts, ...)
    ├── auth/
    │   ├── AuthContext.tsx
    │   └── secure-store.ts
    ├── screens/
    │   ├── LoginScreen.tsx
    │   ├── TodayScreen.tsx
    │   ├── WeekScreen.tsx
    │   ├── WorkoutDetailScreen.tsx
    │   └── SettingsScreen.tsx
    ├── components/
    │   ├── WorkoutCard.tsx
    │   ├── DayCard.tsx
    │   ├── WhySheet.tsx
    │   ├── ProposalSheet.tsx
    │   └── DraggableWeekList.tsx
    ├── hooks/
    │   └── useDragMove.ts
    ├── lib/
    │   ├── dates.ts
    │   └── format.ts
    └── theme/
        └── tokens.ts          (colors, spacing — even though using Tailwind)
```

#### B2. Setup
- `npx create-expo-app -t expo-template-blank-typescript mobile`
- Add deps:
  - `react-native-reanimated`, `react-native-gesture-handler`
  - `@shopify/flash-list`
  - `expo-haptics`, `expo-secure-store`
  - `@tanstack/react-query`, `axios`
  - `nativewind`, `tailwindcss`
  - `openapi-typescript` (devDep)
  - `react-navigation/native`, `@react-navigation/native-stack`,
    `@react-navigation/bottom-tabs`
- TypeScript strict mode on
- Tailwind config with a small custom palette (see `theme/tokens.ts`)
- TypeGen script: `npm run gen-types` → reads `openapi.json`, writes
  `src/api/types.ts`

#### B3. Auth
- Login screen: email + password, calls `POST /auth/login`, stores JWT in
  `expo-secure-store`
- `AuthContext` provides `token`, `login()`, `logout()`
- `axios` instance attaches `Authorization: Bearer <token>` from secure store
- 401 response → clear token + redirect to login

#### B4. Navigation
- Bottom tabs: Today, Week, Chat (placeholder for session 3), Settings
- Modal stack for: Workout Detail, "Why?" sheet, Proposal sheet

#### B5. Today screen
- Top: date string + "What's on tap"
- Coach brief card (placeholder text "Coach brief — wired in session 3")
- Today's planned workout card(s)
- Recent completed runs strip (last 5, horizontal scroll)
- Pull-to-refresh

#### B6. Workout card component
- Title (e.g., "Long run · 18mi")
- Type pill colored by family (running/strength/other)
- Pace target / HR zone
- Status pill (planned/moved/skipped/done)
- Tap → Workout Detail screen
- Long-press handle (only on Week screen, for drag)
- "Why?" button → opens WhySheet

#### B7. Why sheet
- Bottom sheet showing the workout's `intent_md` rendered as markdown
- Includes: prescription detail, intent paragraph, the cycle context
  ("This is week 14 of Phase 1, peak mileage week 23 is 22mi long run.")

#### B8. Week screen
- FlashList of 7 day-cards (Mon-Sun)
- Each day-card shows:
  - Day name + date
  - Each planned workout for that day as a WorkoutCard
  - Each completed run for that day as a small completed-card (smaller, muted)
- Header: week-of-N indicator, jump-to-today button
- Swipe horizontally on header (or buttons) to navigate weeks
- Pull-to-refresh

#### B9. Drag-to-move
This is the hardest piece. Use `react-native-reanimated` v3 + `gesture-handler`.

Behavior spec:
- Long-press (~300ms) on a planned WorkoutCard → haptic light, card lifts
  (scale 1.05, shadow appears)
- While dragging:
  - Card follows finger
  - Hovered day-card highlights
  - Other workouts in that day shift down
- Release on a different day:
  - Haptic medium
  - Card snaps to a placeholder position in the new day
  - Optimistic UI update (the card visually moves immediately)
  - Backend call: `PATCH /workouts/{id}/move` with `new_date`
  - Spinner appears in a small corner of the card while the proposal loads
  - When proposal returns → ProposalSheet opens
- Release on the same day → no-op, snap back
- Release on a rest day → allowed (you can move work onto a rest day)

Implementation notes:
- Don't use `DraggableFlatList` — its drag model is for reorder, not
  cross-bucket move. Build with raw gesture-handler + reanimated.
- Use `runOnJS` to call the React Query mutation
- Persist optimistic state via React Query's `onMutate` + `setQueryData`
- On error, roll back with `setQueryData`

#### B10. Proposal sheet
- Bottom sheet, dismissable
- Shows:
  - Summary line ("You moved Tuesday's tempo to Wednesday — that lands
    next to Thursday strength.")
  - 2 option cards (A and B), each with:
    - Label (e.g., "Drop Wed strength volume")
    - Tradeoff line
    - Rationale (collapsed, expandable)
    - "Apply" button
  - "Just move it" button — applies move with no rebalance
  - "Cancel" button — reverts the visual move
- On Apply / Just move → call `POST /workouts/{id}/apply-move`, dismiss
  sheet, refetch week
- On Cancel → roll back optimistic state, dismiss

#### B11. Workout Detail screen
- Full description rendered as markdown
- Intent block
- If completed: comparison panel
  - Planned distance vs actual distance
  - Planned target pace vs actual avg pace
  - Planned HR zone vs actual avg HR
  - Elevation gain
- Reconciliation section:
  - Match confidence
  - Deviation notes
  - Analyst review (placeholder "Wired in session 3")
- Skip button (with confirmation)

#### B12. Settings screen
- "Reconnect Garmin" — opens form to enter Garmin email/password, calls
  `POST /garmin/reauth`
- Sync status block: last sync time, "needs reauth" warning if true,
  manual sync button
- Athlete info: name, email, plan name, current cycle
- Logout button

---

## Out of scope (explicitly NOT this session)

- ❌ Daily Coach (session 3)
- ❌ Run Analyst (session 3)
- ❌ Free-form chat (session 3)
- ❌ APScheduler — sync still manual via `/admin/sync`
- ❌ Push notifications
- ❌ Polish pass on empty states, skeletons, animations beyond the drag

Coach brief and analyst review on screens stay as placeholder text. The
*structure* should be there so session 3 just wires data in.

---

## Constraints

1. **TypeScript strict mode.** No `any`. No untyped function returns.
2. **All RN screens are functional components with hooks.** No class
   components.
3. **All API calls go through React Query.** No naked `useEffect + axios`.
4. **The drag must feel native.** That means:
   - 60fps during drag (use Reanimated worklets, not setState in handlers)
   - Haptic feedback on lift, hover-over-day, drop
   - Physics-driven snap-back, not abrupt
5. **OpenAPI types must regenerate cleanly** — the script must be runnable
   without errors after backend changes.
6. **Don't add Redux, Zustand, MobX, or any other state lib.** React Query
   + Context is enough.

---

## Working style

1. Read `SPEC.md`, `PLAN.md`, skim `SESSION_1.md`
2. Verify the backend from session 1 still runs end-to-end
3. Propose build order: I'd suggest A1-A4 first (backend additions), then
   B1-B12. Don't start mobile until backend `/move` and `/apply-move` work
   via curl with stub agent responses (real agent in A2).
4. Stop and confirm before coding.
5. Commit after each major piece.
6. Smoke-test on a real iPhone via Expo Go, not just simulator. Drag
   gestures behave differently on real devices.

---

## Done criteria checklist

Backend additions:
- [ ] `PATCH /workouts/{id}/move` calls Plan Adapter, returns proposal
- [ ] `POST /workouts/{id}/apply-move` correctly applies edits per option
- [ ] `PATCH /workouts/{id}/skip` works
- [ ] Plan Adapter persists request/response in `agent_messages`
- [ ] Edit validation rejects bad workout_ids or fields
- [ ] Atomic transaction — no partial application
- [ ] OpenAPI export script works
- [ ] All session 1 tests still pass; new tests cover move, apply-move,
      validation

Mobile:
- [ ] App opens on my iPhone via Expo Go
- [ ] Login flow works end-to-end with real backend
- [ ] Today screen shows today's workouts
- [ ] Week screen shows 7 days correctly
- [ ] "Why?" sheet displays intent_md properly
- [ ] Drag-to-move feels smooth (haptics, lift, hover, drop)
- [ ] Proposal sheet displays AI options legibly
- [ ] All four proposal actions (A, B, just_move, cancel) work
- [ ] Optimistic UI rolls back on error
- [ ] Workout Detail shows planned + completed comparison correctly
- [ ] Settings → Garmin reauth works against real Garmin
- [ ] Logout clears token and returns to login

Quality:
- [ ] `pytest` green on backend
- [ ] `ruff check` and `ruff format --check` pass
- [ ] `tsc --noEmit` passes on mobile (no TS errors)
- [ ] No console warnings in RN runtime
- [ ] App works on the real iPhone, not just simulator

---

## First action

Confirm you've read `SPEC.md` and `PLAN.md`. Verify session 1 backend is
healthy (`docker compose up`, hit `/plan/today`). Propose your build order.
Wait for approval.
