# Marathon App — Personal Deployment Runbook

**Date:** 2026-05-24
**Goal:** Get the marathon app running on the open internet for personal use — FastAPI + Postgres on Railway, Expo web build on Vercel, installed as a PWA on iPhone via Safari "Add to Home Screen."
**Estimated time:** 2–3 hours start to finish, assuming Railway + Vercel + GitHub accounts already exist.

---

## Architecture

```
iPhone Safari (PWA, add-to-home-screen)
        │
        │  HTTPS (CORS)
        ▼
Vercel (static)  ────────►  Railway
marathon-web.vercel.app      ├── api  (FastAPI Docker, prod CMD, 1 GB volume @ /app/data)
                             │   └─ marathon-api.up.railway.app
                             └── postgres (managed plugin, private network only)
```

**Auth model:** unchanged — JWT bearer in `Authorization` header, single user, password = `SEED_PASSWORD` env var.

---

## §0 — Pre-flight

Before you start, verify:
- [ ] Railway account with a project + Hobby plan ($5/mo) — you have this
- [ ] Vercel account on free tier — you have this
- [ ] GitHub repo for the marathon project, with this branch pushed (or master)
- [ ] iPhone running iOS 16+ (PWA install works on older too, just polish varies)
- [ ] Garmin Connect username + password handy
- [ ] (Optional) Anthropic API key if you want AI rebalance to keep working in deployment
- [ ] A fresh 32-byte hex string for `SECRET_KEY` — generate with:
  ```powershell
  python -c "import secrets; print(secrets.token_hex(32))"
  ```
- [ ] A login password you'll remember — this becomes `SEED_PASSWORD`

Work on a deploy branch so master stays clean:
```powershell
git checkout -b deploy/personal-launch
```

---

## §1 — Backend code changes (10 commits, ~30 min)

These are the only code changes the deploy needs. Each is small and self-contained — commit as you go.

### 1.1 — Production Dockerfile

Create `Dockerfile.prod` (alongside the existing `Dockerfile`):

```dockerfile
FROM python:3.12-slim

WORKDIR /app

RUN pip install uv

COPY pyproject.toml .
RUN uv pip install --system .

COPY . .

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
```

Differences from dev `Dockerfile`:
- No `[dev]` extras (no pytest, ruff in prod image)
- No `--reload`
- `--workers 2` for prod concurrency
- No volume mount — code is baked into the image

### 1.2 — `railway.json`

Create `railway.json` at the repo root:

```json
{
  "$schema": "https://railway.app/railway.schema.json",
  "build": {
    "builder": "DOCKERFILE",
    "dockerfilePath": "Dockerfile.prod"
  },
  "deploy": {
    "startCommand": "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 2",
    "healthcheckPath": "/health",
    "healthcheckTimeout": 30,
    "restartPolicyType": "ON_FAILURE",
    "restartPolicyMaxRetries": 3
  }
}
```

The `alembic upgrade head &&` runs migrations on every deploy before the server starts. Idempotent — does nothing if already at head.

### 1.3 — `app/config.py` — add prod env vars + Railway DB URL adapter

Replace the file with:

```python
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    database_url: str = "postgresql+asyncpg://marathon:marathon@db:5432/marathon"
    secret_key: str = "change-me-to-a-real-secret"
    seed_password: str = "marathon"
    anthropic_api_key: str = ""
    tz: str = "America/New_York"
    jwt_expiry_days: int = 30

    # Production additions
    web_origin: str = "*"  # locked down via Railway env in prod
    garmin_username: str = ""
    garmin_password: str = ""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Railway's Postgres plugin gives `postgresql://...`; SQLAlchemy async needs `postgresql+asyncpg://...`
        if self.database_url.startswith("postgresql://"):
            self.database_url = self.database_url.replace("postgresql://", "postgresql+asyncpg://", 1)


settings = Settings()
```

### 1.4 — `app/main.py` — lock down CORS

In `app/main.py:24-30`, replace the CORS block with:

```python
from app.config import settings

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.web_origin] if settings.web_origin != "*" else ["*"],
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=False,
)
```

(Locally, `web_origin` stays `"*"` from the default; on Railway you'll set it to your Vercel URL.)

### 1.5 — Wire `SEED_PASSWORD` into the seed script

Right now `app/seed/load_plan.py:24` hardcodes `DEFAULT_PASSWORD = "changeme123"` — your login password would be that and there's no way to set it via env. Fix it:

In `app/seed/load_plan.py`, change the top of the file:

```python
import os
# ... existing imports ...

