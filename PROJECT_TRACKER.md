# Marathon App — Project Tracker

## Current Sprint

| Sprint | Status | Branch | Notes |
|---|---|---|---|
| Session 1 — Backend foundation + Garmin sync | ✅ Done | merged | JWT auth, plan parser, reconciler, Garmin service |
| Session 2 — Mobile app + drag-to-move + Plan Adapter | ✅ Done | `session-2/backend-move-endpoints` | Backend move endpoints + Expo TS scaffold + drag-to-move |
| Session 2.5 — Workout edit + NES retro polish | ✅ Done | `session-2/backend-move-endpoints` | In-place workout edit, displaced-original flow, full NES restyle |
| Session 2.6 — UX polish + Program tab + Weekly Mileage Tracker | ✅ Done | `session-2/backend-move-endpoints` | Smoother-NES polish, Program tab with 3-lane world map + cycle-scoped mileage chart |
| Session 2.7 — Manual mark-complete + Recent runs + Coach brief + Start-date reseed + JetBrains Mono polish | ✅ Done | `session-2/backend-move-endpoints` | Four parallel features: log-completed flow, recent-runs strip + computed coach brief on Today, start-date reseed with dry_run preview + plan_history audit, typography sweep retiring PressStart2P from content sizes |
| Session 2.8 — Staycation IA + visual overhaul | ✅ Done | `session-2/backend-move-endpoints` | BrandBanner + DayToggle + WorkoutCard rewrite + tab active-pill + WhySheet retired (presentation-only; no API change) |
| Session 2.9 — Plan v3.2 + personal deployment runbook | ✅ Done | `master` (merged) | v3.2 plan integrated; deployment runbook authored. |
| Session 2.10 — Personal deploy executed + iPhone PWA bug batch | ✅ Done (Garmin IP-blocked) | `master` | App live: Railway API + Postgres + Vercel web/PWA + iPhone Add-to-Home-Screen. 6/7 bugs fixed (workout edit body refresh, DayToggle scroll-anchor, Tweak stats default open, Week shows actuals when done, bottom nav layout, drag-and-drop touch-web). Garmin sync defensively wrapped but blocked at Garmin's WAF (datacenter IP rate-limit, HTTP 429). Strava migration is the real fix. |
| Strava integration (alternative to Garmin scraping) | ⏳ Backlog (now urgent — blocks Garmin in prod) | — | OAuth + webhook ingestion. Stub at `docs/superpowers/specs/2026-05-07-feat-strava-integration-backlog.md`. **Promoted from "nice to have" to "needed" after Session 2.10's confirmed Garmin 429 from Railway IP.** Garmin→Strava is a native one-tap setting users already have. |
| Session 3 — Coach Chat (Gemini) + security hardening | ✅ Done (merged + deployed) | `master` | Free-form Gemini coach chat live in prod. Security audit → fail-closed `SECRET_KEY`/`SEED_PASSWORD` in prod. iPhone Safari week-scroll bug fixed. Daily Coach / Run Analyst still deferred. |
| Session 3.1 — Production activation + coach behavior fix | ✅ Done | `master` | Set Railway `APP_ENV`/`SECRET_KEY`/`SEED_PASSWORD`/`GEMINI_API_KEY`; merged `session-3` → master; rotated live athlete password via `reset_password`; fixed coach over-proposing (system-prompt steering); SDLC principles added to global CLAUDE.md; repo junk cleanup. |
| Session 4 — Strava integration backend (polling) | 🔨 Built + QA'd, NOT merged | `session-4/strava-integration` | Full OAuth polling-ingestion backend (19 commits) via subagent-driven dev + overnight adversarial QA. 159 tests green. Ingest-only sync + explicit mark-complete linkage. QA found+fixed OAuth CSRF, 3 sync crash modes (C1/H1/M1), session-poisoning. **Pending:** Strava app registration + Railway env vars + live smoke-test, then merge. Mobile UI is a separate plan. |
| Session 5 — Residential Garmin ingest agent | ✅ Done + merged + live in prod | `master` (merge `f4d8dd3`) | Split sync: laptop *fetch* (residential IP, dodges Garmin WAF 429) + Railway *store*. Backend ingest API + standalone laptop agent (`scripts/garmin_agent/`) via subagent-driven dev. **Live smoke-test PASSED**: 10 activities + 15 fully-enriched daily metrics (sleep/HRV/readiness/status) syncing to prod. NordVPN split-tunnel + Task Scheduler. |

## Sprint History

### Session 5 — Residential Garmin Ingest Agent (2026-06-19 → 2026-06-20)

**Goal:** Defeat Garmin's WAF datacenter-IP 429 (blocks server-side sync from Railway) by moving the Garmin fetch onto a residential laptop agent that POSTs to a token-authenticated backend ingest endpoint, with an on-demand "Sync now" PWA trigger.

**Status:** ✅ Done, merged to `master` (`f4d8dd3`), deployed to Railway, **live-smoke-tested end-to-end in production.**

