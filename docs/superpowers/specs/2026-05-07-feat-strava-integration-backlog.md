# Strava Integration — Backlog Stub

**Status:** Backlog. Not designed in detail. Placeholder for a future Session 2.8 (or later) brainstorming + design pass.

**Why:** The current `garminconnect` library is unofficial scraping of Garmin Connect's web auth. It's fragile to Garmin API changes, blocked by CAPTCHA on new IPs, and doesn't handle 2FA cleanly. Strava offers an official OAuth + webhook API. Garmin → Strava is a native Garmin Connect setting that users already have set up or can flip in one tap. Adding Strava as a secondary (or primary) data source eliminates ~80% of the Garmin-library fragility.

## High-level shape

### OAuth dance
- New endpoint `GET /strava/connect` initiates OAuth (returns Strava authorize URL with our `client_id` + `scope=activity:read,read`).
- Callback `GET /strava/callback?code=...` exchanges the code for an access + refresh token, persists to a new `strava_auth_state` table per-athlete.
- Token refresh handled in middleware or on-demand inside the sync loop (Strava tokens expire every 6 hours).

### Activity ingestion — two paths
**Option A: Webhook subscription (preferred).**
- Strava pushes a `create` event with the activity ID at the moment a Garmin watch syncs to Strava (typically <1 minute after run end).
- We hit `GET /api/v3/activities/{id}` to pull full data, map → `CompletedWorkout`, run reconciler.
- Endpoint: `POST /strava/webhook` (verifies the `subscription_id`, dispatches the activity fetch async).

**Option B: Polling (fallback).**
- Periodically (or on user "Sync now") hit `GET /api/v3/athlete/activities?after=<last_sync_ts>`.
- Same mapping logic. Higher latency, simpler implementation.

Recommendation: ship A; have B as an opt-in "manual catch-up" button.

### Mapping Strava → CompletedWorkout
- `id` → `garmin_activity_id` (rename to a generic `external_activity_id` later, or add a `source` column)
- `start_date_local` → `started_at`
- `start_date.split('T')[0]` → `activity_date`
- `type` (Run, TrailRun, etc.) → existing `family_for_garmin_activity_type` mapping (extend if needed)
- `distance` (meters) → `distance_m`
- `moving_time` (seconds) → `duration_s`
- `average_heartrate` → `avg_hr`
- `max_heartrate` → `max_hr`
- `total_elevation_gain` → `elevation_gain_m`
- `calories` → `calories`
- `average_speed` (m/s) → derive `avg_pace_s_per_km`

### Schema additions
- `strava_auth_state` table: `athlete_id`, `access_token`, `refresh_token`, `expires_at`, `athlete_strava_id`, `last_sync_ts`, `webhook_subscription_id`.
- Optional: add a `source` enum on `CompletedWorkout` (`garmin | strava | manual`) to disambiguate when both Garmin and Strava feeds are active. v1 can rely on `external_activity_id` uniqueness across sources.

### Mobile UX
- Settings → new "Strava" card alongside the existing Garmin card.
- "Connect Strava" button → opens an in-app browser to the OAuth authorize URL.
- After return: card shows last sync time + manual "Sync now" button (uses path B).
- Disconnect button revokes the token and deletes the auth state row.

### Out of scope (defer)
- Posting workouts FROM us TO Strava (one-way ingestion only for v1).
- Strava segments / kudos / comments.
- Multi-account Strava (one Strava connection per athlete).
- Showing Strava-specific metadata (e.g., suffer score, kudos count) in our UI.

### Open questions for the brainstorming pass
1. **Garmin coexistence.** When both Garmin and Strava are connected, do we dedupe activities (the same run lands twice — once via Garmin sync and once via Strava webhook)? Recommend dedupe by `started_at` ± 5 minutes; first-write-wins.
2. **Webhook security.** Strava webhooks require a one-time subscription verification challenge. Endpoint must respond to `GET /strava/webhook?hub.challenge=...`. Handle in the same route or a sibling.
3. **Rate limits.** Strava API: 100 requests / 15 min, 1000 / day. Webhook approach stays under both. Polling approach risks hitting them on bulk catch-up.
4. **Token refresh.** Inline on every API call (always check expiry, refresh if <5 min remaining), or background loop? Inline is simpler, slightly more latency.
5. **Privacy + scopes.** Strava `activity:read` returns public + follower-visible activities. For private activities we'd need `activity:read_all`. Worth asking the athlete which they want.

### Done criteria for the eventual spec
- [ ] OAuth round-trip works end-to-end against Strava sandbox
- [ ] Webhook receives and processes activity create events
- [ ] Activity mapping produces a valid `CompletedWorkout` + `Reconciliation` row
- [ ] Token refresh works without user intervention
- [ ] Settings UI: connect / sync / disconnect
- [ ] Dedupe with Garmin sync if both are active
- [ ] Existing Garmin path remains functional (Strava is additive, not a replacement)

### Estimated scope

~½ day for backend (OAuth + webhook + mapping + token refresh), ~½ day for mobile (Settings card + flow), ~1 day for testing against Strava's sandbox + handling edge cases. Total: 2 days of focused work — comparable to Session 2.7's Feat A or Feat B.

This stub is intentionally light. A full design pass should run through the brainstorming skill the same way Session 2.7's four features did.
