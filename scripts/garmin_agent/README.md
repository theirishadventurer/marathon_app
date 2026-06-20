# Garmin Residential Agent — Setup, Scheduling & Smoke-test Runbook

This agent runs on your **home laptop** (or any always-on home machine) and
periodically pushes Garmin Connect activity and daily-metric data to the
Marathon App backend.  It must run from a residential IP because Garmin's WAF
rate-limits (HTTP 429) datacenter and VPN egress IPs — which is the sole reason
this agent exists as a local process rather than a Railway service.

---

## 1. Backend — Railway env vars (one-time)

Before the agent can push data, the backend needs two env vars set in Railway.

### 1a. Generate an ingest token

```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

Copy the output — you will need this same value in **both** Railway and the
laptop setup below.

### 1b. Set the vars in Railway

| Variable | Value |
|---|---|
| `GARMIN_INGEST_TOKEN` | the token you just generated |
| `GARMIN_INGEST_ATHLETE_EMAIL` | the Marathon App login email whose data the agent ingests |

Redeploy after saving (Railway does not hot-reload env vars).

### 1c. Verify

```bash
curl -s -H "X-Ingest-Token: <your-token>" \
  https://<your-railway-app>.up.railway.app/garmin/poll
```

Expected response: `{"sync_requested": false}`

A `503` means the env var is not set (or the deploy did not finish).
A `403` means the token does not match.

---

## 2. Laptop — Python environment

```cmd
cd scripts\garmin_agent
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

Python 3.11+ is required (3.13 is the tested version).

---

## 3. Laptop — `.env` file

```cmd
copy .env.example .env
```

Open `.env` and set:

| Key | What to put |
|---|---|
| `MARATHON_API_URL` | Your Railway backend URL, e.g. `https://marathonapp-production-cc63.up.railway.app` (no trailing slash) |
| `GARMIN_EMAIL` | Your Garmin Connect account email |

The other keys (`LOOKBACK_DAYS`, `POLL_SECONDS`, `PERIODIC_HOURS`,
`ALLOWED_IP_PREFIXES`) have sensible defaults and can be left as-is for the
first run.

> **Never commit `.env`** — it is gitignored.  Secrets (the ingest token and
> the Garmin session token) are stored in Windows Credential Manager via
> `keyring`, not in `.env`.

---

## 4. Store secrets in Windows Credential Manager

Run this once.  It will prompt you to paste the ingest token (the same value
you set on Railway).

```cmd
.venv\Scripts\python.exe -m garmin_agent.agent --set-secrets
```

Paste the token at the prompt and press Enter.  The token is stored under the
service name `marathon-garmin-agent` in Windows Credential Manager.

---

## 5. Interactive Garmin login (one-time, with MFA)

```cmd
.venv\Scripts\python.exe -m garmin_agent.agent --login
```

This will:
1. Prompt for your Garmin Connect password (via `getpass` — not echoed,
   never stored to disk).
2. If your account has two-factor authentication enabled, prompt for the MFA
   code on the console.
3. Cache the resulting `garth` session token in Windows Credential Manager.

After this step the agent can sync without your password.  Re-run `--login`
any time `agent.log` reports that the cached token was rejected.

---

## 6. NordVPN split tunnel (critical — must be done before first sync)

Garmin's WAF rejects datacenter and VPN egress IPs with HTTP 429.  The agent's
egress guard is **fail-closed**: before every sync it checks the machine's
public IP via `ip-api.com` and **refuses to run** if:

- the IP is classified as a datacenter/VPN host (`hosting: true` or
  `proxy: true`), or
- the ip-api.com lookup itself fails for any reason.

This means if NordVPN is routing the agent's traffic through a VPN exit, syncs
will silently pause until the split tunnel is configured.  Failures and pauses
are logged in `agent.log`.

### Configure split tunneling in NordVPN

1. Open **NordVPN** → **Settings** → **Split Tunneling**.
2. Enable split tunneling, set mode to **"Disable VPN for selected apps"**.
3. Click **Add apps** and add:
   ```
   scripts\garmin_agent\.venv\Scripts\python.exe
   ```
4. Save.

After this, the agent's Python process routes through your home ISP while all
other traffic stays on NordVPN.

### Optional: whitelist a known home IP prefix

If your ISP's ASN triggers a false-positive `hosting: true` classification,
you can add your home IP prefix to `.env`:

```
ALLOWED_IP_PREFIXES=203.0.113.
```

A prefix match always wins and bypasses the datacenter check.

---

## 7. Smoke-test (`--once`)

With NordVPN split tunnel active:

```cmd
.venv\Scripts\python.exe -m garmin_agent.agent --once
```

