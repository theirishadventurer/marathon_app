# Project Memory

## Current Status (2026-05-08, Session 2.8)

**Branch:** `session-2/backend-move-endpoints` (~131 commits ahead of master across Sessions 2 / 2.5 / 2.6 / 2.7 / 2.8)

**State:**
- Backend: untouched this sprint. 104/104 tests pass, ruff clean. Endpoints: auth, plan/today/week/current/full/stats/start-date, workouts CRUD + move/apply-move/reschedule-original/skip/log-completed, workouts/completed/recent, garmin reauth/status/sync, metrics/recent.
- Mobile: Staycation IA + visual overhaul shipped. BrandBanner on every content screen. Today uses `TODAY | TOMORROW` DayToggle; Week uses 7-seg `MON…SUN`. WorkoutCard rewritten (no inline Why/Edit; chevron affordance). Tab bar active-pill (filled phosphor green). WorkoutDetail uses BrandBanner + Back/Edit chip row + BottomActionBar. WhySheet retired. Typecheck clean.
- DB: seeded plan (Marathon Trilogy 2026–2027), 3 cycles, 364 planned workouts. Login `runner@marathon.dev` / `changeme123`. `plan_history` table records reseed events.
- Dev: Docker Desktop on Windows/WSL2; volume gets wiped on `docker compose down` so re-migrate + re-seed after each cycle.

**Open:**
- Sessions 2.5–2.8 work not yet merged to `master`. User to smoke-test, then merge.
- Strava integration is the leading backlog item (OAuth + webhook path) — replaces fragile `garminconnect` scraping.
- Session 3 design / planning (Daily Coach, Run Analyst, free-form chat) is the next session's brainstorm.
- Tracked follow-ups: 7-day toggle narrow-phone fallback (single-letter codes); `DraggableWeekList` per-day `onDayLayout(date, y)` so the 7-seg toggle can scroll-anchor.

## Cross-Session Lessons

### Backend / Pydantic / SQLAlchemy
- **Pydantic V2 `alias` vs `validation_alias`:** `Field(alias=X)` makes the alias the JSON output key when FastAPI's `response_model` serializes. If you want input-only mapping (read from ORM column `foo_json` but emit JSON key `foo`), use `Field(validation_alias=X)`. The wire contract follows the Python field name then.
- **`from_attributes=True` + `populate_by_name=True`:** input semantics — Pydantic accepts both names. Output behavior is independent and depends on `by_alias` / which alias type was used.
- **Native enum columns + shared session:** if a test mutates `obj.status = "raw_string"` and commits via the same session the route reads from, the route gets the raw string back, NOT the coerced enum. Either use the enum value in tests (`WorkoutStatus.done`) or `await session.refresh(obj)` to force re-coercion.
- **Alembic autogenerate trap:** if `alembic_version` table exists but the schema doesn't (drifted dev DB), autogenerate will think every existing table needs to be created. Run `alembic stamp base && alembic upgrade head` to sync, then autogenerate the new migration.
- **`docker compose down` wipes named volumes** on Windows WSL backend in this project — always plan to re-migrate + re-seed after a full restart.

### Mobile / Expo / React Native
- **`react-native@0.81` `EasingStatic` lacks `Easing.steps`** — use `react-native-reanimated`'s `Easing.steps` if you need step-based easing.
- **`expo-secure-store` throws on web in SDK 54.** Wrap with `Platform.OS === 'web'` fallback to `localStorage`.
- **Reanimated config plugin:** don't add `react-native-reanimated` to `app.json` plugins — it has no `app.plugin.js`. The babel plugin is enough.
- **`useFonts` from `expo-font`:** combine with `expo-splash-screen` to gate render until both fonts load; otherwise UI flickers between system font and pixel font.
- **CORS for web demo:** `expo start --web` runs on a different origin than the FastAPI backend. Permissive `CORSMiddleware(allow_origins=["*"])` is fine for local dev.
- **JSX namespace:** with React 19 + TS 5.9, don't annotate `: JSX.Element` on component returns — it errors. Let TS infer.
- **NativeWind v4 + Tailwind aliases:** keep both `colors.bgCard` (legacy alias) and `colors.bgPanel` (new) when migrating palette tokens — avoids breaking existing className consumers mid-refactor.

