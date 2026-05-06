# Project Memory

## Current Status (2026-05-06, Session 2.6)

**Branch:** `session-2/backend-move-endpoints` (~60 commits ahead of master across Sessions 2 / 2.5 / 2.6)

**State:**
- Backend: 61/61 tests pass, ruff clean. Endpoints: auth, plan/today, plan/week, plan/current, **plan/full**, **plan/stats**, workouts CRUD + move/apply-move/reschedule-original/skip, garmin reauth/status/sync, metrics/recent.
- Mobile: smoother-NES restyle (rounded soft borders, phosphor green + cyan accent, no offset shadows), edit feature + Program tab + Weekly Mileage Tracker all wired end-to-end. Typecheck clean.
- DB: seeded plan (Marathon Trilogy 2026–2027), 3 cycles, 364 planned workouts. Login `runner@marathon.dev` / `changeme123`. Seeder now sets `Cycle.peak_week_target` per cycle from the longest non-race long run.
- Dev: Docker Desktop on Windows/WSL2; volume gets wiped on `docker compose down` so re-migrate + re-seed after each cycle.

**Open:**
- Session 2.5 work not yet merged to `master`. User to smoke-test, then merge.
- Session 3 design / planning (Daily Coach, Run Analyst, free-form chat) is the next session's brainstorm.

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

### Process / Workflow
- **TDD discipline pays off** for backend changes — pytest red→green per task surfaced bugs early (e.g., the alias→validation_alias bug, the enum-coercion artifact).
- **Subagent dispatches** work well per-task; for ~30 small mechanical tasks (mobile retro restyles), batching 4–5 into one dispatch saves context without losing rigor.
- **Plan's "append to file" pattern can violate ruff E402** — hoist imports up after the implementer follows the spec verbatim.
- **`/update-notion` is Claude-side**, can't be triggered from a hook. Run it manually at session close-out per the global CLAUDE.md protocol.

## Reference

- Spec template: `docs/superpowers/specs/<date>-<slug>-design.md`
- Plan template: `docs/superpowers/plans/<date>-<slug>.md`
- Auto session log (per-branch): `docs/session-logs/<date>-<branch>.md` (written by `.claude/helpers/session-log.mjs` on SessionEnd)
