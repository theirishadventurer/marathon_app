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
| Session 2.9 — Plan v3.2 + personal deployment runbook | ✅ Done (deploy pending exec) | `session-2/backend-move-endpoints` | New v3.2 plan integrated (22-week MCM build kicking off 2026-05-25, 4-5 runs/week, Mon/Fri strength-only). Phase 2/3 preserved as PRELIMINARY. Personal deployment runbook authored (Railway API + Postgres + 1GB volume / Vercel free web/PWA / iPhone Add-to-Home-Screen). Runbook ready to execute. |
| Strava integration (alternative to Garmin scraping) | ⏳ Backlog | — | OAuth + webhook ingestion path. Stub at `docs/superpowers/specs/2026-05-07-feat-strava-integration-backlog.md`. Goal: replace fragile `garminconnect` scraping with stable Strava official API. Garmin→Strava is a native one-tap setting users already have. |
| Session 3 — Daily Coach, Run Analyst, free-form chat | ⏳ Backlog | — | See `SESSION_3.md` |

## Sprint History

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
