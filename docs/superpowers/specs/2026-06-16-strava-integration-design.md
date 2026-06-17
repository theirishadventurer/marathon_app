# Strava Integration — Design Spec

**Date:** 2026-06-16
**Status:** Approved (brainstorming pass complete) — ready for implementation plan
**Supersedes:** `docs/superpowers/specs/2026-05-07-feat-strava-integration-backlog.md` (the light backlog stub)

## Purpose

Garmin sync is environmentally blocked in production — Garmin's WAF rate-limits
Railway's datacenter IP with HTTP 429, so `garminconnect` login silently fails
from the deployed server. Completed runs are therefore manual-only (the MARK DONE
flow) in prod. Strava offers an official OAuth API; Garmin → Strava is a native
one-tap Garmin Connect setting the athlete already has. This integration makes
completed activities ingest automatically again, via Strava as the production
activity source.

## Scope decisions (from the brainstorming pass)

1. **Ingest all available Strava data** — activities with their full summary metric
   set (distance, time, elevation, HR, cadence, watts, calories, relative effort,
   sport type). **Strava exposes NO daily wellness/recovery data** (sleep, HRV,
   resting HR, body battery, training readiness) — those are Garmin-only and have
   no Strava equivalent. The Garmin-fed `DailyMetric` table stays as-is (dormant in
   prod). This is a hard Strava API limit, not a design choice.
2. **Ingestion = polling (Approach A).** On-demand "Sync now" + a client-side sync
   on app open/login. No webhooks, no server-side scheduler in v1 (YAGNI for a
   single-athlete app). Webhooks are a clean future add.
