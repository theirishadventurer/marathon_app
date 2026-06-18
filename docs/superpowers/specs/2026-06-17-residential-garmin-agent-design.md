# Residential Garmin Ingest Agent — Design

**Date:** 2026-06-17
**Status:** Approved (brainstorming complete) — ready for implementation plan
**Branch (proposed):** `session-5/garmin-residential-agent`

## Problem

Garmin Connect data is fetched via the unofficial `garminconnect`/`garth` library. The
existing `GarminSyncService` runs **inside the Railway container**, so its Garmin login
originates from a datacenter IP. Garmin's WAF rate-limits datacenter IPs with HTTP 429
(`garmin_sync.py:79-86` already defends against the silent-fail mode this produces), which
permanently breaks server-side Garmin sync in production.

Strava's official OAuth is the cloud-friendly alternative, but as of 2026-06-01 the Strava
API requires the developer to hold a paid Strava subscription (~$11.99/mo). The user has
declined to pay. The durable, free fix is to move **only the Garmin fetch** onto a
residential IP, while the server keeps ownership of storage.

## Goal

Split the sync into **fetch** (a small agent on the user's laptop, residential IP) and
**store** (the Railway backend). The agent talks to Garmin and POSTs already-fetched JSON to
a new token-authenticated ingest endpoint. The server never contacts Garmin. Includes an
optional on-demand "Sync now" trigger from the existing PWA via a poll-based flag (no
inbound connection to the laptop).

## Non-goals

- No native mobile app, no on-device Garmin fetch (would require reimplementing Garmin auth
  in JS + Apple Developer Program). The "Sync now" button only *triggers*; the laptop fetches.
- No cloud/serverless host for the fetch (all datacenter IPs → 429).
- No removal of the existing in-container `/garmin/sync` + `/garmin/reauth` endpoints. They
  are dead in prod (429) but harmless and still unit-tested; leave them.
- Displaying `DailyMetric` data in the app is separate follow-up work. The agent *ingests*
  metrics; surfacing them in the UI is out of scope here.

## Decisions (from brainstorming)

| Decision | Choice |
|---|---|
| Sync scope | Activities **and** daily metrics (sleep/HRV/resting HR/body battery/readiness) |
| Agent → API auth | Dedicated **ingest token** (not athlete password) |
| Host | User's laptop, Windows Task Scheduler; portable unchanged to a Pi/mini-PC later |
| Cadence | Launch at logon (catch-up) + periodic + on-demand; **14-day lookback** every run |
| On-demand trigger | "Sync now" button in PWA → poll-based flag the agent pulls |
| Old in-container endpoints | Leave in place |
| Security | Hardened — see Security section |

## Architecture

```
  LAPTOP (residential IP; agent's python.exe split-tunneled off NordVPN)   RAILWAY
 ┌───────────────────────────────────────────────┐        ┌───────────────────────────┐
 │ garmin_agent (watch mode, launched at logon)    │        │ FastAPI                   │
 │  - startup: catch-up sync (14-day lookback)     │        │                           │
 │  - loop: poll flag every ~60s; periodic sync    │        │                           │
 │  0. egress-IP guardrail (abort if datacenter/VPN)│        │                           │
 │  1. load cached garth token (interactive 1st run)│──Garmin (residential → no 429)     │
 │  2. get_activities_by_date(last 14d)            │        │                           │
 │  3. get_daily_stats(last 14d)                   │        │                           │
 │  4. POST {activities, metrics} ────────────────│──HTTPS─▶ POST /garmin/ingest         │
 │     header: X-Ingest-Token                      │        │   validate token (503/401) │
 │  5. GET /garmin/poll (is sync requested?) ──────│──HTTPS─▶ GET  /garmin/poll           │
 │                                                 │        │   → map + dedup + store →  │
 │                                                 │        │   CompletedWorkout +       │
 │                                                 │        │   DailyMetric (source=garmin)│
 └───────────────────────────────────────────────┘        └───────────────────────────┘
   PWA "Sync now" button ─ athlete JWT ─▶ POST /garmin/request-sync (sets flag) ──┘
```

Pull model only: the laptop initiates every connection. Nothing inbound to the laptop, no
port forward, no listener.

## Backend changes (Railway)

### Config (`app/config.py`)
- Add `garmin_ingest_token: str = ""` and `garmin_ingest_athlete_email: str = ""`.
- **Fail-closed in production:** when `app_env == production`, raise at startup if
  `garmin_ingest_token` is empty (mirrors the existing `SECRET_KEY` check). Local dev and the
  pytest suite (default `app_env=development`) keep working with empty defaults.

### Migration (small)
- Add `sync_requested_at` (`TIMESTAMP WITH TIME ZONE`, nullable) to `garmin_auth_state`.
  Timezone-aware to match the `datetime.now(UTC)` usage and the Strava `TIMESTAMPTZ` precedent.
- Up/down both verified.

### Refactor `app/services/garmin_sync.py` (no behavior change)
- Extract the activity-mapping loop (`:166-198`) into `map_activities(raw: list[dict],
  athlete_id) -> list[CompletedWorkout]` and the metric-mapping loop (`:235-259`) into
  `map_metrics(raw: list[dict], athlete_id) -> list[DailyMetric]`. Set `source="garmin"` on
  mapped activities.
- Existing `sync_activities` / `sync_daily_metrics` call these helpers. Existing tests stay green.

### New routes (`app/routes/garmin.py`)
1. `POST /garmin/ingest` — **ingest-token auth** via `X-Ingest-Token` header, **constant-time**
   compared to `settings.garmin_ingest_token`. Returns 503 if unconfigured, 401 on mismatch
   (CORS-safe). Resolves the athlete server-side from `settings.garmin_ingest_athlete_email`
   (the agent never selects the athlete). Body `{activities: [...], metrics: [...]}` →
   `map_activities` + `map_metrics` with dedup (by `garmin_activity_id` / `metric_date`),
   per-activity skip on malformed input, commit, update `last_successful_sync`, clear
   `sync_requested_at`. Returns counts (`SyncReport`-style). **Write-only; single athlete; no
   read path** (no IDOR, nothing to exfiltrate).
2. `GET /garmin/poll` — ingest-token auth. Returns `{ sync_requested: bool }` (true when
   `sync_requested_at` is set). Lightweight; the agent polls it ~every 60s.
3. `POST /garmin/request-sync` — **athlete JWT** auth (called by the PWA button). Sets
   `sync_requested_at = now(UTC)`. Returns `{ ok: true }`. CORS-safe.

### Tests (`tests/test_garmin_ingest.py`)
- 503 when `garmin_ingest_token` unconfigured.
- 401 on bad token; 200 on good token.
- Happy-path ingest creates `CompletedWorkout` + `DailyMetric`; second identical POST dedups
  (no duplicates).
- Malformed activity (missing required field) is skipped, not fatal (mirrors Strava hardening).
- Unknown/foreign `garmin_ingest_athlete_email` → rejected.
- `request-sync` sets the flag; `poll` reflects it; ingest clears it.

## Agent (`scripts/garmin_agent/`, committed; secrets gitignored)

- `agent.py`
  - `--once`: single fetch + ingest, then exit (for manual runs / pure-scheduled use).
  - `--watch` (default for Task Scheduler at logon): startup catch-up sync, then loop —
    poll `/garmin/poll` every ~60s and sync-on-demand when the flag is set, plus a periodic
    sync every ~6h (configurable). Exits cleanly on shutdown; relaunched at next logon
    (catch-up covers any gap).
  - **Egress-IP guardrail:** on each sync, fetch the agent's public IP and log it; if it
    resolves to a known datacenter/VPN ASN (or a configurable denylist), log a clear error and
    **abort the Garmin call** rather than burn a 429.
  - **Token caching:** first run is interactive (handles Garmin MFA if enabled), persists only
    the `garth` token; subsequent runs load it. On token expiry/invalidation, log a clear
    "re-run interactively" message.
- `requirements.txt` — **pinned versions + hashes** (`garminconnect`, `httpx`).
- `.env.example`, `README.md` — venv setup, first-run interactive login, Task Scheduler entry
  (logon trigger, "run whether logged on or not", "run ASAP after missed start"), NordVPN
  split-tunnel steps (add the venv `python.exe`), DPAPI secret setup.
- Real `.env` / token file are **gitignored**.

## Security

The user raised credential-at-rest risk. Posture:

1. **No Garmin password at rest** — interactive first login mints a `garth` token; the agent
   persists **only the token** (revocable, expiring), never the password.
2. **Windows DPAPI / Credential Manager** for the cached `garth` token and the ingest token,
   not a plaintext `.env` (encrypted at rest, tied to the Windows user).
3. **Recommend enabling MFA** on the Garmin account.
4. **Pinned + hashed deps** in an isolated venv (supply-chain containment for the unofficial
   `garminconnect`).
5. **Split tunneling is outbound routing only** — no inbound listener, no exposure. Garmin
   already sees the home IP from the official app/watch.
6. **Ingest endpoint** is write-only, single-athlete, token-gated (constant-time, fail-closed),
   strict payload validation, per-activity skip. Worst-case leak = bogus workouts injected
   into the log (annoying, not dangerous); rotate the token to revoke.

## Mobile (PWA — existing Expo app)

- `useRequestSync` hook → `POST /garmin/request-sync`.
- "Sync now" button on the Settings Garmin card (where Garmin status already lives). On tap: call the
  endpoint, show a toast ("Sync requested — your laptop will pick it up shortly"), optionally
  poll `/garmin/status` to reflect an updated `last_sync`. No native code; the button only
  triggers.

## Rollout

1. Merge backend + agent to master; deploy (Railway runs the migration on boot).
2. Set Railway env: `GARMIN_INGEST_TOKEN`, `GARMIN_INGEST_ATHLETE_EMAIL`.
3. On the laptop: create venv, configure DPAPI secrets, run `agent.py` once interactively
   (Garmin login / MFA), verify a successful ingest, add the NordVPN split-tunnel entry, then
   register the Task Scheduler logon task in `--watch` mode.

## Risks

- `garminconnect` is unofficial — Garmin may change web auth and break login (script edit to
  fix, not an app-store release). Residential IPs are throttled far less than datacenter, but
  not never; the egress guardrail + clear error logging make failures legible.
- Laptop-off windows: covered by 14-day lookback + dedup. If always-on matters later, move the
  same folder to a Pi/mini-PC unchanged.
