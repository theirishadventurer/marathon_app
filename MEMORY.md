# Project Memory

## Current Status (2026-05-25, Session 2.9)

**Branch:** `session-2/backend-move-endpoints` (~135 commits ahead of master across Sessions 2 / 2.5 / 2.6 / 2.7 / 2.8 / 2.9)

**State:**
- Backend: 104/104 tests pass, ruff clean. Endpoints unchanged from 2.8. **PLAN.md rewritten to v3.2** — new Phase 1 (22 weeks, Mon=strength_a / Tue-Wed-Thu trail / Fri=strength_b / Sat=long / Sun=recovery), kickoff Mon 2026-05-25. Phase 2/3 preserved as PRELIMINARY. `app/seed/plan_parser.py` `CYCLES[0]` re-anchored to 2026-05-25, 22 weeks.
- Mobile: unchanged from 2.8 (no code edits this sprint).
- DB: re-seeded against v3.2 plan, **322 planned workouts** (was 364 under old v2.0), peak_week_target=20 (was 23). Login `runner@marathon.dev` / `changeme123` (until SEED_PASSWORD patch lands in deploy prep).
- Deploy: **personal deployment runbook authored** at `docs/superpowers/specs/2026-05-24-personal-deployment-runbook.md` — Railway (API + Postgres + 1 GB Garmin-token volume), Vercel (Expo web build → iPhone Safari Add-to-Home-Screen PWA). Runbook ready to execute end-to-end (~2-3h solo).
- Dev: Docker Desktop on Windows/WSL2; volume wipes on `docker compose down` apply doubly when changing plan structure — idempotent seed leaves ghost weeks from old structure, so `docker compose down -v` (destructive) is the canonical re-seed.

**Open:**
- **Personal deployment is the immediate next step** — runbook §0 through §6, then iPhone Add-to-Home-Screen and smoke-test checklist.
- Sessions 2.5–2.9 work not yet merged to `master`. User to smoke-test (and deploy), then merge.
- Cycles 2 (Disney) + 3 (Delaware) need re-anchoring after MCM 2026-10-25 — currently flagged PRELIMINARY in the seed.
- Strava integration is the leading backlog item (OAuth + webhook path) — replaces fragile `garminconnect` scraping; especially relevant once Railway-IP Garmin sync is real-world tested.
- Session 3 design / planning (Daily Coach, Run Analyst, free-form chat) is a later session's brainstorm.
- Tracked mobile follow-ups: 7-day toggle narrow-phone fallback (single-letter codes); `DraggableWeekList` per-day `onDayLayout(date, y)` so the 7-seg toggle can scroll-anchor; PWA-specific UI affordance for slider/flex days (Session 2.9 explicitly deferred this — drag-to-move handles it functionally for now).

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

### Plan / Seed / Deploy (Session 2.9)
- **Pipe-table parser is structure-agnostic.** `_parse_code_block` regex only requires `WEEK N` headers + `Day | type | dist | dur | desc | intent` rows. Switching from a 6-run/week template to a 4-5 run/week template needed zero parser changes — the entire v3.2 integration was PLAN.md content + a one-line `CYCLES[0]` start_date/weeks update. Keep parser dumb; push philosophy into the data file.
- **Seed upsert is idempotent BUT leaks ghost rows.** Upsert key is `(cycle_id, week_number, day)` — when Phase 1 shrunk from 28 → 22 weeks, old W23-28 rows survived the re-run. `docker compose down -v` (wipes pgdata) is the canonical local re-seed for structural plan changes. On Railway, a fresh deploy starts empty so there's no ghost problem; for a future in-place re-seed write a one-off `app/seed/reset_planned.py` that deletes only `planned_workouts WHERE status='planned'` for a given athlete (preserve `completed_workouts`, `reconciliations`, `plan_history`).
- **`SEED_PASSWORD` env var was declared in `app/config.py` but never read.** `app/seed/load_plan.py:24` had `DEFAULT_PASSWORD = "changeme123"` hardcoded. Caught while authoring the deploy runbook — fix is `DEFAULT_PASSWORD = os.environ.get("SEED_PASSWORD", "changeme123")` so Railway env can drive it. Watch for similar "declared but unused" config drift in other settings fields.
- **Railway Postgres URL scheme adapter.** Plugin injects `DATABASE_URL=postgresql://...` but SQLAlchemy async needs `postgresql+asyncpg://...`. Patch in `Settings.__init__`: if it starts with `postgresql://`, rewrite the scheme. Same env var works locally (Docker) and on Railway with no orchestration layer.
- **iOS personal-install economics.** Apple Developer Program ($99/yr) gives clean TestFlight + 1-year ad-hoc installs. Free Apple ID needs 7-day re-signs. PWA via Expo web → Vercel → Safari "Add to Home Screen" avoids both: fullscreen + custom splash + your icon, no signing. Tradeoff: bottom-sheets / drag-to-move / `expo-secure-store` need web-fallback consideration (most already handled in this codebase).
- **Garmin tokens are on-disk state.** `./data/garmin_tokens/<athlete_id>/tokens.json` — on Railway, mount a 1 GB volume at `/app/data` or every redeploy silently breaks Garmin sync (tokens vanish, scraper tries fresh login, hits Garmin auth wall).
- **`EXPO_PUBLIC_*` env vars are inlined into the JS bundle.** Visible to any client. Fine for API base URL; never for secrets. Vercel UX shows them in the env panel like any other var so it's easy to forget the distinction.

## Reference

- Spec template: `docs/superpowers/specs/<date>-<slug>-design.md`
- Plan template: `docs/superpowers/plans/<date>-<slug>.md`
- Auto session log (per-branch): `docs/session-logs/<date>-<branch>.md` (written by `.claude/helpers/session-log.mjs` on SessionEnd)
