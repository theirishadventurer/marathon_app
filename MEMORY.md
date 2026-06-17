# Project Memory

## Current Status (2026-06-16, Session 3.1)

**Branch:** `master` — Session 3 is merged and LIVE in production. Railway has `APP_ENV=production` + `SECRET_KEY` + `SEED_PASSWORD` + `GEMINI_API_KEY` set; fail-closed checks pass on boot. Live login `runner@marathon.dev` (athlete `7ff7b20e-…`) rotated to the `SEED_PASSWORD` value via `app.scripts.reset_password` run through `railway ssh`.

**Session 3.1 (this session) — production activation + coach behavior fix:**
- **Activated Session 3 in prod.** The chat + fail-closed config was never merged; `master` had only the old chat stub. Merged `session-3/coach-chat` → `master` (`c613725`) — that push is what actually shipped coach chat + security hardening + the iOS scroll fix. Set the four Railway env vars first (correct order — fail-closed needs the values present).
- **Coach over-proposing fix (`68765b8`).** Live use showed the coach firing plan-change proposals instead of conversing. Root cause: function-calling AUTO mode + a system prompt with no "when to propose" policy. Fixed by adding an explicit converse-first / propose-only-on-request policy (plus a periodic plain-text reminder that the plan can be adjusted) to `COACH_SYSTEM_PROMPT`. Behavior fix still needs a live smoke-test (external model, mocked in tests).
- **Global CLAUDE.md** gained an SDLC Principles section (test-with-code, maintainability, secure coding, full-arc thinking).
- **Repo hygiene:** removed 46 junk untracked files; flagged `docs/household-financial-platform-spec_1.md` (a different project's spec) for relocation.

**Prior — Session 3 (2026-05-30 → 31):**
- **Coach Chat shipped** — free-form Gemini (`gemini-2.5-flash`) coach on the Chat tab: live athlete context, persistent `user_chat` thread, and `propose_plan_change` function-calling that reuses the proposal/apply machinery via a new shared `proposal_apply` service (with §3.2 per-edit ownership re-validation). Backend 128 tests pass in-container; mobile `tsc` clean. Not yet runtime-smoke-tested (needs live `GEMINI_API_KEY` + device).
- **Security hardening** — public-URL audit found default `SECRET_KEY` + `SEED_PASSWORD` with no enforcement. Added `APP_ENV=production`-gated fail-closed checks; `app/scripts/reset_password.py` for live-row rotation. No IDOR (routes scope by `Plan.athlete_id`). **User must set Railway `APP_ENV`/`SECRET_KEY`/`SEED_PASSWORD`/`GEMINI_API_KEY` + rotate the live athlete password before/at merge.**
- **Scroll bug** — fixed inverted `scrollEnabled` in `WeekScreen.tsx` (iPhone Safari couldn't scroll back up after reaching the bottom).

**Prior status (2026-05-26, Session 2.10):**

**State:**
- Backend: 106/106 tests pass, ruff clean. Live on Railway at `https://marathonapp-production-cc63.up.railway.app`. Boot chain: `alembic upgrade head` → idempotent `python -m app.seed.load_plan` → uvicorn on `$PORT`. Postgres plugin linked via Variable Reference; 1 GB volume mounted at `/app/data` for Garmin tokens.
- Web/Mobile: live on Vercel at `https://marathon-app-livid.vercel.app`. Installed as PWA on iPhone Safari (Add to Home Screen) — fullscreen, dark navy splash, app icon.
- DB: 322 planned workouts seeded against v3.2 plan. Login `runner@marathon.dev` / whatever `SEED_PASSWORD` was at first Railway seed.
- 6/7 iPhone PWA smoke-test bugs fixed (Session 2.10): workout edit body refresh, DayToggle scroll-anchor, Tweak stats default open, Week shows actuals when done, bottom nav layout, drag-and-drop touch-web. #7 (Garmin sync) is environmentally blocked — Garmin's WAF 429s the Railway datacenter IP — defensive error handling shipped, real fix is Strava migration.
- Dev: Docker Desktop on Windows/WSL2 still primary for local iteration. Tests run in container.

**Open:**
- **Strava integration moved from "nice to have" to "needed"** — Garmin sync is environmentally blocked from Railway. Until Strava OAuth ingestion is built, "completed" runs are manual-only via MARK DONE flow.
- `BOOT:` diagnostic logging in `app/main.py` + `railway.json` could be backed out (low-priority cleanup; served its purpose during the deploy saga).
- Cycles 2 (Disney) + 3 (Delaware) need re-anchoring after MCM 2026-10-25 — currently flagged PRELIMINARY in the seed.
- Session 3 design / planning (Daily Coach, Run Analyst, free-form chat) is a later session's brainstorm.
- Tracked mobile follow-ups: 7-day toggle narrow-phone fallback (single-letter codes); PWA-specific UI affordance for slider/flex days (Session 2.9 explicitly deferred; drag-to-move handles it functionally).

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

### Deploy Execution + Bug Batch + Retro (Session 2.10)

- **Railway startCommand parser is partial-shell.** It supports `&&` for chaining but does NOT shell-expand `${VAR:-default}` POSIX syntax cleanly. Plain `$PORT` substitution is inconsistent too. Always wrap in explicit `sh -c '...'` when you need guaranteed shell semantics. (Burned ~30 min and 3 deploy cycles on this — exactly the anti-pattern systematic-debugging.md warns about: candidate fixes without evidence-gathering instrumentation between attempts.)
- **Diagnostic logging BEFORE the next candidate fix.** When the platform is opaque (Railway in this case), add `echo "BOOT: PORT=$PORT"` + a FastAPI lifespan logger line — one deploy will tell you whether shell expansion works AND whether uvicorn imported the app. The cost of an extra `echo` line is far less than the cost of three sequential guesses.
- **Railway default healthcheckTimeout 30s is too short.** Cold-start migrations + uvicorn boot on managed Postgres can exceed it. Bump to 300 in `railway.json`.
- **Branch matters for deploy.** Railway tracks a specific branch. If all feature work is on a long-running branch and master is stale (only initial docs), Railway sees nothing and Railpack reports "could not determine how to build the app." Merge to master OR change Railway's tracked branch before deploying. Add as Step 0 in any deploy runbook.
- **Idempotent seed in startCommand = self-healing deploys.** Chain `python -m app.seed.load_plan` after `alembic upgrade head`. The seed's `(athlete_email, plan_name)` upsert makes every boot safe. Avoids needing to find Railway's web shell for the one-off seed step.
- **`EXPO_PUBLIC_*` URL values MUST include protocol.** axios treats `marathonapp-prod.up.railway.app` (no `https://`) as a relative path → request goes to `https://your-vercel-domain/marathonapp-prod.up.railway.app/auth/login` → 404. ALWAYS prefix with `https://`. Diagnostic shortcut: check the actual Request URL in DevTools Network tab.
- **`EXPO_PUBLIC_*` requires Vercel rebuild after change.** Compile-time inlined into the JS bundle; Vercel does NOT auto-rebuild on env var change. Trigger Redeploy (uncheck "Use existing build cache") to bake the new value into the bundle.
- **5xx without CORS headers shows up in browser as "blocked by CORS policy".** FastAPI's default exception handler returns 500s without CORS decoration. When diagnosing a "CORS error", get the HTTP status code + response body BEFORE blaming the middleware. Defensive route-level try/except converting to `HTTPException(4xx)` keeps responses CORS-compliant. (Backlog: add a global exception handler that decorates 5xx with CORS headers.)
- **`garminconnect.Garmin.login()` silently returns on HTTP 429** (Garmin WAF rate-limiting datacenter IPs) instead of raising. Defend via post-login `hasattr(client, 'garth')` check; raise a custom `GarminLoginFailed` exception. Garmin sync from Railway is broken until Strava migration replaces the scraping path.
- **`react-native-gesture-handler` on touch-web has two known caveats:** (1) parent ScrollView claims upward touches before Pan can activate → "can only drag down, not up." Fix: toggle `scrollEnabled` during drag via parent state. (2) Pressable's `onPress` fires after long-press gesture completes → "drop opens detail." Fix: track `isDraggingRef` with 150ms post-drag suppression. Add `onFinalize` cleanup for cancelled gestures.
- **Workout edit doesn't auto-refresh description/intent unless explicitly sent.** PATCH `/workouts/{id}` originally only updated type/family/title/distance/duration. Added `description_md` + `intent_md` to `EditWorkoutRequest` schema + route. Frontend EditQuestSheet QUICK_PICKS now carries `defaultDescriptionMd` / `defaultIntentMd` per workout type and sends on Confirm.
- **Planned vs actual on Week tab:** /plan/week now joins through Reconciliation → CompletedWorkout to populate an `actual` field on PlannedWorkoutOut. WorkoutCard prefers `actual.distance_mi` when status=done; renders `plan: X.Xmi` sub-label when actual and planned differ by ≥0.1 mi.

#### Process retro lessons (worth re-reading before next debugging session)

- **The systematic-debugging skill is rigid for a reason.** When I followed it (bug batch, post-mid-session pivot), all 6 fixes went cleanly. When I didn't (Railway port saga), 3 wasted deploys + ~30 min lost. The skill's "one more fix attempt = STOP and add diagnostic instrumentation" rule is the single highest-leverage discipline.
- **Failing test before implementation** for non-trivial backend changes (#1 description_md/intent_md, #5b actual on /plan/week) made the fix verifiable AND scoped correctly. Both failed exactly the way I predicted on first run, then passed after the minimal fix. ~10 min extra upfront, saves rework.
- **Push back on batching under user time pressure.** When the user requested "fix all 4 [then 6] bugs tonight, batched" *right after* I'd confessed to bad batching on Railway, my instinct was to accept. The skill's discipline pays off: I pushed back, scoped to one-at-a-time, all 6 shipped clean. Recurring failure mode: treating "user wants it done" as override for "should be done correctly."
- **Recognize when the root cause is external.** Bug #3 (Garmin 429) wasn't a code defect — it was Garmin's WAF blocking Railway. The right action was defensive error surfacing + strategic note ("Strava migration is the real fix"), not trying to "make Garmin work harder."
- **"Browser says CORS error" ≠ "CORS is the problem."** When the request *receives* a response (even an error), CORS is firing. The real bug is whatever made the upstream return a header-less error.

### Plan / Seed / Deploy (Session 2.9)
- **Pipe-table parser is structure-agnostic.** `_parse_code_block` regex only requires `WEEK N` headers + `Day | type | dist | dur | desc | intent` rows. Switching from a 6-run/week template to a 4-5 run/week template needed zero parser changes — the entire v3.2 integration was PLAN.md content + a one-line `CYCLES[0]` start_date/weeks update. Keep parser dumb; push philosophy into the data file.
- **Seed upsert is idempotent BUT leaks ghost rows.** Upsert key is `(cycle_id, week_number, day)` — when Phase 1 shrunk from 28 → 22 weeks, old W23-28 rows survived the re-run. `docker compose down -v` (wipes pgdata) is the canonical local re-seed for structural plan changes. On Railway, a fresh deploy starts empty so there's no ghost problem; for a future in-place re-seed write a one-off `app/seed/reset_planned.py` that deletes only `planned_workouts WHERE status='planned'` for a given athlete (preserve `completed_workouts`, `reconciliations`, `plan_history`).
- **`SEED_PASSWORD` env var was declared in `app/config.py` but never read.** `app/seed/load_plan.py:24` had `DEFAULT_PASSWORD = "changeme123"` hardcoded. Caught while authoring the deploy runbook — fix is `DEFAULT_PASSWORD = os.environ.get("SEED_PASSWORD", "changeme123")` so Railway env can drive it. Watch for similar "declared but unused" config drift in other settings fields.
- **Railway Postgres URL scheme adapter.** Plugin injects `DATABASE_URL=postgresql://...` but SQLAlchemy async needs `postgresql+asyncpg://...`. Patch in `Settings.__init__`: if it starts with `postgresql://`, rewrite the scheme. Same env var works locally (Docker) and on Railway with no orchestration layer.
- **iOS personal-install economics.** Apple Developer Program ($99/yr) gives clean TestFlight + 1-year ad-hoc installs. Free Apple ID needs 7-day re-signs. PWA via Expo web → Vercel → Safari "Add to Home Screen" avoids both: fullscreen + custom splash + your icon, no signing. Tradeoff: bottom-sheets / drag-to-move / `expo-secure-store` need web-fallback consideration (most already handled in this codebase).
- **Garmin tokens are on-disk state.** `./data/garmin_tokens/<athlete_id>/tokens.json` — on Railway, mount a 1 GB volume at `/app/data` or every redeploy silently breaks Garmin sync (tokens vanish, scraper tries fresh login, hits Garmin auth wall).
- **`EXPO_PUBLIC_*` env vars are inlined into the JS bundle.** Visible to any client. Fine for API base URL; never for secrets. Vercel UX shows them in the env panel like any other var so it's easy to forget the distinction.

### LLM / Coach Chat steering (Session 3.1)
- **Gemini function-calling defaults to AUTO mode** when `tools=[...]` is passed with no `tool_config`. The model decides each turn whether to call the tool — so "when to use the tool" must be steered by the **system prompt**, not assumed. With a permissive prompt + a context blob full of editable workout IDs + an available mutation tool, `gemini-2.5-flash` over-eagerly fires the function. Fix = an explicit interaction policy (converse by default; ask clarifying questions; only call the tool on an explicit request). Keep AUTO — never force `ANY` (forces a call) or `NONE` (disables proposals).
- **Mocked LLM tests can't verify model *behavior*.** `test_coach_chat.py` mocks `generate_content`, so it validates the converse-vs-propose *contract* (text → text, change-request → proposal) but never exercises the real model's decision — exactly where prod diverged. When a fix depends on an external model, say so and require a live smoke-test; don't claim "done" off green unit tests alone.
- **Coach-chat latency:** v1 sends the full athlete context every turn (no `CachedContent`) and 2.5-flash has "thinking" on by default. If slowness matters, add a `thinking_config` budget and/or cache the context — tracked as a separate change, not bundled with behavior fixes.

## Reference

- Spec template: `docs/superpowers/specs/<date>-<slug>-design.md`
- Plan template: `docs/superpowers/plans/<date>-<slug>.md`
- Auto session log (per-branch): `docs/session-logs/<date>-<branch>.md` (written by `.claude/helpers/session-log.mjs` on SessionEnd)