### Backend / Service patterns
- **Cache umbrella `invalidate_for_athlete(athlete_id)`** in `app/services/cache_invalidation.py` is the single bust point. Every mutation handler calls it. Per-route caches (plan_full, plan_stats, recent_completed, coach_brief) register their `_clear_*` helpers via lazy import to avoid circular deps.
- **Reseed > delta-shift for start-date changes.** Per athlete preference: when reseeding, KEEP completed/skipped within the new range, DELETE incomplete planned (including user edits — accepted tradeoff), re-emit fresh from parser. Audit captured in `plan_history` table.
- **`plan_parser` accepts `cycle_one_start_date` override.** When set, drops earliest template weeks to fit the shortened cycle. Race date stays anchored.
- **`POST /plan/start-date?dry_run=true`** for preview before commit. The mobile sheet uses this to show impact (planned dropped, completed kept, proposals discarded) before the user confirms.
- **Manual `POST /workouts/{id}/log-completed`** writes a `CompletedWorkout` with `garmin_activity_id=NULL` (column is nullable now), match_confidence 1.0. Reconciler is unchanged — it only matches against `planned`/`moved`, so a manually-logged `done` row is invisible to it (Garmin syncs that arrive later are recorded as bonus, no double-match).
- **Coach brief is heuristic, not LLM.** `app/services/coach_brief.py` composes 1-3 sentences from today's prescription + yesterday's completion + last-5-days adherence + days-to-race. ≤280 chars. Returns `None` only when there's nothing useful to say.

### Mobile / Navigation
- **Composite navigation prop typing.** When a tab screen needs to push onto the root stack (e.g., Program → WorkoutDetail), use `CompositeNavigationProp<BottomTabNavigationProp<TabParamList, '...'>, NativeStackNavigationProp<RootStackParamList>>` — without this you can't call both `navigate('Tabs', { screen: 'Week', params })` and `navigate('WorkoutDetail', { workoutId })` from the same screen.
- **`noUncheckedIndexedAccess` everywhere.** All `array[i]` reads return `T | undefined`. Use `?? fallback` patterns. The mobile codebase has this enabled in tsconfig and it consistently catches off-by-one bugs at typecheck.
- **`useRoute<RouteProp<TabParamList, 'Week'>>()`** is how you read tab-level route params. Used for `initialDate` on the Week tab so Program-tab tile-taps navigate cleanly.

### Backend / Caching
- **Per-athlete in-process cache + explicit busts** is the right shape for read-heavy aggregators on a single-worker FastAPI deployment. 60s TTL is generous; bust on every mutation handler that touches `planned_workouts`. Don't over-engineer with Redis until ≥10 athletes.
- **Pydantic v2 `Literal` types** serialize as plain strings via `model_dump`, round-trip through FastAPI / OpenAPI / openapi-typescript without ceremony. Use them for status/scope/kind enums.
- **`select_from(PlannedWorkout)` is required** when a `select(...).join(Reconciliation).join(CompletedWorkout)` selects only fields from `CompletedWorkout` — without the explicit anchor, SQLAlchemy infers FROM as `completed_workouts` and the chained joins leave `planned_workouts` unjoined.

### Design / UX
- **`SectionHeader` cyan mixed-case mono w/ `▸` caret** is the legibility win over `PressStart2P fontSize 8` all-caps headers. Pixel font for headers below 10pt is unreadable on smaller phones.
- **Soft borders (1px slate) + 4–6px corners + no offset shadow** reads as polished retro without looking dated. The lifted bgPanel tone provides elevation; hard offset shadows stack visually and flatten hierarchy.
- **Filled-rounded badge variant** for family/platform tags (NES/SNES style); bracket-style `[ PLANNED ]` reserved for status text where the matrix-terminal vibe still works.

### Mobile / Navigation v7 quirks
- **react-navigation v7 selected-tab signal is `aria-selected`**, not `accessibilityState.selected` (the v6 prop). When wiring a custom `tabBarButton` to render an active-pill behind the icon+label, read `props['aria-selected']` (typed as `boolean | undefined`) — the old prop never fires under v7 and the pill stays dark.
- **`SafeAreaView` + `BottomActionBar` interaction.** When a screen ends in a sibling-layout BottomActionBar that already adds `insets.bottom` to its own padding, wrap the screen `SafeAreaView` with `edges={['top']}`. Default edges double-pad the home indicator and visually push the action bar up by the same amount twice.

### Mobile / Text rendering
- **`firstSentence` extractor needs markdown strip + `?` terminator + bare-punct guard.** A subline cut from a richer description (markdown bold/italics, multi-sentence) needs all three or you ship `**Tempo run**` literal markers, miss `?` endings, or trail off with a stray `,`/`-`. Caught by manual smoke on the rewritten WorkoutCard, not by typecheck.

### Process / Workflow
- **TDD discipline pays off** for backend changes — pytest red→green per task surfaced bugs early (e.g., the alias→validation_alias bug, the enum-coercion artifact).
- **Subagent dispatches** work well per-task; for ~30 small mechanical tasks (mobile retro restyles), batching 4–5 into one dispatch saves context without losing rigor.
- **Plan's "append to file" pattern can violate ruff E402** — hoist imports up after the implementer follows the spec verbatim.
- **`/update-notion` is Claude-side**, can't be triggered from a hook. Run it manually at session close-out per the global CLAUDE.md protocol.

## Reference

- Spec template: `docs/superpowers/specs/<date>-<slug>-design.md`
- Plan template: `docs/superpowers/plans/<date>-<slug>.md`
- Auto session log (per-branch): `docs/session-logs/<date>-<branch>.md` (written by `.claude/helpers/session-log.mjs` on SessionEnd)