Check `agent.log` (in `scripts\garmin_agent\`) for:

```
INFO egress IP <your-home-ip> OK (residential)
INFO ingest ok: +N activities, +M metrics, 0 skipped
```

Then open the Marathon App PWA and confirm a recent activity appears in the
dashboard.

If you see `ABORT: egress IP ... looks like a datacenter/VPN exit`, the split
tunnel is not active for this Python executable — re-check step 6.

If `agent.log` says `Cached token rejected`, re-run `--login` (step 5).

---

## 8. On-demand sync ("Sync now" in PWA Settings)

Start the agent in watch mode:

```cmd
.venv\Scripts\python.exe -m garmin_agent.agent --watch
```

In the PWA, go to **Settings** and tap **Sync now**.  Within approximately
`POLL_SECONDS` (default: 60 seconds), `agent.log` should show:

```
INFO on-demand sync requested
INFO egress IP <your-home-ip> OK (residential)
INFO ingest ok: +N activities, +M metrics, ...
```

The backend's `sync_requested` flag is automatically cleared after the agent
reads it.

---

## 9. Windows Task Scheduler (persistent background run)

Register the agent as a scheduled task so it starts automatically at login and
restarts if missed.

1. Open **Task Scheduler** → **Create Task** (not Basic Task).
2. **General** tab:
   - Name: `Marathon Garmin Agent`
   - Select **"Run whether user is logged on or not"** if you want it to run
     even at the lock screen (requires storing your Windows password).
3. **Triggers** tab → **New**:
   - Begin the task: **At log on**
4. **Actions** tab → **New**:
   - Action: **Start a program**
   - Program/script:
     ```
     C:\Coding Projects\marathon_app\scripts\garmin_agent\.venv\Scripts\python.exe
     ```
   - Add arguments:
     ```
     -m garmin_agent.agent --watch
     ```
   - Start in (this is the working directory — required for `.env` and `agent.log` paths):
     ```
     C:\Coding Projects\marathon_app\scripts\garmin_agent
     ```
5. **Settings** tab:
   - Enable **"Run task as soon as possible after a scheduled start is missed"**.
6. Click **OK** and enter your Windows credentials if prompted.

To verify: log out and back in, wait ~30 seconds, then check `agent.log` for
the watch-mode startup line:

```
INFO watch mode: startup catch-up sync
```

---

## 10. Moving to an always-on machine (optional, later)

If you later want the agent to run on a Raspberry Pi, Mac mini, or NUC on your
home WiFi instead of your laptop:

1. Copy the `scripts/garmin_agent/` folder to the target machine.
2. Repeat steps 2–6 on that machine (create venv, install deps, copy `.env`,
   store secrets, run `--login`).
3. Set up a cron job (Linux/macOS) or Task Scheduler task (Windows) pointing at
   `--watch`.
4. No code changes required — the agent is already written to be
   machine-portable.

---

## 11. Known limitations / follow-ups

### Metrics enrichment (daily summary only)

The agent currently fetches daily metrics via `get_stats(date)`, which returns
the **daily summary only**.  Fields populated from this endpoint:

- `restingHeartRate`
- `bodyBattery*` values

The following fields are returned as `null` until a follow-up enrichment pass
is implemented:

| Field | Garmin SDK endpoint needed |
|---|---|
| `sleepScore` | `get_sleep_data(date)` |
| `hrvOvernight` | `get_hrv_data(date, date)` |
| `trainingReadiness` | `get_training_readiness(date)` |
| `trainingStatus` | `get_training_status(date)` |

All four endpoints are present in `garminconnect 0.2.25`.  `null` values for
these fields during the smoke-test are expected and not a bug.  A follow-up
task will merge these endpoints into `garmin_fetch.fetch()` after validating
the response shapes against a live payload.

### ip-api.com availability

The egress guard calls `ip-api.com` over plain HTTP (the free tier does not
offer HTTPS).  A man-in-the-middle could spoof the response to bypass the guard
— accepted risk, since worst-case impact is a degraded Garmin sync, not asset
compromise.  If `ip-api.com` is unreachable for any reason, syncs pause until
it recovers (fail-closed, intentional).

---

## Quick reference

| Command | Purpose |
|---|---|
| `python -m garmin_agent.agent --set-secrets` | Store ingest token in Windows Credential Manager |
| `python -m garmin_agent.agent --login` | Interactive Garmin login (handles MFA, caches session) |
| `python -m garmin_agent.agent --once` | Single sync and exit (smoke-test) |
| `python -m garmin_agent.agent --watch` | Continuous poll loop (normal running mode) |

Log file: `scripts\garmin_agent\agent.log` (rotates at 1 MB, keeps 3 backups).