PLAN_NAME = "Marathon Trilogy 2026-2027"
DEFAULT_PASSWORD = os.environ.get("SEED_PASSWORD", "changeme123")
```

(Ruff E402 watch: keep `import os` at the top of the imports block.) Now your Railway `SEED_PASSWORD` env var becomes the actual login password.

### 1.6 — Sanity check locally before pushing

```powershell
docker compose up -d --build
docker compose exec -T api pytest
```

Expect all tests green. If anything red, fix before continuing.

### 1.7 — Commit the backend changes

```powershell
git add Dockerfile.prod railway.json app/config.py app/main.py app/seed/load_plan.py
git commit -m "feat(deploy): prod Dockerfile + railway.json + CORS lockdown + env-driven seed password"
git push -u origin deploy/personal-launch
```

---

## §2 — Railway setup (~30 min, mostly waiting on builds)

### 2.1 — Provision Postgres

In your existing Railway project:
1. Click **+ New** → **Database** → **Add PostgreSQL**.
2. Wait for it to provision (~30s). It will auto-inject a `DATABASE_URL` into any service that's linked to it.

### 2.2 — Provision the API service

1. **+ New** → **GitHub Repo** → select the marathon repo → branch `deploy/personal-launch`.
2. Once the service is created, click into it → **Settings**:
   - **Build:** Railway should auto-detect `railway.json` and use `Dockerfile.prod`. Verify.
   - **Networking:** click **Generate Domain** — Railway gives you something like `marathon-api-production-xxxx.up.railway.app`. **Copy this URL** — you'll need it for Vercel.
3. **Variables** tab — add all of these (Railway auto-injects `DATABASE_URL` via the service link, but verify it's present):

   | Variable | Value |
   |---|---|
   | `SECRET_KEY` | `<the 32-byte hex you generated>` |
   | `SEED_PASSWORD` | `<the login password you chose>` |
   | `WEB_ORIGIN` | placeholder for now — `https://example.com` |
   | `GARMIN_USERNAME` | your Garmin email |
   | `GARMIN_PASSWORD` | your Garmin password |
   | `ANTHROPIC_API_KEY` | your key (or skip if not using AI features) |
   | `TZ` | `America/New_York` |

4. **Connect Postgres to the API service:**
   - Service → **Variables** → **Add Variable Reference** → pick the Postgres service's `DATABASE_URL`.
   - Railway will redeploy automatically.

### 2.3 — Attach a volume for Garmin tokens

Garmin tokens are written to `./data/garmin_tokens/<athlete_id>/tokens.json` — without a persistent volume, every redeploy wipes the tokens and you'd have to re-auth manually each time.

1. API service → **Settings** → **Volumes** → **+ New Volume**.
2. Mount path: `/app/data`, size: 1 GB. (Costs ~$0.25/mo on Railway pricing.)
3. Railway will redeploy.

### 2.4 — Verify the API is up

After the deploy finishes:
```powershell
curl https://<your-railway-url>/health
```
Expect `{"status":"ok"}`. If you get a 502, check **Deployments** tab → **View Logs** — likely either:
- Migration failed (most common: `DATABASE_URL` not wired) → fix the var reference
- Import error → look for the traceback

### 2.5 — Seed the marathon plan (one-time)

In the API service, open the **Shell** (top right of the service page):
```bash
python -m app.seed.load_plan
```
This loads the marathon training plan into Postgres. Expect output ending with "Plan loaded." (or similar). If it fails because the plan already exists, that's fine — it means a prior boot already seeded.

### 2.6 — Find your athlete_id

The seed creates an athlete with a random UUID, identified by the email in `PLAN.md`. To get the ID, run in Railway shell:

```bash
python -c "
import asyncio
from sqlalchemy import select
from app.db import async_session_factory
from app.models.athlete import Athlete
async def go():
    async with async_session_factory() as db:
        rows = (await db.execute(select(Athlete.id, Athlete.email))).all()
        for r in rows:
            print(r)
asyncio.run(go())
"
```

Copy the UUID — you'll need it next.

### 2.7 — Bootstrap Garmin auth (one-time)

The Garmin client needs a one-time login to mint tokens, which then persist to the volume.

Easiest path: once the web app is up (§5), tap **Sync** on the Today screen or use the Settings flow that calls `POST /garmin/reauth`. The route reads `GARMIN_USERNAME` / `GARMIN_PASSWORD` from env and writes tokens to `/app/data/garmin_tokens/<athlete_id>/tokens.json`.