3. **OAuth scope = `activity:read_all`** so private / followers-only activities are
   not missed (it is the athlete's own data).
4. **Streams (per-activity time-series) deferred** to a future "Run Analyst"
   feature — high volume, not needed to display completed runs.
5. **Garmin stays in place but dormant.** Not removed (still works from a
   non-datacenter IP if metrics are ever wanted). No cross-source dedup built in v1.

## Module layout (small, single-purpose units)

```
app/services/strava/
  oauth.py    # build authorize URL; exchange code→tokens; refresh; deauthorize (pure-ish, unit-testable)
  client.py   # thin httpx.AsyncClient wrapper; get_strava_client() seam for mocking (mirrors get_gemini_client)
  sync.py     # StravaSyncService: list activities → map → dedup → persist → reconcile
app/models/strava.py        # StravaAuthState ORM model
app/schemas/strava.py       # StravaStatusOut, StravaConnectOut, StravaSyncReportOut
app/routes/strava.py        # connect / callback / sync / status / disconnect (all CORS-safe)
app/lib/workout_family.py   # + family_for_strava_sport_type()
alembic/versions/<rev>_strava_integration.py   # strava_auth_state table + CompletedWorkout columns
mobile/src/api/hooks/useStrava.ts              # connect / status / sync / disconnect
mobile/src/screens/SettingsScreen.tsx          # + Strava card (mirrors Garmin card)
```

Design intent: `oauth.py` and `sync.py` are independently testable; `client.py` is
the single network seam, mocked in tests exactly like `get_gemini_client`.

## Data model

### New table: `strava_auth_state` (one row per athlete)

Tokens live in the **database**, not on a disk volume (an improvement over Garmin's
on-disk `tokens.json`, which needed a Railway volume mount).

| Column | Type | Notes |
|---|---|---|
| `athlete_id` | UUID PK / FK → athletes.id (CASCADE) | one Strava connection per athlete |
| `access_token` | Text | short-lived (6h) |
| `refresh_token` | Text | long-lived |
| `expires_at` | timestamptz | access token expiry — converted from Strava's epoch-seconds `expires_at` at persist time |
| `athlete_strava_id` | BigInteger | Strava's athlete id |
| `scope` | Text | granted scope string |
| `last_successful_sync` | timestamptz, nullable | drives `?after=` and Settings display |
| `last_error` | Text, nullable | |
| `last_error_at` | timestamptz, nullable | |

### `CompletedWorkout` additions (Alembic migration)

- `strava_activity_id` (BigInteger, nullable) — dedup key for Strava-sourced rows
- `source` (String: `garmin` \| `strava` \| `manual`) — **backfill:** `garmin` where
  `garmin_activity_id IS NOT NULL`, else `manual`
- `avg_cadence` (Numeric, nullable)
- `avg_watts` (Numeric, nullable)
- `relative_effort` (Integer, nullable) — from Strava `suffer_score`
- existing `raw_summary_json` stores the full Strava activity payload

## OAuth + token lifecycle

- `GET /strava/connect` → returns the Strava authorize URL:
  `https://www.strava.com/oauth/authorize?client_id=<id>&redirect_uri=<STRAVA_REDIRECT_URI>&response_type=code&scope=activity:read_all&approval_prompt=auto`.
  Mobile opens it in an in-app browser.
- `GET /strava/callback?code=...&scope=...` → POST `https://www.strava.com/oauth/token`
  with `grant_type=authorization_code` → receive `access_token`, `refresh_token`,
  `expires_at`, `athlete.id` → upsert `strava_auth_state` → redirect back into the app
  (deep link / success page).
- **Inline token refresh** (`oauth.refresh`): before any Strava API call, if
  `expires_at` is within a 5-minute buffer, POST `/oauth/token` with
  `grant_type=refresh_token`, persist the new tokens. No background loop.

## Sync flow (polling)

`StravaSyncService.sync(since: date | None) -> StravaSyncReport`:

1. Resolve the client (refresh token inline if near expiry). If not connected, return empty.
2. `GET /api/v3/athlete/activities?after=<last_successful_sync or since, epoch>&per_page=100`,
   paginating until a short page.
3. Dedup: load existing `strava_activity_id`s in the batch; skip those already stored.
4. Map each activity → `CompletedWorkout`:
   - `id` → `strava_activity_id`; `source = 'strava'`
   - `distance` (m) → `distance_m`
   - `moving_time` (s) → `duration_s`
   - `start_date_local` → `started_at`; date portion → `activity_date`
   - `average_speed` (m/s) → `avg_pace_s_per_km = 1000 / average_speed` (guard zero)
   - `average_heartrate`/`max_heartrate` → `avg_hr`/`max_hr` (when `has_heartrate`)
   - `total_elevation_gain` → `elevation_gain_m`
   - `average_cadence` → `avg_cadence`; `average_watts` → `avg_watts`
   - `suffer_score` → `relative_effort`; `calories` → `calories`
   - `sport_type` → `activity_type`; `family_for_strava_sport_type(sport_type)` → `family`
   - full payload → `raw_summary_json`
5. Flush new rows, then call `reconcile(db, athlete_id)` (matches completed→planned,
   updates statuses). NOTE: the existing Garmin `/admin/sync` does **not** currently
   call `reconcile()` (the service runs only in tests today) — Strava does it
   correctly; wiring the Garmin path is a separate pre-existing follow-up, out of
   scope here.
6. Update `last_successful_sync`; on failure record `last_error`/`last_error_at` and
   surface via the route as a CORS-safe 502.

**Trigger:** manual "Sync now" (`POST /strava/sync`) + a client-side sync on app
open/login. No server-side scheduler in v1.

## API routes

All routes use route-level try/except converting upstream failures to
`HTTPException(502)` (missing config → 503) so 5xx responses keep CORS headers
(per the project's 5xx-CORS gotcha).

| Method | Path | Purpose |
|---|---|---|
| GET | `/strava/connect` | Return authorize URL (`StravaConnectOut`) |
| GET | `/strava/callback` | Exchange code, persist tokens, redirect to app |
| POST | `/strava/sync` | On-demand sync (`StravaSyncReportOut`) |
| GET | `/strava/status` | Connected? last sync? last error? (`StravaStatusOut`) |
| DELETE | `/strava/disconnect` | POST Strava `/oauth/deauthorize`, delete auth row |

## Mobile UX

A **"Strava" card** in `SettingsScreen`, mirroring the existing Garmin card:
- "Connect Strava" → opens the authorize URL in an in-app browser.
- After connect: shows last-sync time + a "Sync now" button.
- "Disconnect" → revokes and clears.
- New `useStrava` hook (connect / status / sync / disconnect) following existing
  hook patterns.

## Config / secrets (backend-only — never `EXPO_PUBLIC_*`)

- `STRAVA_CLIENT_ID`
- `STRAVA_CLIENT_SECRET`
- `STRAVA_REDIRECT_URI` (the deployed `GET /strava/callback` URL)

Added as `Settings` fields (default `""`); set on Railway. Missing config → routes
return 503 (CORS-safe), mirroring the Gemini key gate. One-time manual step:
register the API application + callback domain in Strava's developer settings.

## Testing (automated tests authored alongside the code)

Mock the network seam (`get_strava_client`) the same way the Gemini/Garmin tests do.
Coverage:
- `oauth.build_authorize_url` produces the correct URL + scope.
- code→token exchange persists `strava_auth_state` correctly.
- token refresh fires when `expires_at` is within the buffer; persists new tokens.
- activity → `CompletedWorkout` mapping (incl. `avg_pace_s_per_km` derivation and
  zero-speed guard, HR present/absent, cadence/watts/relative_effort).
- dedup: an already-stored `strava_activity_id` is skipped.
- `reconcile()` is invoked after ingest and matches a planned workout.
- disconnect deletes the auth row.
- route test: an upstream Strava failure returns a **CORS-safe 502**, missing config
  returns **503**.

Behavioral note (SDLC): unit tests mock Strava, so the real OAuth round-trip and
live activity pull require a **live smoke-test against Strava's API** (sandbox or the
athlete's own account) before declaring done — analogous to the coach-chat live test.

## Out of scope (v1)

Webhooks (real-time push), Streams/time-series ingestion, cross-source Garmin dedup,
posting activities *to* Strava, segments/kudos/comments, multi-account Strava.

## Done criteria

- [ ] OAuth round-trip works end-to-end against a real Strava account
- [ ] `POST /strava/sync` ingests new activities and maps them to `CompletedWorkout`
- [ ] `reconcile()` runs after ingest; a synced run flips its matching planned workout
- [ ] Inline token refresh works without user intervention
- [ ] Settings card: connect / sync / disconnect all function on the PWA
- [ ] Missing/invalid config and upstream failures return CORS-safe 503/502
- [ ] Full backend suite green in-container; mobile `tsc --noEmit` clean
- [ ] Garmin path remains untouched and functional (Strava is additive)
