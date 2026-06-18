# Residential Garmin Ingest Agent — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Move the Garmin fetch onto a residential laptop agent that POSTs activities + daily metrics to a new token-authenticated backend ingest endpoint, with an on-demand "Sync now" trigger from the PWA.

**Architecture:** Split sync into *fetch* (laptop agent, residential IP — avoids Garmin's datacenter 429) and *store* (Railway backend, never contacts Garmin). The agent pulls everything (no inbound to the laptop): it fetches from Garmin, POSTs to `/garmin/ingest`, and polls `/garmin/poll` for an on-demand flag the PWA sets via `/garmin/request-sync`.

**Tech Stack:** Backend — FastAPI, Pydantic v2, SQLAlchemy async, Alembic, pytest (in Docker). Agent — standalone Python (`garminconnect`, `httpx`, `keyring`), Windows Task Scheduler. Mobile — Expo/React Native, TanStack Query.

## Global Constraints

- Backend tests run in container: `docker compose exec -T api pytest` (host has no deps).
- Pydantic v2: use `Field(validation_alias=...)` not `alias=` for input-only mapping.
- Fail-closed config checks fire **only** when `APP_ENV=production` (dev + pytest use defaults).
- 5xx without CORS headers reads as "CORS blocked" in the browser — convert expected failures to explicit `HTTPException(4xx)` / 503 so CORS headers survive.
- Mobile validation gate per task: `cd mobile && npx tsc --noEmit`. No jest infra.
- Keep files under ~500 lines; hoist imports to top (ruff E402).
- Agent secrets: **never** store the Garmin password at rest; persist only the `garth` token + ingest token via `keyring` (Windows Credential Manager / DPAPI). Real `.env`/token files are gitignored.
- Migration head before this work: `3ef08f92d555`. New migration's `down_revision` = `3ef08f92d555`.
- Sync scope = activities **and** daily metrics. `source="garmin"` on ingested activities.
- Leave the existing in-container `/garmin/sync`, `/garmin/reauth`, `/admin/sync` endpoints untouched.

---

## File Structure

**Backend**
- Modify `app/config.py` — `garmin_ingest_token`, `garmin_ingest_athlete_email` + fail-closed check.
- Modify `app/models/garmin.py` — `sync_requested_at` column.
- Create `alembic/versions/<rev>_garmin_sync_requested_at.py` — migration.
- Modify `app/services/garmin_sync.py` — extract pure `map_activity` / `map_metric`.
- Modify `app/schemas/garmin.py` — `GarminIngestRequest`, `GarminIngestResponse`, `GarminPollOut`.
- Modify `app/deps.py` — `require_ingest_token`, `get_ingest_athlete`.
- Modify `app/routes/garmin.py` — `POST /garmin/ingest`, `GET /garmin/poll`, `POST /garmin/request-sync`.
- Create `tests/test_garmin_ingest.py`.
- Modify `tests/test_config.py` — fail-closed ingest-token test.

**Mobile**
- Modify `mobile/src/api/hooks/useGarmin.ts` — `useRequestSync`.
- Modify `mobile/src/screens/SettingsScreen.tsx` — repoint the existing "Sync now" button.

**Agent** (`scripts/garmin_agent/`)
- Create `garmin_agent/__init__.py`, `config.py`, `ipguard.py`, `garmin_fetch.py`, `api_client.py`, `agent.py`.
- Create `requirements.txt`, `.env.example`, `README.md`.
- Create `tests/test_ipguard.py`, `tests/test_payload.py`.
- Modify root `.gitignore` — agent secrets.

---

# Phase 1 — Backend ingest pipeline

### Task 1: Config fields + fail-closed check

**Files:**
- Modify: `app/config.py`
- Test: `tests/test_config.py`

**Interfaces:**
- Produces: `settings.garmin_ingest_token: str`, `settings.garmin_ingest_athlete_email: str`.

- [ ] **Step 1: Write the failing test** — append to `tests/test_config.py`:

```python
def test_production_requires_garmin_ingest_token():
    import pytest
    from app.config import Settings
    with pytest.raises(RuntimeError, match="GARMIN_INGEST_TOKEN"):
        Settings(
            app_env="production",
            secret_key="x" * 40,
            garmin_ingest_token="",
        )


def test_production_allows_garmin_ingest_token_set():
    from app.config import Settings
    s = Settings(
        app_env="production",
        secret_key="x" * 40,
        garmin_ingest_token="a-real-token",
    )
    assert s.garmin_ingest_token == "a-real-token"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `docker compose exec -T api pytest tests/test_config.py::test_production_requires_garmin_ingest_token -v`
Expected: FAIL (no RuntimeError raised — field/check absent).

- [ ] **Step 3: Implement** — in `app/config.py`, add fields after `strava_redirect_uri` (line 21):

```python
    garmin_ingest_token: str = ""
    garmin_ingest_athlete_email: str = ""
```

Then inside `__init__`, at the end of the `if self.is_production:` block (after the secret-key checks, ~line 63), add:

```python
            if not self.garmin_ingest_token:
                raise RuntimeError(
                    "GARMIN_INGEST_TOKEN is unset in production. Generate one with "
                    "`python -c \"import secrets; print(secrets.token_urlsafe(32))\"` "
                    "and set it in the Railway environment."
                )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `docker compose exec -T api pytest tests/test_config.py -v`
Expected: PASS (all config tests).

- [ ] **Step 5: Commit**

```bash
git add app/config.py tests/test_config.py
git commit -m "feat(garmin): ingest-token config + fail-closed prod check"
```

---

### Task 2: Model column + migration

**Files:**
- Modify: `app/models/garmin.py:25`
- Create: `alembic/versions/<rev>_garmin_sync_requested_at.py`

**Interfaces:**
- Produces: `GarminAuthState.sync_requested_at: datetime | None` (TIMESTAMPTZ).

- [ ] **Step 1: Add the column** — in `app/models/garmin.py`, add imports and the column. Change the import line 6 to include `DateTime`:

```python
from sqlalchemy import Boolean, DateTime, ForeignKey, Text
```

Add after `needs_reauth` (line 25):

```python
    sync_requested_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
```

- [ ] **Step 2: Generate an empty migration revision** (auto-sets `down_revision` to head)

Run: `docker compose exec -T api alembic revision -m "garmin sync_requested_at"`
Expected: prints `Generating .../alembic/versions/<rev>_garmin_sync_requested_at.py`.

- [ ] **Step 3: Fill the migration body** — replace the generated `upgrade`/`downgrade` with:

```python
import sqlalchemy as sa
from alembic import op


def upgrade() -> None:
    op.add_column(
        "garmin_auth_state",
        sa.Column("sync_requested_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("garmin_auth_state", "sync_requested_at")
```

Leave the auto-generated `revision`/`down_revision` lines as-is (down_revision must be `3ef08f92d555`).

- [ ] **Step 4: Apply + verify the migration round-trips**

Run:
```bash
docker compose exec -T api alembic upgrade head
docker compose exec -T api alembic downgrade -1
docker compose exec -T api alembic upgrade head
```
Expected: each completes without error; final state at head.

- [ ] **Step 5: Commit**

```bash
git add app/models/garmin.py alembic/versions/
git commit -m "feat(garmin): sync_requested_at column + migration"
```

---

### Task 3: Refactor garmin_sync into pure per-item mappers

**Files:**
- Modify: `app/services/garmin_sync.py`
- Test: `tests/test_garmin_sync.py` (existing — must stay green)

**Interfaces:**
- Produces (module-level functions):
  - `map_activity(act: dict, athlete_id: str) -> CompletedWorkout | None`
  - `map_metric(day: dict, athlete_id: str) -> DailyMetric | None`

  Both return `None` for malformed input (missing required keys) instead of raising.

- [ ] **Step 1: Write the failing test** — append to `tests/test_garmin_sync.py`:

```python
def test_map_activity_maps_core_fields():
    from app.services.garmin_sync import map_activity
    act = {
        "activityId": 555,
        "startTimeLocal": "2026-06-10 07:30:00",
        "activityType": {"typeKey": "running"},
        "duration": 1800,
        "distance": 5000,
        "averageHR": 150,
        "maxHR": 170,
    }
    w = map_activity(act, "11111111-1111-1111-1111-111111111111")
    assert w is not None
    assert w.garmin_activity_id == 555
    assert w.source == "garmin"
    assert w.duration_s == 1800


def test_map_activity_returns_none_when_malformed():
    from app.services.garmin_sync import map_activity
    assert map_activity({"startTimeLocal": "2026-06-10 07:30:00"}, "x") is None  # no activityId


def test_map_metric_returns_none_without_calendar_date():
    from app.services.garmin_sync import map_metric
    assert map_metric({"sleepScore": 80}, "x") is None
```

- [ ] **Step 2: Run to verify it fails**

Run: `docker compose exec -T api pytest tests/test_garmin_sync.py -k map_ -v`
Expected: FAIL (ImportError — `map_activity` not defined).

- [ ] **Step 3: Implement the mappers** — in `app/services/garmin_sync.py`, add these module-level functions after the `SyncReport` dataclass (before `class GarminSyncService`):

```python
def map_activity(act: dict, athlete_id: str) -> CompletedWorkout | None:
    """Map one Garmin activity dict to an unsaved CompletedWorkout.

    Returns None (skip) on malformed input — mirrors the per-activity-skip
    hardening used on the Strava path. Caller is responsible for dedup + add.
    """
    gid = act.get("activityId")
    if gid is None:
        return None
    started = act.get("startTimeLocal") or act.get("startTimeGMT")
    if not started:
        return None
    activity_type = act.get("activityType", {}).get("typeKey", "other")
    try:
        activity_date = date.fromisoformat(started[:10])
        started_at = datetime.fromisoformat(started)
    except ValueError:
        return None
    return CompletedWorkout(
        athlete_id=athlete_id,
        garmin_activity_id=gid,
        activity_date=activity_date,
        started_at=started_at,
        activity_type=activity_type,
        family=family_for_garmin_activity_type(activity_type),
        duration_s=int(act.get("duration", 0)),
        distance_m=Decimal(str(act["distance"])) if act.get("distance") else None,
        avg_hr=act.get("averageHR"),
        max_hr=act.get("maxHR"),
        avg_pace_s_per_km=None,
        elevation_gain_m=(
            Decimal(str(act["elevationGain"])) if act.get("elevationGain") else None
        ),
        calories=act.get("calories"),
        source="garmin",
        raw_summary_json=act,
    )


def map_metric(day: dict, athlete_id: str) -> DailyMetric | None:
    """Map one Garmin daily-stats dict to an unsaved DailyMetric, or None."""
    cal_date_str = day.get("calendarDate")
    if not cal_date_str:
        return None
    return DailyMetric(
        athlete_id=athlete_id,
        metric_date=date.fromisoformat(cal_date_str),
        sleep_score=day.get("sleepScore"),
        sleep_duration_s=day.get("sleepDurationSeconds"),
        hrv_overnight_ms=(Decimal(str(day["hrvOvernight"])) if day.get("hrvOvernight") else None),
        resting_hr=day.get("restingHeartRate"),
        body_battery_high=day.get("bodyBatteryHighestValue"),
        body_battery_low=day.get("bodyBatteryLowestValue"),
        training_readiness=day.get("trainingReadiness"),
        training_status=day.get("trainingStatus"),
        raw_json=day,
    )
```

- [ ] **Step 4: Rewire the existing methods to call the mappers** — in `sync_activities`, replace the per-activity construction loop (currently `garmin_sync.py:166-193`) with:

```python
        new_workouts: list[CompletedWorkout] = []
        for act in activities:
            gid = act["activityId"]
            if gid in existing_ids:
                continue
            workout = map_activity(act, self.athlete_id)
            if workout is None:
                continue
            self.db.add(workout)
            new_workouts.append(workout)
```

In `sync_daily_metrics`, replace the per-day construction loop (currently `:235-259`) with:

```python
        new_metrics: list[DailyMetric] = []
        for day in stats:
            metric = map_metric(day, self.athlete_id)
            if metric is None or metric.metric_date in existing_dates:
                continue
            self.db.add(metric)
            new_metrics.append(metric)
```

- [ ] **Step 5: Run the full garmin_sync suite to verify no regression**

Run: `docker compose exec -T api pytest tests/test_garmin_sync.py -v`
Expected: PASS (existing tests + the 3 new mapper tests).

- [ ] **Step 6: Commit**

```bash
git add app/services/garmin_sync.py tests/test_garmin_sync.py
git commit -m "refactor(garmin): extract pure map_activity/map_metric (no behavior change)"
```

---

### Task 4: Ingest schemas + token dependency

**Files:**
- Modify: `app/schemas/garmin.py`
- Modify: `app/deps.py`

**Interfaces:**
- Produces:
  - `GarminIngestRequest{ activities: list[dict], metrics: list[dict] }`
  - `GarminIngestResponse{ synced_activities: int, synced_metrics: int, skipped: int }`
  - `GarminPollOut{ sync_requested: bool }`
  - dependency `require_ingest_token()` → 503 unconfigured / 401 bad token
  - dependency `get_ingest_athlete(db) -> Athlete` → 503 unconfigured / 400 unknown email

- [ ] **Step 1: Add schemas** — append to `app/schemas/garmin.py`:

```python
class GarminIngestRequest(BaseModel):
    activities: list[dict] = []
    metrics: list[dict] = []


class GarminIngestResponse(BaseModel):
    synced_activities: int
    synced_metrics: int
    skipped: int


class GarminPollOut(BaseModel):
    sync_requested: bool
```

- [ ] **Step 2: Add dependencies** — append to `app/deps.py` (imports first, hoisted to top: add `import hmac`, `from fastapi import Header`, `from app.config import settings`):

```python
async def require_ingest_token(
    x_ingest_token: str | None = Header(default=None),
) -> None:
    if not settings.garmin_ingest_token:
        raise HTTPException(status_code=503, detail="Garmin ingest is not configured")
    if x_ingest_token is None or not hmac.compare_digest(
        x_ingest_token, settings.garmin_ingest_token
    ):
        raise HTTPException(status_code=401, detail="Invalid ingest token")


async def get_ingest_athlete(db: AsyncSession = Depends(get_db)) -> Athlete:
    email = settings.garmin_ingest_athlete_email
    if not email:
        raise HTTPException(status_code=503, detail="Garmin ingest athlete not configured")
    athlete = (
        await db.execute(select(Athlete).where(Athlete.email == email))
    ).scalar_one_or_none()
    if athlete is None:
        raise HTTPException(status_code=400, detail="Configured ingest athlete not found")
    return athlete
```

- [ ] **Step 3: Verify import sanity** (no route yet — just that the app imports clean)

Run: `docker compose exec -T api python -c "import app.deps, app.schemas.garmin; print('ok')"`
Expected: prints `ok`.

- [ ] **Step 4: Commit**

```bash
git add app/schemas/garmin.py app/deps.py
git commit -m "feat(garmin): ingest schemas + ingest-token/athlete deps"
```

---

### Task 5: `POST /garmin/ingest`

**Files:**
- Modify: `app/routes/garmin.py`
- Test: `tests/test_garmin_ingest.py` (create)

**Interfaces:**
- Consumes: `map_activity`, `map_metric` (Task 3); `require_ingest_token`, `get_ingest_athlete` (Task 4); schemas (Task 4).
- Produces: `POST /garmin/ingest` returning `GarminIngestResponse`.

- [ ] **Step 1: Write failing tests** — create `tests/test_garmin_ingest.py`. Uses the existing `client` + `athlete` fixtures from `tests/conftest.py` (the `athlete` fixture's email is `test@marathon.dev`; `auth_headers` authenticates as that same athlete). `ingest_configured` depends on `athlete` so the configured email resolves to a real row.

```python
import pytest

from app.config import settings

ATHLETE_EMAIL = "test@marathon.dev"  # matches the conftest `athlete` fixture

ACTIVITY = {
    "activityId": 9001,
    "startTimeLocal": "2026-06-10 07:30:00",
    "activityType": {"typeKey": "running"},
    "duration": 1800,
    "distance": 5000,
    "averageHR": 150,
}
METRIC = {"calendarDate": "2026-06-10", "sleepScore": 82, "restingHeartRate": 48}


@pytest.fixture
def ingest_configured(monkeypatch, athlete):
    monkeypatch.setattr(settings, "garmin_ingest_token", "test-ingest-token")
    monkeypatch.setattr(settings, "garmin_ingest_athlete_email", ATHLETE_EMAIL)


async def test_ingest_503_when_unconfigured(client, monkeypatch):
    monkeypatch.setattr(settings, "garmin_ingest_token", "")
    r = await client.post("/garmin/ingest", json={"activities": [], "metrics": []})
    assert r.status_code == 503


async def test_ingest_401_bad_token(client, ingest_configured):
    r = await client.post(
        "/garmin/ingest",
        json={"activities": [], "metrics": []},
        headers={"X-Ingest-Token": "wrong"},
    )
    assert r.status_code == 401


async def test_ingest_creates_and_dedups(client, ingest_configured):
    hdr = {"X-Ingest-Token": "test-ingest-token"}
    body = {"activities": [ACTIVITY], "metrics": [METRIC]}
    r1 = await client.post("/garmin/ingest", json=body, headers=hdr)
    assert r1.status_code == 200
    assert r1.json()["synced_activities"] == 1
    assert r1.json()["synced_metrics"] == 1
    r2 = await client.post("/garmin/ingest", json=body, headers=hdr)
    assert r2.json()["synced_activities"] == 0  # deduped
    assert r2.json()["synced_metrics"] == 0


async def test_ingest_skips_malformed_activity(client, ingest_configured):
    hdr = {"X-Ingest-Token": "test-ingest-token"}
    body = {"activities": [{"startTimeLocal": "2026-06-10 07:30:00"}], "metrics": []}
    r = await client.post("/garmin/ingest", json=body, headers=hdr)
    assert r.status_code == 200
    assert r.json()["synced_activities"] == 0
    assert r.json()["skipped"] == 1
```

- [ ] **Step 2: Run to verify it fails**

Run: `docker compose exec -T api pytest tests/test_garmin_ingest.py -v`
Expected: FAIL (404 — route not defined).

- [ ] **Step 3: Implement the route** — in `app/routes/garmin.py`, add imports at top:

```python
from sqlalchemy import select
from app.deps import get_db, require_ingest_token, get_ingest_athlete
from app.models.athlete import Athlete
from app.models.garmin import GarminAuthState
from app.models.metrics import DailyMetric
from app.models.workout import CompletedWorkout
from app.services.garmin_sync import map_activity, map_metric
from app.schemas.garmin import GarminIngestRequest, GarminIngestResponse
from datetime import UTC, datetime
```

Add the route:

```python
@router.post("/ingest", response_model=GarminIngestResponse)
async def ingest(
    body: GarminIngestRequest,
    _: None = Depends(require_ingest_token),
    athlete: Athlete = Depends(get_ingest_athlete),
    db: AsyncSession = Depends(get_db),
):
    aid = str(athlete.id)
    skipped = 0

    # Activities: dedup vs DB + within-batch
    incoming_ids = [a.get("activityId") for a in body.activities if a.get("activityId")]
    existing = set()
    if incoming_ids:
        rows = await db.execute(
            select(CompletedWorkout.garmin_activity_id).where(
                CompletedWorkout.garmin_activity_id.in_(incoming_ids)
            )
        )
        existing = {r[0] for r in rows.all()}
    seen: set[int] = set()
    synced_activities = 0
    for act in body.activities:
        w = map_activity(act, aid)
        if w is None:
            skipped += 1
            continue
        if w.garmin_activity_id in existing or w.garmin_activity_id in seen:
            continue
        seen.add(w.garmin_activity_id)
        db.add(w)
        synced_activities += 1

    # Metrics: dedup by (athlete, date)
    synced_metrics = 0
    if body.metrics:
        rows = await db.execute(
            select(DailyMetric.metric_date).where(DailyMetric.athlete_id == athlete.id)
        )
        existing_dates = {r[0] for r in rows.all()}
        seen_dates = set()
        for day in body.metrics:
            m = map_metric(day, aid)
            if m is None:
                skipped += 1
                continue
            if m.metric_date in existing_dates or m.metric_date in seen_dates:
                continue
            seen_dates.add(m.metric_date)
            db.add(m)
            synced_metrics += 1

    # Clear the on-demand flag + stamp last sync
    state = (
        await db.execute(
            select(GarminAuthState).where(GarminAuthState.athlete_id == athlete.id)
        )
    ).scalar_one_or_none()
    if state is not None:
        state.last_successful_sync = datetime.now(UTC)
        state.sync_requested_at = None

    await db.commit()
    return GarminIngestResponse(
        synced_activities=synced_activities,
        synced_metrics=synced_metrics,
        skipped=skipped,
    )
```

- [ ] **Step 4: Run to verify pass**

Run: `docker compose exec -T api pytest tests/test_garmin_ingest.py -v`
Expected: PASS (4 tests).

- [ ] **Step 5: Commit**

```bash
git add app/routes/garmin.py tests/test_garmin_ingest.py
git commit -m "feat(garmin): POST /garmin/ingest (token-gated, dedup, per-item skip)"
```

---

### Task 6: `GET /garmin/poll` + `POST /garmin/request-sync`

**Files:**
- Modify: `app/routes/garmin.py`
- Test: `tests/test_garmin_ingest.py`

**Interfaces:**
- Consumes: `require_ingest_token`, `get_ingest_athlete`, `get_current_athlete`, `GarminPollOut`.
- Produces: `GET /garmin/poll` (token auth) → `GarminPollOut`; `POST /garmin/request-sync` (athlete JWT) → `{ok: true}`.

- [ ] **Step 1: Write failing test** — append to `tests/test_garmin_ingest.py`:

```python
async def test_request_sync_sets_flag_and_poll_reflects_it(
    client, auth_headers, ingest_configured
):
    hdr = {"X-Ingest-Token": "test-ingest-token"}
    # initially not requested
    r0 = await client.get("/garmin/poll", headers=hdr)
    assert r0.status_code == 200 and r0.json()["sync_requested"] is False
    # PWA requests a sync (athlete JWT)
    rr = await client.post("/garmin/request-sync", headers=auth_headers)
    assert rr.status_code == 200
    # poll now true
    r1 = await client.get("/garmin/poll", headers=hdr)
    assert r1.json()["sync_requested"] is True
    # ingest clears it
    await client.post(
        "/garmin/ingest", json={"activities": [], "metrics": []}, headers=hdr
    )
    r2 = await client.get("/garmin/poll", headers=hdr)
    assert r2.json()["sync_requested"] is False
```

> NOTE: `auth_headers` is the existing fixture other route tests use for the seeded athlete's Bearer token. `request-sync` upserts a `GarminAuthState` row if none exists.

- [ ] **Step 2: Run to verify it fails**

Run: `docker compose exec -T api pytest tests/test_garmin_ingest.py::test_request_sync_sets_flag_and_poll_reflects_it -v`
Expected: FAIL (404).

- [ ] **Step 3: Implement** — in `app/routes/garmin.py` add `from app.schemas.garmin import GarminPollOut` and `from app.deps import get_current_athlete`, then the routes:

```python
@router.get("/poll", response_model=GarminPollOut)
async def poll(
    _: None = Depends(require_ingest_token),
    athlete: Athlete = Depends(get_ingest_athlete),
    db: AsyncSession = Depends(get_db),
):
    state = (
        await db.execute(
            select(GarminAuthState).where(GarminAuthState.athlete_id == athlete.id)
        )
    ).scalar_one_or_none()
    requested = state is not None and state.sync_requested_at is not None
    return GarminPollOut(sync_requested=requested)


@router.post("/request-sync")
async def request_sync(
    athlete: Athlete = Depends(get_current_athlete),
    db: AsyncSession = Depends(get_db),
):
    state = (
        await db.execute(
            select(GarminAuthState).where(GarminAuthState.athlete_id == athlete.id)
        )
    ).scalar_one_or_none()
    if state is None:
        state = GarminAuthState(
            athlete_id=athlete.id,
            token_dir_path="",  # residential agent owns tokens; server stores none
            needs_reauth=False,
        )
        db.add(state)
    state.sync_requested_at = datetime.now(UTC)
    await db.commit()
    return {"ok": True}
```

- [ ] **Step 4: Run full ingest suite to verify pass**

Run: `docker compose exec -T api pytest tests/test_garmin_ingest.py -v`
Expected: PASS (5 tests).

- [ ] **Step 5: Run the whole backend suite — no regressions**

Run: `docker compose exec -T api pytest -q`
Expected: all pass (prior 159 + new ingest/config/mapper tests).

- [ ] **Step 6: Commit**

```bash
git add app/routes/garmin.py tests/test_garmin_ingest.py
git commit -m "feat(garmin): poll + request-sync flag endpoints"
```

---

# Phase 2 — Mobile trigger

### Task 7: `useRequestSync` + repoint Settings "Sync now"

**Files:**
- Modify: `mobile/src/api/hooks/useGarmin.ts`
- Modify: `mobile/src/screens/SettingsScreen.tsx`

**Interfaces:**
- Consumes: `POST /garmin/request-sync`.
- Produces: `useRequestSync()` mutation hook.

- [ ] **Step 1: Add the hook** — append to `mobile/src/api/hooks/useGarmin.ts`:

```typescript
export function useRequestSync() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async () => {
      await api.post('/garmin/request-sync');
    },
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ['garmin'] });
    },
  });
}
```

- [ ] **Step 2: Repoint the button** — in `mobile/src/screens/SettingsScreen.tsx`:

Replace the import on line 7:
```typescript
import { useGarminReauth, useGarminStatus, useRequestSync } from '@/api/hooks/useGarmin';
```

Replace line 122:
```typescript
  const sync = useRequestSync();
```

Replace the `onSync` handler (lines 130-142):
```typescript
  const onSync = async () => {
    setSyncMsg(null);
    try {
      await sync.mutateAsync();
      setSyncMsg('Sync requested — your laptop agent will pick it up shortly.');
    } catch (e) {
      setSyncMsg(
        isAxiosError(e) ? (e.response?.data?.detail ?? 'Request failed.') : 'Request failed.',
      );
    }
  };
```

The button label at line 228 already reads `sync.isPending ? 'Syncing…' : 'Sync now'` — change `'Syncing…'` to `'Requesting…'`.

- [ ] **Step 3: Typecheck**

Run: `cd mobile && npx tsc --noEmit`
Expected: clean (no errors; `useManualSync` import removed so no unused-symbol error).

- [ ] **Step 4: Commit**

```bash
git add mobile/src/api/hooks/useGarmin.ts mobile/src/screens/SettingsScreen.tsx
git commit -m "feat(garmin): repoint Settings Sync-now to /garmin/request-sync flag"
```

---

# Phase 3 — Laptop agent

> The agent runs on the laptop (host Python 3.12+), not in Docker. Its tests cover the
> pure logic only; Garmin login + ingest are validated by the live smoke-test in Task 13.

### Task 8: Agent package scaffold + config

**Files:**
- Create: `scripts/garmin_agent/garmin_agent/__init__.py` (empty)
- Create: `scripts/garmin_agent/garmin_agent/config.py`
- Create: `scripts/garmin_agent/requirements.txt`
- Create: `scripts/garmin_agent/.env.example`
- Modify: root `.gitignore`

**Interfaces:**
- Produces: `AgentConfig` dataclass + `load_config() -> AgentConfig`; secret helpers
  `get_ingest_token()`, `get_garth_token()/set_garth_token()` via `keyring`.

- [ ] **Step 1: requirements.txt** (pinned — verify latest stable versions at implementation time and pin exactly):

```
garminconnect==0.2.25
httpx==0.27.2
keyring==25.4.1
python-dotenv==1.0.1
```

- [ ] **Step 2: `.env.example`**

```
# Non-secret config (real .env is gitignored). Secrets live in Windows Credential
# Manager via keyring (see README), NOT here.
MARATHON_API_URL=https://marathonapp-production-cc63.up.railway.app
GARMIN_EMAIL=you@example.com
LOOKBACK_DAYS=14
POLL_SECONDS=60
PERIODIC_HOURS=6
# Optional: comma-separated home IP prefixes that are always allowed (skips the
# datacenter/VPN guard for these). Leave blank to rely on the hosting/proxy check.
ALLOWED_IP_PREFIXES=
```

- [ ] **Step 3: `config.py`**

```python
from __future__ import annotations

import os
from dataclasses import dataclass

import keyring
from dotenv import load_dotenv

load_dotenv()

KEYRING_SERVICE = "marathon-garmin-agent"


@dataclass
class AgentConfig:
    api_url: str
    garmin_email: str
    lookback_days: int
    poll_seconds: int
    periodic_hours: int
    allowed_ip_prefixes: list[str]


def load_config() -> AgentConfig:
    return AgentConfig(
        api_url=os.environ["MARATHON_API_URL"].rstrip("/"),
        garmin_email=os.environ["GARMIN_EMAIL"],
        lookback_days=int(os.environ.get("LOOKBACK_DAYS", "14")),
        poll_seconds=int(os.environ.get("POLL_SECONDS", "60")),
        periodic_hours=int(os.environ.get("PERIODIC_HOURS", "6")),
        allowed_ip_prefixes=[
            p.strip() for p in os.environ.get("ALLOWED_IP_PREFIXES", "").split(",") if p.strip()
        ],
    )


def get_ingest_token() -> str:
    tok = keyring.get_password(KEYRING_SERVICE, "ingest_token")
    if not tok:
        raise RuntimeError("ingest_token not set — run `python -m garmin_agent.agent --set-secrets`")
    return tok


def set_ingest_token(value: str) -> None:
    keyring.set_password(KEYRING_SERVICE, "ingest_token", value)


def get_garth_token() -> str | None:
    return keyring.get_password(KEYRING_SERVICE, "garth_token")


def set_garth_token(value: str) -> None:
    keyring.set_password(KEYRING_SERVICE, "garth_token", value)
```

- [ ] **Step 4: gitignore agent secrets** — append to root `.gitignore`:

```
# Garmin residential agent — local secrets
scripts/garmin_agent/.env
scripts/garmin_agent/.venv/
scripts/garmin_agent/**/__pycache__/
```

- [ ] **Step 5: Commit**

```bash
git add scripts/garmin_agent/garmin_agent/__init__.py scripts/garmin_agent/garmin_agent/config.py scripts/garmin_agent/requirements.txt scripts/garmin_agent/.env.example .gitignore
git commit -m "feat(agent): garmin agent scaffold + keyring-backed config"
```

---

### Task 9: Egress IP guard (pure + testable)

**Files:**
- Create: `scripts/garmin_agent/garmin_agent/ipguard.py`
- Test: `scripts/garmin_agent/tests/test_ipguard.py`

**Interfaces:**
- Produces: `is_datacenter_ip(info: dict, allowed_prefixes: list[str]) -> bool`;
  `check_egress(allowed_prefixes) -> tuple[str, bool]` (returns `(ip, is_datacenter)`).

- [ ] **Step 1: Write failing test** — create `scripts/garmin_agent/tests/test_ipguard.py`:

```python
from garmin_agent.ipguard import is_datacenter_ip


def test_hosting_flag_is_datacenter():
    info = {"query": "203.0.113.5", "hosting": True, "proxy": False}
    assert is_datacenter_ip(info, []) is True


def test_proxy_flag_is_datacenter():
    assert is_datacenter_ip({"query": "203.0.113.5", "proxy": True}, []) is True


def test_residential_is_not_datacenter():
    info = {"query": "98.42.10.7", "hosting": False, "proxy": False}
    assert is_datacenter_ip(info, []) is False


def test_allowed_prefix_overrides():
    info = {"query": "98.42.10.7", "hosting": True}  # flagged but whitelisted
    assert is_datacenter_ip(info, ["98.42."]) is False
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd scripts/garmin_agent && python -m pytest tests/test_ipguard.py -v`
Expected: FAIL (ModuleNotFoundError).

- [ ] **Step 3: Implement** — create `scripts/garmin_agent/garmin_agent/ipguard.py`:

```python
from __future__ import annotations

import httpx

IPINFO_URL = "http://ip-api.com/json/?fields=status,query,org,isp,as,proxy,hosting"


def is_datacenter_ip(info: dict, allowed_prefixes: list[str]) -> bool:
    """True if the IP looks like a datacenter/VPN exit (Garmin would 429 it).

    An explicit allowed-prefix match always wins (your known home IP)."""
    ip = info.get("query", "")
    if any(ip.startswith(p) for p in allowed_prefixes):
        return False
    return bool(info.get("hosting") or info.get("proxy"))


def check_egress(allowed_prefixes: list[str]) -> tuple[str, bool]:
    """Fetch this machine's public IP + classification. Returns (ip, is_datacenter)."""
    resp = httpx.get(IPINFO_URL, timeout=10)
    resp.raise_for_status()
    info = resp.json()
    ip = info.get("query", "unknown")
    return ip, is_datacenter_ip(info, allowed_prefixes)
```

- [ ] **Step 4: Run to verify pass**

Run: `cd scripts/garmin_agent && python -m pytest tests/test_ipguard.py -v`
Expected: PASS (4 tests).

- [ ] **Step 5: Commit**

```bash
git add scripts/garmin_agent/garmin_agent/ipguard.py scripts/garmin_agent/tests/test_ipguard.py
git commit -m "feat(agent): egress IP datacenter/VPN guard"
```

---

### Task 10: Garmin fetch wrapper (token cache)

**Files:**
- Create: `scripts/garmin_agent/garmin_agent/garmin_fetch.py`

**Interfaces:**
- Produces: `login_interactive(email) -> str` (returns garth token blob, prompts password/MFA);
  `client_from_token(token) -> Garmin`; `fetch(client, lookback_days) -> tuple[list[dict], list[dict]]`.

- [ ] **Step 1: Implement** — create `scripts/garmin_agent/garmin_agent/garmin_fetch.py`:

```python
from __future__ import annotations

import logging
from datetime import date, timedelta
from getpass import getpass

from garminconnect import Garmin

logger = logging.getLogger(__name__)


def login_interactive(email: str) -> str:
    """One-time interactive login (handles MFA). Returns the garth token blob.

    The password is read at the prompt and never persisted."""
    password = getpass(f"Garmin password for {email}: ")
    client = Garmin(email=email, password=password)
    client.login()  # prompts for MFA on the console if the account requires it
    if getattr(client, "garth", None) is None:
        raise RuntimeError("Login did not establish a session (check creds / rate limit).")
    return client.garth.dumps()


def client_from_token(token: str) -> Garmin:
    client = Garmin()
    client.garth.loads(token)
    client.login()  # refreshes via cached token; no password
    if getattr(client, "garth", None) is None:
        raise RuntimeError("Cached token rejected — re-run with --login.")
    return client


def fetch(client: Garmin, lookback_days: int) -> tuple[list[dict], list[dict]]:
    start = (date.today() - timedelta(days=lookback_days)).isoformat()
    end = date.today().isoformat()
    activities = client.get_activities_by_date(start, end) or []
    metrics: list[dict] = []
    cursor = date.today() - timedelta(days=lookback_days)
    while cursor <= date.today():
        try:
            stats = client.get_daily_stats(cursor.isoformat())
            if stats:
                metrics.append(stats if isinstance(stats, dict) else stats[0])
        except Exception as exc:  # noqa: BLE001
            logger.warning("daily stats failed for %s: %s", cursor, exc)
        cursor += timedelta(days=1)
    return activities, metrics
```

- [ ] **Step 2: Import sanity check**

Run: `cd scripts/garmin_agent && python -c "import garmin_agent.garmin_fetch; print('ok')"`
Expected: prints `ok` (requires `pip install -r requirements.txt` in the venv first).

- [ ] **Step 3: Commit**

```bash
git add scripts/garmin_agent/garmin_agent/garmin_fetch.py
git commit -m "feat(agent): garmin fetch wrapper with garth token cache"
```

---

### Task 11: API client (poll + ingest) + payload builder

**Files:**
- Create: `scripts/garmin_agent/garmin_agent/api_client.py`
- Test: `scripts/garmin_agent/tests/test_payload.py`

**Interfaces:**
- Produces: `build_payload(activities, metrics) -> dict`; `post_ingest(cfg, token, payload) -> dict`;
  `poll_requested(cfg, token) -> bool`.

- [ ] **Step 1: Write failing test** — create `scripts/garmin_agent/tests/test_payload.py`:

```python
from garmin_agent.api_client import build_payload


def test_build_payload_shape():
    p = build_payload([{"activityId": 1}], [{"calendarDate": "2026-06-10"}])
    assert p == {"activities": [{"activityId": 1}], "metrics": [{"calendarDate": "2026-06-10"}]}


def test_build_payload_defaults_empty():
    assert build_payload(None, None) == {"activities": [], "metrics": []}
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd scripts/garmin_agent && python -m pytest tests/test_payload.py -v`
Expected: FAIL (ModuleNotFoundError).

- [ ] **Step 3: Implement** — create `scripts/garmin_agent/garmin_agent/api_client.py`:

```python
from __future__ import annotations

import httpx

from garmin_agent.config import AgentConfig


def build_payload(activities, metrics) -> dict:
    return {"activities": activities or [], "metrics": metrics or []}


def post_ingest(cfg: AgentConfig, token: str, payload: dict) -> dict:
    resp = httpx.post(
        f"{cfg.api_url}/garmin/ingest",
        json=payload,
        headers={"X-Ingest-Token": token},
        timeout=60,
    )
    resp.raise_for_status()
    return resp.json()


def poll_requested(cfg: AgentConfig, token: str) -> bool:
    resp = httpx.get(
        f"{cfg.api_url}/garmin/poll",
        headers={"X-Ingest-Token": token},
        timeout=15,
    )
    resp.raise_for_status()
    return bool(resp.json().get("sync_requested"))
```

- [ ] **Step 4: Run to verify pass**

Run: `cd scripts/garmin_agent && python -m pytest tests/test_payload.py -v`
Expected: PASS (2 tests).

- [ ] **Step 5: Commit**

```bash
git add scripts/garmin_agent/garmin_agent/api_client.py scripts/garmin_agent/tests/test_payload.py
git commit -m "feat(agent): api client (ingest POST + poll) + payload builder"
```

---

### Task 12: Agent orchestration (`--once` / `--watch` / `--login` / `--set-secrets`)

**Files:**
- Create: `scripts/garmin_agent/garmin_agent/agent.py`

**Interfaces:**
- Consumes: all prior agent modules.
- Produces: `python -m garmin_agent.agent [--once|--watch|--login|--set-secrets]`.

- [ ] **Step 1: Implement** — create `scripts/garmin_agent/garmin_agent/agent.py`:

```python
from __future__ import annotations

import argparse
import logging
import sys
import time
from getpass import getpass
from logging.handlers import RotatingFileHandler
from pathlib import Path

from garmin_agent import config as cfgmod
from garmin_agent.api_client import build_payload, poll_requested, post_ingest
from garmin_agent.garmin_fetch import client_from_token, fetch, login_interactive
from garmin_agent.ipguard import check_egress

LOG_PATH = Path(__file__).resolve().parent.parent / "agent.log"
logger = logging.getLogger("garmin_agent")


def _setup_logging() -> None:
    logger.setLevel(logging.INFO)
    fmt = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
    fh = RotatingFileHandler(LOG_PATH, maxBytes=1_000_000, backupCount=3)
    fh.setFormatter(fmt)
    sh = logging.StreamHandler()
    sh.setFormatter(fmt)
    logger.addHandler(fh)
    logger.addHandler(sh)


def run_sync(cfg: cfgmod.AgentConfig) -> None:
    ip, is_dc = check_egress(cfg.allowed_ip_prefixes)
    if is_dc:
        logger.error(
            "ABORT: egress IP %s looks like a datacenter/VPN exit. Split-tunnel this "
            "python.exe off NordVPN before Garmin will accept it.", ip
        )
        return
    logger.info("egress IP %s OK (residential)", ip)
    token_blob = cfgmod.get_garth_token()
    if token_blob is None:
        logger.error("No cached Garmin token — run `--login` once interactively.")
        return
    client = client_from_token(token_blob)
    activities, metrics = fetch(client, cfg.lookback_days)
    result = post_ingest(cfg, cfgmod.get_ingest_token(), build_payload(activities, metrics))
    logger.info(
        "ingest ok: +%s activities, +%s metrics, %s skipped",
        result["synced_activities"], result["synced_metrics"], result["skipped"],
    )


def watch(cfg: cfgmod.AgentConfig) -> None:
    logger.info("watch mode: startup catch-up sync")
    _safe(run_sync, cfg)
    last_periodic = time.monotonic()
    token = cfgmod.get_ingest_token()
    while True:
        time.sleep(cfg.poll_seconds)
        try:
            if poll_requested(cfg, token):
                logger.info("on-demand sync requested")
                _safe(run_sync, cfg)
        except Exception as exc:  # noqa: BLE001
            logger.warning("poll failed: %s", exc)
        if time.monotonic() - last_periodic >= cfg.periodic_hours * 3600:
            logger.info("periodic sync")
            _safe(run_sync, cfg)
            last_periodic = time.monotonic()


def _safe(fn, cfg) -> None:
    try:
        fn(cfg)
    except Exception:  # noqa: BLE001
        logger.exception("sync run failed")


def main() -> None:
    _setup_logging()
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--once", action="store_true", help="single sync then exit")
    g.add_argument("--watch", action="store_true", help="poll loop + periodic sync")
    g.add_argument("--login", action="store_true", help="interactive Garmin login (mints token)")
    g.add_argument("--set-secrets", action="store_true", help="store ingest token in keyring")
    args = ap.parse_args()
    cfg = cfgmod.load_config()

    if args.login:
        cfgmod.set_garth_token(login_interactive(cfg.garmin_email))
        logger.info("Garmin token cached. You can now run --once / --watch.")
    elif args.set_secrets:
        cfgmod.set_ingest_token(getpass("Ingest token: "))
        logger.info("Ingest token stored in Windows Credential Manager.")
    elif args.once:
        run_sync(cfg)
    elif args.watch:
        watch(cfg)
    else:
        ap.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Help-text smoke check**

Run: `cd scripts/garmin_agent && python -m garmin_agent.agent --help`
Expected: prints usage with `--once/--watch/--login/--set-secrets`.

- [ ] **Step 3: Run the agent's pure-logic tests**

Run: `cd scripts/garmin_agent && python -m pytest tests/ -v`
Expected: PASS (ipguard + payload tests).

- [ ] **Step 4: Commit**

```bash
git add scripts/garmin_agent/garmin_agent/agent.py
git commit -m "feat(agent): orchestration with once/watch/login/set-secrets modes"
```

---

### Task 13: Runbook (`README.md`) + live smoke-test

**Files:**
- Create: `scripts/garmin_agent/README.md`

This task's deliverable is the documented, executed setup. The README is the source of truth for steps 2-9 below; perform them on the laptop.

- [ ] **Step 1: Write `scripts/garmin_agent/README.md`** with these sections:

````markdown
# Garmin Residential Ingest Agent

Fetches Garmin activities + daily metrics from a residential IP and POSTs them to the
marathon backend's `/garmin/ingest`. Runs on your laptop (Windows Task Scheduler).

## Why this exists
Garmin's WAF 429s datacenter IPs, so server-side sync from Railway is impossible. This agent
does the Garmin fetch from your home IP; the server only stores what it receives.

## One-time backend setup (Railway)
1. Generate a token: `python -c "import secrets; print(secrets.token_urlsafe(32))"`
2. Railway → Variables: set `GARMIN_INGEST_TOKEN=<that token>` and
   `GARMIN_INGEST_ATHLETE_EMAIL=<your app login email>`. Redeploy.

## One-time laptop setup
1. `cd scripts/garmin_agent`
2. `python -m venv .venv` then `.venv\Scripts\activate`
3. `pip install -r requirements.txt`
4. `copy .env.example .env` and edit `MARATHON_API_URL`, `GARMIN_EMAIL`.
5. Store the ingest token (Windows Credential Manager): `python -m garmin_agent.agent --set-secrets`
   and paste the same token you set on Railway.
6. Interactive Garmin login (handles MFA, caches token): `python -m garmin_agent.agent --login`
7. **NordVPN split tunnel:** Settings → Split Tunneling → enable app-based →
   *Disable VPN for selected apps* → add `scripts\garmin_agent\.venv\Scripts\python.exe`.
8. Test a one-shot run: `python -m garmin_agent.agent --once`. Confirm `agent.log` shows
   `egress IP ... OK (residential)` and `ingest ok: +N activities`.

## Schedule it (Task Scheduler)
- Create Task → Trigger: **At log on**. Action: Start a program →
  `scripts\garmin_agent\.venv\Scripts\python.exe`, args `-m garmin_agent.agent --watch`,
  Start in `...\scripts\garmin_agent`.
- Settings: ✅ "Run task as soon as possible after a scheduled start is missed",
  ✅ "Run whether user is logged on or not". Conditions: optionally uncheck "only on AC power".

## Re-login
If `agent.log` says the cached token was rejected, re-run `--login`.

## Move to an always-on box later
Copy this folder to a Pi/mini-PC on your home WiFi, repeat laptop setup, point Task Scheduler
(or cron `--watch`) at it. No code change.
````

- [ ] **Step 2: Execute backend setup** — set `GARMIN_INGEST_TOKEN` + `GARMIN_INGEST_ATHLETE_EMAIL` on Railway; redeploy; confirm `/health` 200 and that `/garmin/poll` with the token returns `{"sync_requested": false}` (503 would mean the env var didn't take).

- [ ] **Step 3: Execute laptop setup** — venv, deps, `.env`, `--set-secrets`, `--login`, NordVPN split-tunnel (README steps 1-7).

- [ ] **Step 4: Live smoke-test** — `python -m garmin_agent.agent --once`; verify `agent.log` shows residential IP + a real ingest count; spot-check a recent run appears in the app (Week/Today screen).

- [ ] **Step 5: On-demand smoke-test** — start `--watch`; tap **Sync now** in the PWA Settings; within ~60s confirm `agent.log` logs "on-demand sync requested" and the flag clears.

- [ ] **Step 6: Schedule** — register the Task Scheduler logon task (README "Schedule it"). Reboot, confirm the watch process starts and logs a catch-up sync.

- [ ] **Step 7: Commit**

```bash
git add scripts/garmin_agent/README.md
git commit -m "docs(agent): setup + scheduling + smoke-test runbook"
```

---

## Self-Review Notes

- **Spec coverage:** config+fail-closed (T1) · migration/`sync_requested_at` (T2) · pure mappers (T3) · ingest endpoint w/ dedup+skip+token (T4-5) · poll+request-sync (T6) · PWA button (T7) · agent fetch/post/guard/token-cache/watch (T8-12) · security: keyring/no-password/pinned-deps/split-tunnel/egress-guard (T8-9,13) · runbook (T13). All spec sections mapped.
- **Leave-in-place:** `/admin/sync`, `/garmin/sync`, `/garmin/reauth` untouched — confirmed (no task modifies them).
- **Type consistency:** `map_activity`/`map_metric` signatures match across T3/T5; `GarminIngestResponse{synced_activities,synced_metrics,skipped}` consistent T4/T5; `sync_requested_at` consistent T2/T5/T6; `build_payload`/`poll_requested`/`post_ingest` consistent T11/T12.
- **Verified against codebase:** `tests/conftest.py` exposes `client`/`athlete`/`auth_headers` (athlete email `test@marathon.dev`); `Athlete.email` is the unique login field (`app/models/athlete.py:17`). Migration head `3ef08f92d555` confirmed. Only open item: pin exact current `garminconnect`/`httpx`/`keyring` versions in `requirements.txt` at implementation time.
```