Manual alternative via Railway shell:
```bash
python -c "
import asyncio
from app.db import async_session_factory
from app.services.garmin_sync import GarminSyncService
from app.config import settings
async def go():
    async with async_session_factory() as db:
        svc = GarminSyncService(db, athlete_id='<paste-uuid-from-2.6>')
        await svc.reauth(settings.garmin_username, settings.garmin_password)
        print('Garmin tokens minted')
asyncio.run(go())
"
```

Verify with `ls /app/data/garmin_tokens/`. You should see a folder named with your athlete UUID containing `tokens.json`.

---

## §3 — Web/Vercel code changes (~15 min)

### 3.1 — PWA polish in `mobile/app.json`

Replace the `web` block:

```json
"web": {
  "favicon": "./assets/favicon.png",
  "name": "Marathon Coach",
  "shortName": "Marathon",
  "themeColor": "#0e1320",
  "backgroundColor": "#0e1320",
  "display": "standalone",
  "orientation": "portrait",
  "lang": "en-US"
}
```

This tells Expo's web bundler to emit a PWA manifest plus iOS Safari meta tags, so "Add to Home Screen" gets a proper icon, fullscreen launch, and dark navy splash.

### 3.2 — Apple touch icon

Drop a 180×180 PNG (no transparency — iOS adds the corner radius itself) at `mobile/assets/apple-touch-icon.png`. If you don't have one, just copy the existing `mobile/assets/icon.png` and resize to 180×180.

### 3.3 — Vercel project config

Create `mobile/vercel.json`:

```json
{
  "$schema": "https://openapi.vercel.sh/vercel.json",
  "buildCommand": "npx expo export -p web",
  "outputDirectory": "dist",
  "framework": null,
  "installCommand": "npm install"
}
```

### 3.4 — Verify local web build

```powershell
cd mobile
npx expo export -p web
```

Expect a `dist/` folder. Open `dist/index.html` to sanity check the output exists. **Don't open it in a browser** — file:// won't run an SPA. We'll let Vercel serve it.

### 3.5 — Commit and push

```powershell
cd ..
git add mobile/app.json mobile/vercel.json mobile/assets/apple-touch-icon.png
git commit -m "feat(deploy): PWA manifest + Vercel config for personal web deploy"
git push
```

---

## §4 — Vercel deploy (~10 min)