**Delivered:**
- **Phase 1-2 (backend):** `POST /garmin/ingest` (token-gated, dedup, per-item skip), `GET /garmin/poll`, `POST /garmin/request-sync`; `sync_requested_at` migration (`767ce537f1dc`); PWA Sync-now repointed; fail-closed `GARMIN_INGEST_TOKEN` prod check.
- **Phase 3 (laptop agent, subagent-driven):** `scripts/garmin_agent/` — keyring/file-backed config, fail-closed egress IP guard (ip-api), garth fetch wrapper, ingest API client, CLI (`--login`/`--set-secrets`/`--once`/`--watch`), README runbook. Agent suite **15/15**, each task implementer→reviewer→fix-loop + opus final review.

**Live smoke-test bugs found + fixed (import tests couldn't catch):**
- `client_from_token` used `garth.loads` + `login()` → fresh SSO w/ empty creds → 401. Fixed to `login(tokenstore=token)` (`72c0b4c`).
- garth token blob >2560B → Windows `CredWrite` `WinError 1783`. Moved garth token keyring→gitignored `.garth_token` file, `0o600` (`6512081`/`a25a190`).
- `--login` 401'd on NordVPN datacenter IP (no egress guard) → added guard + clear message (`b8d3b3b`); README step-order fixed.
- Railway deploys `master` → `/garmin/*` 404 until merged; `GARMIN_INGEST_ATHLETE_EMAIL` must be app-login email, not Garmin email (400).

**Enhancement:** recovery-metric enrichment (`3f3bad1`) — `enrich_metric()` merges sleep score/duration, overnight HRV, training readiness, training status from separate Garmin endpoints (live-validated field paths); +3 unit tests.

**Follow-on (same session, shipped to prod):** mobile **"Link a run →"** UI on `WorkoutDetailScreen` — picks a nearby synced/completed activity (source-agnostic) and links it to a planned workout via the already-live `strava-candidates` + `link-completed` endpoints (`LinkRunSheet` + `useLinkFlow`, mirrors the log-completed flow). Closed the gap where synced Garmin runs couldn't be attached to planned workouts. tsc clean; live-confirmed linking works.

**Remaining (user-side, non-blocking):** scheduled `--watch` task is registered but uses `pythonw.exe`, which NordVPN's split-tunnel doesn't yet bypass (add `…\.venv\Scripts\pythonw.exe` + `C:\Python313\pythonw.exe`, or switch the task to the already-tunneled `python.exe`). Manual `--watch` covers syncs meanwhile.

**Plan:** `docs/superpowers/plans/2026-06-17-residential-garmin-agent.md`.

### Session 4 — Strava Integration Backend + Overnight QA (2026-06-16 → 2026-06-17)

**Goal:** Build the Strava polling-ingestion backend (the durable fix for Garmin's WAF block) via subagent-driven development, then run an autonomous overnight QA + bug-fix pass. Auto-fix on branch; no merge.

**Status:** ✅ Built + hardened on `session-4/strava-integration` (19 commits, **unmerged**). 159 tests pass, ruff clean. Full report: `docs/session-logs/2026-06-17-overnight-strava-qa.md`.

**Delivered (plan Tasks 1–14):** config + `family_for_strava_sport_type`; `CompletedWorkout` columns (`strava_activity_id`/`source`/`avg_cadence`/`avg_watts`/`relative_effort`); `StravaAuthState` (DB tokens, TIMESTAMPTZ); `app/services/strava/{oauth,client,sync}.py` (ingest-only sync, dedup, inline refresh, pagination); routes connect/callback/status/sync/disconnect (CORS-safe); mark-complete linkage (`strava-candidates` + `link-completed`, ownership re-validated); Alembic migration `3ef08f92d555`.

**Overnight QA found + fixed (Tasks 15–19):**
- OAuth **CSRF + callback-auth** gap → signed state-token (`aea79bd`).
- Adversarial review found 3 **confirmed sync crash modes** (C1 KeyError, H1 in-batch dup, M1 numeric overflow) + C2 session poisoning + H2 all-or-nothing commit → hardened with per-activity skip, in-batch dedup, per-page commit, clamps, typed errors, `last_error` wiring (`9bf21d4`).
- Round-2 verification caught residual bugs in the round-1 fix (`expunge` vs `rollback`; unclamped distance/calories/hr) → fixed (`39890fc`).
- Fixed pre-existing date-rot in `test_plan_start_date.py` (`34b7141`); added refresh/pagination coverage (`2ab27c6`).

**Remaining before live:** register Strava app + set Railway `STRAVA_CLIENT_ID/SECRET/REDIRECT_URI`; live smoke-test; then merge. Mobile UI (Settings card + MARK DONE picker) is a separate plan. **Backlog (non-blocking):** sync cursor (`last_successful_sync=now()`) can skip late-uploaded/backdated activities.

**Specs/plans:** `docs/superpowers/specs/2026-06-16-strava-integration-design.md`, `docs/superpowers/plans/2026-06-16-strava-integration-backend.md`.

### Session 3.1 — Production Activation + Coach Behavior Fix (2026-06-15 → 2026-06-16)

**Goal:** Activate the Session 3 work in production (env vars + merge + live login), then debug the coach's behavior based on first real use.

**Delivered (on `master`):**
- **Railway env + deploy** — set `APP_ENV=production`, `SECRET_KEY` (64-hex), `SEED_PASSWORD`, `GEMINI_API_KEY`; confirmed the fail-closed checks pass on boot. Discovered the Session 3 code (chat + fail-closed config) was never merged — `master` only had the old chat stub. Merged `session-3/coach-chat` → `master` (`c613725`), which is the deploy that actually activated coach chat + the security hardening + the iOS scroll fix.
- **Live login rotation** — ran `python -m app.scripts.reset_password --email runner@marathon.dev --from-seed-env` inside the prod container via `railway ssh` (seed never rotates an existing athlete's password). Athlete `7ff7b20e-…` now logs in with the `SEED_PASSWORD` value.
- **Coach behavior fix (`68765b8`)** — first live use surfaced the coach throwing plan-change proposals without conversing. Systematic-debugging root cause: function-calling runs in AUTO mode with a system prompt that gave **no policy on *when* to propose**, so Gemini over-fired `propose_plan_change` on benign messages (the intended converse-first contract lived only in mocked tests). Fix: explicit "How to interact" policy in `COACH_SYSTEM_PROMPT` — converse by default, ask clarifying questions, only propose on an explicit change request, and periodically remind the athlete in plain text that the plan can be adjusted. No logic change; 128 backend tests green.
- **Global CLAUDE.md** — added a Software Development Lifecycle (SDLC) Principles section (test-alongside-code, maintainability, secure coding, full-arc thinking).
- **Repo hygiene** — removed 46 junk untracked files (0-byte shell-redirect fragments + a typo'd root `package.json`/`package-lock.json` from a stray `npm install -g`). Flagged `docs/household-financial-platform-spec_1.md` as a different project's spec to relocate.

**Verification:** backend 128/128 green in-container. Coach behavior fix needs live smoke-test (depends on external Gemini model — mocked in tests). Coach chat confirmed responding in prod; Garmin sync still environmentally blocked.

### Session 3 — Coach Chat (Gemini) + Security Hardening (2026-05-30 → 2026-05-31)

**Goal:** Fix the iPhone-Safari week-scroll bug, security-audit the public deployment, and build the free-form Gemini coach chat from the existing `session 3` scaffolding.

**Delivered (branch `session-3/coach-chat`, 12 commits):**
- **Scroll bug** — inverted `scrollEnabled` wiring in `WeekScreen.tsx` (gesture finalize disabled scroll instead of re-enabling it). One-char fix (`!active`).
- **Security audit** — two HIGH findings: default JWT `SECRET_KEY` and default `SEED_PASSWORD`, both with no enforcement on a public URL. Fix: `APP_ENV=production`-gated fail-closed checks in `config.py` + `load_plan.py`; `app/scripts/reset_password.py` for live-row rotation; 8 new config tests. Authz audit found no IDOR (every route scopes by `Plan.athlete_id`).
- **Coach Chat** — Gemini `gemini-2.5-flash`; `build_athlete_context` (live snapshot+markdown); `coach_chat.run_turn` (persistent `user_chat` thread); `propose_plan_change` function-calling reusing the proposal contract; shared `proposal_apply` service (extracted from `apply-move`) with §3.2 per-edit ownership re-validation; `GET/POST /chat` + `/chat/proposal/apply` (502/503 CORS-safe); mobile `ChatScreen`/`ChatBubble`/`useChat` reusing `ProposalSheet`.
- **Verification:** backend 128 passed in-container; mobile `tsc --noEmit` clean. NOT yet runtime-smoke-tested (needs live `GEMINI_API_KEY` + device).

**Remaining:** live smoke-test; set Railway `GEMINI_API_KEY` + `APP_ENV`/`SECRET_KEY`/`SEED_PASSWORD`; rotate live athlete password; then merge to `master`.

### Session 2.10 — Personal Deploy Executed + iPhone PWA Bug Batch (2026-05-25 → 2026-05-26)

**Goal:** Execute the Session 2.9 deployment runbook end-to-end, get the app reachable on the open internet via Railway (API + Postgres) and Vercel (Expo web → iPhone PWA), then fix the bugs surfaced by the first real smoke-test session on iPhone Safari.

**Status:** ✅ App is live and functional. 6/7 reported bugs fixed; #7 (Garmin sync) is blocked by external constraint (Garmin's WAF rate-limits datacenter IPs with HTTP 429) — defensive error handling shipped, real fix is the Strava migration on the backlog.

**Deployment deliverables (Step 1 → Step 5 of runbook):**
- `Dockerfile.prod` + `railway.json` shipped — Railway builds from Dockerfile, runs `alembic upgrade head` + `python -m app.seed.load_plan` + uvicorn on `$PORT` (idempotent seed makes every boot self-healing on fresh Postgres).
- `app/config.py` rewrites `postgresql://` → `postgresql+asyncpg://` at startup so Railway's auto-injected `DATABASE_URL` works with SQLAlchemy async.
- `app/main.py` CORS locked down to Vercel origin via `WEB_ORIGIN` env var.
- `app/seed/load_plan.py` reads `SEED_PASSWORD` from env (was hardcoded `"changeme123"` — caught during runbook authoring, fixed pre-deploy).
- Railway: API service from `master`, Postgres plugin linked via Variable Reference, 1 GB volume mounted at `/app/data` for Garmin tokens, all env vars set.
- `mobile/app.json` PWA web block: name, shortName, themeColor `#0e1320`, display `standalone`, lang `en-US`.
- `mobile/vercel.json` + `mobile/assets/apple-touch-icon.png`.
- Vercel project rootDir `mobile`, `EXPO_PUBLIC_API_URL` pointed at Railway domain.
- iPhone PWA: Safari → Share → Add to Home Screen → fullscreen navy splash + icon. Working.

**Bug batch deliverables (followed systematic-debugging discipline this round):**
- **#1 workout-edit body refresh** — `EditWorkoutRequest` schema + route gain `description_md` / `intent_md` fields. Frontend `EditQuestSheet` QUICK_PICKS map carries `defaultDescriptionMd` / `defaultIntentMd` per type and sends on Confirm. Failing test landed before fix.
- **#2 DayToggle scroll-anchor** — `DraggableWeekList` exposes `onDayLayout(date, y)` callback. `WeekScreen` caches per-day offsets and scrolls on day pick. Completes the Session 2.8 follow-up.
- **#5a Tweak stats default open** — `useState(false)` → `useState(true)` in `EditQuestSheet`. Surfaces the distance/duration fields users were missing.
- **#5b Week tab shows actuals when done** — New `PlannedActualOut` schema (`distance_mi`, `duration_s`, `started_at`) + optional `actual` field on `PlannedWorkoutOut`. `/plan/week` joins through `Reconciliation` → `CompletedWorkout`. `WorkoutCard` prefers `actual.distance_mi` when status=done; renders `plan: X.Xmi` sub-label when actual and planned differ by ≥0.1 mi. Failing test landed before fix.
- **#6 bottom nav squished on iPhone 15 Pro Max** — `PillTabBarButton` flexDirection `row` → `column`, paddingHorizontal `14` → `8`. Standard tab layout, fits all reasonable iPhone widths.
- **#7 drag-and-drop on touch web** — Two symptoms, same root cause: `react-native-gesture-handler` gesture priority doesn't translate to web touch events. Fix: WeekScreen controls `scrollEnabled` state, DraggableWeekList exposes `onDragActive`; Pan disables scroll during drag (fixes "can only move down"). DraggableWorkout tracks `isDraggingRef` with 150ms post-drag suppression window (fixes "drop opens workout detail"). `onFinalize` belt-and-suspenders for cancelled gestures.
- **#3 Garmin defensive error handling** — `GarminLoginFailed` exception in `garmin_sync.py` covers wrong creds, 429, network errors, and the silent failure mode where `client.login()` returns without setting `.garth` (observed on 429). Route converts to `HTTPException(502)` with the message, so users see a clean error instead of opaque 500 (which the browser then misreports as CORS-blocked).
- **#4 free-form coach** — explicitly deferred to Session 3.

**Specs:** `docs/superpowers/specs/2026-05-24-personal-deployment-runbook.md` (the executable runbook, refined during execution).

**Commit range:** `a918e2c..e61eb05` on `master` (Session 2.9 design + Session 2.10 execution + bug batch).

---

#### Retro — what went well, what went wrong

**🟢 Wins (worth repeating):**

1. **Brainstorming discipline on v3.2** — design → spec → user approval → implementation → tests went smoothly with no rework.
2. **Bug-batch discipline (post-mid-session)** — once we invoked `systematic-debugging`, all 6 fixes followed Phase 1 → 4. Failing test before implementation for #1 and #5b made the work verifiable. One commit per logical batch with rollback points.
3. **Defensive Garmin fix** — recognized when the root cause was external (Garmin WAF) and the right action was clean error surfacing + a strategic note, not "make it work harder."
4. **Multi-component evidence gathering** — adding `echo "BOOT: PORT=$PORT"` + lifespan logger to diagnose the deploy crashes was textbook (even if it came late — see Loss #1).

**🔴 What went wrong (and what we should have done):**

1. **Three sequential blind fixes on the Railway port issue (~30 min wasted, 3 deploy cycles):** `--port 8000` → `${PORT:-8000}` → `$PORT` → `sh -c '$PORT'`. Each fix was a guess without evidence. Should have added the `BOOT: PORT=$PORT` echo on attempt #2 — one deploy would have told us whether shell expansion was working at all. Exactly the anti-pattern `systematic-debugging.md` calls out ("one more fix attempt" after 2+ failures).
   - **Lesson:** When the platform is opaque (Railway's exec form vs sh form behavior), add diagnostic instrumentation BEFORE the next candidate fix. The skill's "Phase 1.4 — Gather Evidence in Multi-Component Systems" section is exactly for this case.

2. **CORS error masquerading as Garmin error** — initial diagnosis pointed at `WEB_ORIGIN` trailing slash; that was wrong. The real cause was a 500 from `/garmin/reauth` whose response stripped CORS headers, making the browser report it as "blocked by CORS." Took two diagnostic round-trips to get to the application-log traceback.
   - **Lesson:** "Browser console says CORS" is not the same as "CORS is misconfigured." When the request is *receiving a response* (even an error), CORS is firing — the real issue is whatever made the upstream return a header-less error. Always ask for HTTP status code + response body before assuming CORS root cause.
   - **Lesson:** Add a global FastAPI exception handler that decorates 5xx responses with CORS headers, so future 500s show up correctly in the browser as "500 Internal Server Error" instead of as CORS ghosts. (Backlog: defensive infra improvement.)

3. **Branch mismatch on first Railway deploy** — Railway deployed `master` (which had only initial docs, no code). All Session 1–2.9 work was on `session-2/backend-move-endpoints` and never merged. Required merging to master to fix.
   - **Lesson:** Add explicit "merge feature branch to master" as a Step 0 in any deploy runbook. The deploy assumes master = production state; long-running feature branches break that assumption silently.

4. **EXPO_PUBLIC_API_URL without `https://`** — axios treated the bare hostname as a relative path, producing the absurd concatenated URL `vercel-domain/railway-domain/auth/login` → 404. Diagnostic was fast once we saw the Network tab Request URL.
   - **Lesson:** Vercel env-var UX needs stronger guidance for `EXPO_PUBLIC_*` values — always include protocol, never trailing slash. Add to runbook §4 explicitly.

5. **Tried to batch 6 bug fixes initially** — user requested "fix all 4 [then 6] tonight, batched." Almost replicated the Railway anti-pattern. Pushed back, scoped to one-at-a-time. Good outcome but the instinct to batch under pressure is a recurring failure mode.
   - **Lesson:** When the user requests batching after I've just confessed to bad batching, push back harder up-front, not by default-accepting.

6. **Hardcoded `SEED_PASSWORD` "changeme123" was lurking** — declared in `app/config.py` for unknown reasons but never read from env until I noticed during runbook authoring. Caught it, but represents "declared-but-unused" config drift from earlier sessions.
   - **Lesson:** Periodically grep config fields against actual usage; remove declared-but-unread fields OR wire them through.

**🟡 External constraints (acknowledged, not fixable in this codebase):**

- **Garmin's WAF rate-limits datacenter IPs (429)** — `garminconnect` is unofficial scraping; Garmin actively blocks it from cloud providers. Strava integration via official OAuth is the only durable path.
- **react-native-gesture-handler on web is imperfect** — gesture priority vs browser native touch handling causes the scrollable-list drag issues we patched in #7. Patches work but a future Expo SDK or gesture-handler version may need re-tuning.
- **Railway startCommand exec form** — does NOT shell-expand `${VAR:-default}` POSIX syntax cleanly. Wrap in explicit `sh -c '...'` if you need shell semantics. This is undocumented behavior we discovered the hard way.

#### Notable lessons (added to CLAUDE.md + MEMORY.md)

- Railway `DATABASE_URL` scheme adapter pattern (`postgresql://` → `postgresql+asyncpg://`) at Settings init time
- Railway startCommand `sh -c` wrapping for guaranteed shell expansion (`$PORT`, `&&`, etc.)
- Idempotent seed in startCommand makes deploys self-healing (no shell needed for one-off seed)
- `EXPO_PUBLIC_*` vars are compile-time inlined into the JS bundle — never put secrets there; ALWAYS include `https://` for URL values (axios treats bare hostnames as relative)
- 500-without-CORS-headers shows up in browser as a "CORS blocked" error — get the HTTP status code + traceback before blaming CORS config
- Garmin login failing silently (returning without setting `.garth` on 429) — defend via post-login `hasattr` check
- "Can only move down, not up" on touch-web drag = parent ScrollView claiming upward touches — fix by toggling `scrollEnabled` during gesture

### Session 2.9 — Plan v3.2 + Personal Deployment Runbook (2026-05-24 → 2026-05-25)

**Goal:** Two coordinated workstreams ahead of the actual marathon training kickoff on Monday 2026-05-25 — (A) ship the user's new v3.2 training plan into the seed pipeline so day-1 mobile data is accurate, and (B) author a complete personal-deployment runbook for Railway (API + Postgres) + Vercel (Expo web/PWA) the user can execute solo in one evening.

**Status:** ✅ Plan v3.2 integration shipped and verified. Deployment runbook authored and committed; runbook execution by the user is the next step.

**Decisions captured during brainstorming:**
- Slider/flexibility modeling: deterministic days (Mon=strength_a, Wed=quality, Sat=long, Sun=recovery), flex documented in body text and handled via existing drag-to-move UX. No schema/UI change.
- Cycles 2/3 policy: keep v2.0 content, prefix every workout description with `"PRELIMINARY — "` until post-MCM re-anchoring.
- Workout type granularity: reuse existing `WorkoutType` enum, encode "intro" / "trail" / "quality" flavor in body text. Avoided Alembic migration on the native Postgres enum.
- iOS path: avoid Apple Developer / sideloading complexity by shipping as a PWA installed via Safari "Add to Home Screen."

**Backend / data deliverables:**
- `PLAN.md` rewritten end-to-end for v3.2 — new Phase 1 (22 weeks, Mon=strength_a / Tue/Wed/Thu trail / Fri=strength_b / Sat=long / Sun=recovery), KNEE RULE on W20 peak, race week 22 mapped to special layout; Phase 2 + 3 v2.0 content preserved with `PRELIMINARY — ` prefix on every workout body. Athlete philosophy block updated to v3.2 5-point version.
- `app/seed/plan_parser.py` — `CYCLES[0]` anchored to `date(2026, 5, 25)`, `weeks=22`. No parser logic changes (pipe-table format is structure-agnostic).
- Test re-calibration across 5 files: 322 workouts total (was 364), `peak_week_target=20` (was 23), `len(cycle1.weeks)=22` (was 28); reseed test fixtures shifted to `date(2026, 6, 15)` with `new_cycle1_weeks=19` (was 25).
- 104/104 backend tests green; mobile typecheck clean. Local DB seeded against new plan; spot-checks verified W1 Mon = Strength A intro, W18 Sat = 20mi w/ 70g/hr, W20 Sat = 21-22mi peak, W22 Sun = MCM race.

**Deployment runbook deliverables:**
- `docs/superpowers/specs/2026-05-24-personal-deployment-runbook.md` (490 lines) — §0 pre-flight, §1 backend changes (Dockerfile.prod, railway.json, CORS lockdown, `SEED_PASSWORD` wire-through patch for `load_plan.py`, Railway DB-URL adapter for `postgresql://` → `postgresql+asyncpg://`), §2 Railway setup (Postgres plugin, API service, 1GB volume for Garmin tokens, env vars, seed, athlete_id discovery, Garmin reauth bootstrap), §3 mobile/Vercel code (PWA manifest in `app.json`, `mobile/vercel.json`), §4 Vercel deploy + CORS close-out, §5 iPhone Add-to-Home-Screen, §6 smoke-test checklist per screen, §7 day-2 ops (redeploy, rollback, rotate creds, logs, backups), §8 risks (Garmin scraper from datacenter IPs, bottom-sheet web parity, iOS PWA storage purges), §9 quick reference card.

**Specs:**
- `docs/superpowers/specs/2026-05-24-personal-deployment-runbook.md`
- `docs/superpowers/specs/2026-05-24-plan-v3.2-integration-design.md`

**Commit range:** `a918e2c..2af3079` (3 commits on `session-2/backend-move-endpoints`: runbook, v3.2 design spec, v3.2 implementation)

**Notable lessons:**
- The `_parse_code_block` regex parser is intentionally format-agnostic — switching from a 6-run/week template to a 4-5 run/week template requires zero parser changes as long as the `WEEK N` header + `Day | type | dist | dur | desc | intent` row format is preserved. Lets you change plan philosophy without code churn.
- The seed `seed_plan(idempotent=True)` upserts by `(cycle_id, week_number, day)` but does NOT delete weeks that no longer exist in the source. When `Phase 1` shrunk from 28 to 22 weeks, old W23-28 rows persisted as ghosts. `docker compose down -v` followed by fresh `alembic upgrade head` + `python -m app.seed.load_plan` is the canonical local re-seed for structural plan changes.
- `app/config.py` declared `seed_password` but no code actually read it — `load_plan.py:24` hardcoded `DEFAULT_PASSWORD = "changeme123"`. Caught during deploy-runbook authoring; runbook §1.5 includes the `os.environ.get("SEED_PASSWORD", "changeme123")` patch as part of pre-deploy backend prep.
- Railway's Postgres plugin injects `DATABASE_URL` in `postgresql://` form, but SQLAlchemy async needs `postgresql+asyncpg://`. Lightweight `__init__` patch in `Settings` rewrites the scheme so the same env var works locally and on Railway without surrounding orchestration.
- Personal iOS install without Apple Developer Program ($99/yr) is a real tradeoff. Free-Apple-ID resigning every 7 days is friction; Expo web → PWA → Safari Add-to-Home-Screen avoids the signing/distribution rabbit hole entirely and feels app-like enough (fullscreen, custom splash, your icon). Tradeoff: bottom-sheets, drag-to-move, and `expo-secure-store` need web-fallback consideration (most already done).

### Session 2.8 — Staycation IA + Visual Overhaul (2026-05-07 → 2026-05-08)

**Goal:** Restructure mobile content screens to match the staycation.exe reference — branded banner, segmented day toggles, restyled card composition (no inline buttons, chevron affordance), filled-pill active tab — without changing data model, API, or navigation tree.

**Status:** ✅ Complete. ~16 plan tasks across 5 phases, 21 commits, mobile typecheck clean. Backend untouched.

**Mobile deliverables:**
- New `BrandBanner` (wordmark + `▸` caret subhead + 1px slate rule) on every content screen
- New generic `DayToggle<T>` segmented pill — used as 2-seg `TODAY | TOMORROW` on Today and 7-seg `MON…SUN` on Week
- New `BottomActionBar` (safe-area-aware sibling-layout action row) — used by WorkoutDetail for MARK DONE / SKIP
- `WorkoutCard` rewritten to staycation composition: meta + family badge + status badge + chevron + monoBold title + lighter mono sub; `onWhy`/`onEdit` props dropped, `compact`→`dense`
- Custom `PillTabBarButton` in `RootNavigator` reading v7 `aria-selected`; active tab now shows filled phosphor-green rounded pill behind icon+label
- Today: BrandBanner + DayToggle + sync icon button + day-choice-aware loading/error gates; coach brief now plain paragraph (no RetroBorder)
- Week: BrandBanner + 7-day DayToggle (M–S) + selectedDay resets when cursor changes weeks
- WorkoutDetail: BrandBanner + thin Back/Edit chip row + BottomActionBar; SafeAreaView `edges={['top']}`
- Program: BrandBanner + `▸ The trilogy` and `▸ Weekly mileage` SectionHeaders above lanes / tracker
- Settings: BrandBanner ▸ ATHLETE — email subhead
- WeekTile dense restyle: filled status chip + neutral background
- Deleted: `WhySheet.tsx` and all dead refs (intent already lives on WorkoutDetail)

**Spec:** `docs/superpowers/specs/2026-05-07-feat-staycation-ux-overhaul-design.md`
**Plan:** `docs/superpowers/plans/2026-05-08-session-2.8-staycation-overhaul.md`
**Commit range:** `6f5876f..7b47400` (21 commits on `session-2/backend-move-endpoints`)

**Notable lessons:**
- React-navigation v7 selected-tab signal is `aria-selected`, not `accessibilityState.selected` (the v6 prop). The custom `tabBarButton` had to read the new prop or the active pill never lit up.
- A SafeAreaView wrapping a screen that ends in a `BottomActionBar` should use `edges={['top']}`. Default `edges` (top+bottom) double-pads the home indicator since the action bar already adds `insets.bottom`.
- 7-day toggle scroll-anchor is best-effort: `DraggableWeekList` doesn't expose per-day Y offsets, so the toggle updates visual state only. List is at top when on the current week, which is the realistic case. Follow-up tracked in plan §Risk Register.
- `firstSentence` extractor for card subs needs markdown stripping + `?` terminator support + bare-punctuation guards or it leaves `**` markers and orphan punctuation. Caught by manual smoke on the post-rewrite WorkoutCard.

### Session 2.7 — Manual mark-complete + Recent runs + Coach brief + Start-date reseed + JetBrains Mono polish (2026-05-07)

**Goal:** Four coordinated features in one sprint addressing user feedback after Session 2.6 demo: (A) manual mark-complete with workout-data dialog, (B) recent runs strip + computed coach brief on Today, (C) program start-date picker with auto-reseed, (D) typography polish toward staycation-crisp by retiring PressStart2P from content sizes.

**Status:** ✅ Complete. ~50 plan tasks across 6 phases shipped, ~50 commits, 104/104 backend tests green, mobile typecheck clean.

**Backend deliverables:**
- `app/services/cache_invalidation.py` — `invalidate_for_athlete(athlete_id)` umbrella that fans out to plan_full, plan_stats, recent_completed, coach_brief caches
- `garmin_activity_id` migration: nullable so manual logs can persist without a Garmin ID
- `plan_history` audit ledger table for tracking start-date reseeds
- `POST /workouts/{id}/log-completed` — creates `CompletedWorkout` + `Reconciliation`, sets planned status to done, derives pace from distance/duration if not supplied
- `GET /workouts/completed/recent?limit=N` — last N completions, 60s cache, busted on mutations
- `app/services/coach_brief.py` — heuristic composer (no LLM): today's prescription + yesterday recap + adherence band + days-to-race; ≤280 chars
- `coach_brief` field populated on `/plan/today` (replaces null placeholder)
- `app/seed/plan_parser.py` parametrized with `cycle_one_start_date` — drops earliest template weeks when cycle is shortened
- `app/services/plan_reseed.py` — `compute_reseed_impact` (read-only preview) + `apply_reseed` (delete incomplete planned, re-emit fresh, discard pending proposals, write plan_history)
- `POST /plan/start-date?dry_run=<bool>` — preview impact OR commit reseed

**Mobile deliverables:**
- JetBrains Mono Regular + Bold loaded via expo-font; new `fonts.mono` / `fonts.monoBold` tokens
- Typography sweep across 17 files: PressStart2P retired from content sizes (titles → monoBold, labels → mono); kept only on brand title, tab labels, badges, primary CTA, and data-table sub-headers
- New components: `LogCompletedSheet` (mark-done form + Garmin sync link), `RecentRunsStrip` + `RecentRunSheet`, `StartDateSheet` (with live dry_run impact preview)
- New hooks: `useLogCompleted`, `useSync`, `useRecentCompleted`, `useResetStartDatePreview`, `useResetStartDateApply`, `useLogFlow`
- WorkoutDetail: MARK DONE button (hidden for rest workouts and done/skipped status)
- Settings: RESET START DATE button under Plan card
- TodayScreen consolidated PR: SYNC pill in header, RecentRunsStrip replaces placeholder, live coach brief replaces placeholder, full typography sweep applied

**Spec:** `docs/superpowers/specs/2026-05-07-feat-{a,b,c,d}-*.md`, `2026-05-07-session-2.7-cross-cutting-review.md`
**Plan:** `docs/superpowers/plans/2026-05-07-session-2.7-feats-abcd.md`
**Decisions:** `docs/superpowers/plans/2026-05-07-session-2.7-decisions.md`
**Phase 0 user decisions:** No `abandoned` status (reseed semantics chosen over delta-shift); no `MIN_WEEKS_TO_RACE` refusal; `fonts.mono` / `fonts.monoBold` token names.



### Session 2.6 — UX Polish + Program Tab + Weekly Mileage Tracker (2026-05-06)

**Goal:** Polish NES restyle toward staycation.exe (rounded soft borders, phosphor green + cyan accents, no offset shadows, pixel font display-only), and ship a Program tab with full-program world-map view + a Weekly Mileage Tracker that compares actual vs planned mileage cycle by cycle.

**Status:** ✅ Complete. 25 plan tasks across 5 phases, 22 commits, 61/61 backend tests green, mobile typecheck clean.

**Backend deliverables:**
- `app/services/plan_aggregator.py` — week rollups + KPI builder + 60s per-athlete cache + `invalidate_plan_cache(athlete_id)` for explicit busts
- `GET /plan/full` — cycles → weeks rollup tree (3 cycles, 52 weeks, ~6 KB)
- `GET /plan/stats?scope=cycle|plan` — KPI bundle (on-plan %, streak, planned/actual mi, next milestone, peak week)
- Cache busting wired into `PATCH /workouts/{id}`, `/skip`, `/apply-move` (all return paths), `/reschedule-original`
- New Pydantic schemas: `WeekRollup`, `CycleFull`, `PlanFullOut`, `NextMilestone`, `PeakWeekSummary`, `PlanStatsOut`
- Seeder now sets `Cycle.peak_week_target` heuristically (week containing the longest non-race long run)

**Mobile deliverables:**
- Palette shifted to staycation tones: navy `#0e1320` bg, slate `#2a3045` line, phosphor green `#22d36a`, cyan `#7ec8c8` accent, warmer cream ink
- Primitives rounded (4–6px), soft-bordered (1px slate), no offset shadow — `softBorder` helper added; `nesBorder`/`nesShadow` kept as legacy opt-ins
- Primary `RetroButton` is filled with no border; press-translate softened to 1px
- `RetroPill` gains filled-rounded `badge` variant alongside the bracket-style status variant
- New `SectionHeader` (cyan mixed-case VT323 with `▸` caret) replaces ad-hoc all-caps pixel headers on Today / WorkoutDetail / Settings
- New Program tab with `▤` glyph between Week and Chat
- New components: `WeekTile` (status-aware mileage glyph: ✓/▶/!/↓/★/[FLAG]), `RaceMilestoneTile`, `CycleLane` (auto-scroll to current week), `StatTile`, `StatsPanel` (5-tile KPI grid), `WeeklyMileageTracker` (cycle-scoped bar chart with planned/actual bars, P1/P2/P3 toggle, cumulative overlay, semantic delta header)
- New hooks: `usePlanFull`, `useProgressStats`
- Week tab now accepts `initialDate` route param so Program → Week tile-tap drills into the right week

**Spec:** `docs/superpowers/specs/2026-05-06-program-tab-progress-tracker-design.md`, `2026-05-06-ux-polish-staycation-observations.md`
**Plan:** `docs/superpowers/plans/2026-05-06-session-2.6-ux-polish-and-program-tab.md`
**Commit range:** `25f77c6..ec40dcb` (22 commits on `session-2/backend-move-endpoints`)



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