1. Vercel dashboard → **+ Add New** → **Project** → import the marathon repo.
2. **Configure project:**
   - **Root directory:** `mobile` (critical — the Expo app lives here, not at repo root)
   - **Framework preset:** Other (Vercel may auto-detect; that's fine)
   - **Build & output settings:** leave the defaults — Vercel will read `mobile/vercel.json`.
3. **Environment variables:**
   - `EXPO_PUBLIC_API_URL` = `https://<your-railway-url>` (from §2.2)
   - Important: anything prefixed `EXPO_PUBLIC_` is inlined into the JS bundle — never put a secret here.
4. **Deploy** — first build takes 2–3 min.
5. Once it lights up green, you'll get a URL like `marathon-<hash>.vercel.app`. You can rename it under **Settings → Domains** to something cleaner like `marathon-cab.vercel.app`.

### 4.1 — Close the CORS loop

Now go back to Railway → API service → **Variables** → update:
```
WEB_ORIGIN = https://marathon-cab.vercel.app   (or whatever your Vercel URL ended up)
```
Railway redeploys. CORS now allows the web app to call the API.

### 4.2 — Verify end-to-end

In your iPhone Safari (or desktop browser first if easier):
1. Visit your Vercel URL.
2. Login screen should render. Login with `SEED_PASSWORD`.
3. You should see the Today screen with the seeded plan.

If you get a CORS error in the browser console, double-check `WEB_ORIGIN` matches your Vercel URL exactly (no trailing slash, https not http).

---

## §5 — iPhone PWA install

On your iPhone, in Safari:
1. Navigate to your Vercel URL.
2. Tap the **Share** icon (square with arrow up).
3. Scroll down → **Add to Home Screen**.
4. Name it "Marathon" (or whatever) → **Add**.

Open from your home screen. Expected:
- Fullscreen (no Safari chrome) because of `display: standalone`
- Dark navy splash because of `backgroundColor: "#0e1320"`
- Your icon, properly rounded

---

## §6 — Smoke test checklist

Tap through every screen and verify nothing's broken on iOS Safari:

- [ ] Login screen accepts your password
- [ ] **Today** — coach brief loads, recent runs strip renders, sync button works (will trigger Garmin pull)
- [ ] **Week** — DayToggle (M–S) responsive; tap a day; drag-to-move a workout to a different day
- [ ] **Program** — BrandBanner renders, 3-lane world map scrolls, WeeklyMileageTracker bars render
- [ ] **WorkoutDetail** — opens; MARK DONE flow works; EDIT flow works; BottomActionBar pinned to bottom (safe-area)
- [ ] **Settings** — RESET START DATE preview + apply works
- [ ] Sign out → log back in → token persisted in localStorage (no re-login needed unless you cleared it)

Web-specific known fragile areas to pay extra attention to:
- `@gorhom/bottom-sheet` — drag-to-dismiss may feel different on iOS Safari touch
- `react-native-gesture-handler` drag-to-move — should work via PointerEvents but smoke test it
- Fonts (PressStart2P / JetBrains Mono / VT323) — load via expo-font, which on web becomes CSS `@font-face`. First load may flash unstyled text; subsequent loads cached.

---

## §7 — Day-2 ops

**Redeploy after a code change:**
```powershell
git push   # both Railway and Vercel auto-deploy on push to the branch they're tracking
```

**Roll back a bad deploy:**
- Railway: **Deployments** tab → pick last good deploy → **Redeploy**.
- Vercel: **Deployments** tab → pick last good → **Promote to Production**.

**Rotate Garmin password:**
1. Change in Garmin Connect.
2. Update `GARMIN_PASSWORD` env var on Railway (auto-redeploys).
3. Re-run §2.6 to refresh tokens.

**Rotate `SECRET_KEY`:**
- This invalidates your current JWT — you'll have to log back in once. Just update the var on Railway.

**Check API logs:**
- Railway → API service → **Deployments** → click latest → **View Logs**.

**Check web logs:**
- Vercel → project → **Logs** tab.

**Postgres backup:**
- Railway Postgres plugin includes daily snapshots on Hobby plan. Confirm under the Postgres service → **Settings** → **Backups**. For personal use this is enough.

---

## §8 — Known risks & open questions

| Risk | Why | Mitigation |
|---|---|---|
| Garmin scraper fails from Railway IPs | `garminconnect` is unofficial; Garmin sometimes rate-limits/blocks datacenter IPs | If sync starts failing, fall back to manual mark-complete (Session 2.7 flow). Long-term: the Strava integration on the backlog (`docs/superpowers/specs/2026-05-07-feat-strava-integration-backlog.md`) replaces this. |
| Bottom sheets feel wrong on iOS Safari | `@gorhom/bottom-sheet` web support is workable but not pixel-perfect | Smoke-test in §6. If unacceptable, swap sheets for a simpler modal on web (`Platform.OS === 'web'` branch). |
| Drag-to-move feels jittery on touch web | `react-native-gesture-handler` web uses PointerEvents | If it's bad, can disable drag on web only and rely on the Edit flow. |
| iOS PWA loses localStorage on long inactivity | iOS purges site data after ~7 days of disuse | You'd have to re-login. Acceptable cost. JWT expiry is 30 days anyway. |
| Railway free credits run out | $5/mo Hobby is enough for this app, but if you idle the service for a long time and come back, you'll see usage spikes around the migration run | Just keep an eye on the usage page first week. |
| Migrations fail mid-deploy | `alembic upgrade head` in `startCommand` could brick the boot | Roll back to last good deploy in Railway, fix migration locally, push fix. |

---

## §9 — Quick reference card

**URLs:**
- API: `https://<railway-url>/health` — should return `{"status":"ok"}`
- Web: `https://<vercel-url>` — login page

**Env vars cheat sheet:**

Railway (API service):
```
DATABASE_URL=<auto from Postgres plugin>
SECRET_KEY=<32-byte hex>
SEED_PASSWORD=<your login password>
WEB_ORIGIN=https://<vercel-url>
GARMIN_USERNAME=<email>
GARMIN_PASSWORD=<password>
ANTHROPIC_API_KEY=<key>
TZ=America/New_York
```

Vercel (web project):
```
EXPO_PUBLIC_API_URL=https://<railway-url>
```

**The login password is `SEED_PASSWORD`.** Don't forget it.

---

## Done

After §5 you should be tapping the marathon icon on your iPhone home screen and using the app. If anything in §6 is broken, list which ones and we'll tackle them in a follow-up session.
