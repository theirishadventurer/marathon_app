# Strava Integration (Backend) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add Strava as the production activity source — OAuth connect, ingest-only activity sync, and explicit mark-complete linkage that resolves planned-vs-actual discrepancies by letting the athlete pick the matching run.

**Architecture:** A `strava` service package splits responsibilities: `client.py` is the single httpx network seam (mocked in tests via a `get_strava_client()` factory, mirroring `get_gemini_client`), `oauth.py` is pure token logic, `sync.py` ingests activities into `CompletedWorkout` with NO auto-reconcile. Tokens live in a new `strava_auth_state` table. Linkage happens through two new `/workouts/{id}/…` endpoints driven by the MARK DONE picker. The fuzzy `reconcile()` service is untouched.

**Tech Stack:** FastAPI, Pydantic v2, SQLAlchemy async, Alembic, httpx (already a dep). Tests run in the container: `docker compose exec -T api pytest`.

**Spec:** `docs/superpowers/specs/2026-06-16-strava-integration-design.md`

**Scope note:** This plan is backend-only. The mobile Settings card + MARK DONE picker UI is a separate follow-up plan written after this merges. Tests build schema via `Base.metadata.create_all` (see `tests/conftest.py`), so new models work in tests without the migration; the Alembic migration (Task 13) is for the real DB only.

---

## File Structure

- Create: `app/models/strava.py` — `StravaAuthState` ORM model
- Modify: `app/models/__init__.py` — register `StravaAuthState` so `create_all` sees it
- Modify: `app/models/workout.py` — new `CompletedWorkout` columns
- Modify: `app/config.py` — Strava config fields
- Modify: `app/lib/workout_family.py` — `family_for_strava_sport_type()`
- Create: `app/services/strava/__init__.py`
- Create: `app/services/strava/client.py` — httpx seam + `get_strava_client()`
- Create: `app/services/strava/oauth.py` — pure token helpers
- Create: `app/services/strava/sync.py` — `StravaSyncService` (ingest only)
- Create: `app/schemas/strava.py` — response/request schemas
- Create: `app/routes/strava.py` — connect/callback/sync/status/disconnect
- Modify: `app/main.py` — register the strava router
- Modify: `app/routes/workouts.py` — `strava-candidates` + `link-completed`
- Create: `alembic/versions/<rev>_strava_integration.py` — table + columns + backfill
- Tests: `tests/test_strava_oauth.py`, `tests/test_strava_sync.py`, `tests/test_strava_routes.py`, `tests/test_workout_linkage.py`, `tests/test_workout_family.py` (extend)

---

## Task 1: Strava config fields

**Files:**
- Modify: `app/config.py:16-19`
- Test: `tests/test_config.py`

- [ ] **Step 1: Write the failing test**

Add to `tests/test_config.py`:

```python
def test_strava_config_defaults_empty():
    from app.config import Settings

    s = Settings()
    assert s.strava_client_id == ""
    assert s.strava_client_secret == ""
    assert s.strava_redirect_uri == ""
```

- [ ] **Step 2: Run test to verify it fails**

Run: `docker compose exec -T api pytest tests/test_config.py::test_strava_config_defaults_empty -v`
Expected: FAIL — `AttributeError: 'Settings' object has no attribute 'strava_client_id'`

- [ ] **Step 3: Add the fields**

In `app/config.py`, after the `gemini_model` line (`app/config.py:18`), add:

```python
    strava_client_id: str = ""
    strava_client_secret: str = ""
    strava_redirect_uri: str = ""
```

- [ ] **Step 4: Run test to verify it passes**

Run: `docker compose exec -T api pytest tests/test_config.py::test_strava_config_defaults_empty -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add app/config.py tests/test_config.py
git commit -m "feat(strava): add STRAVA_CLIENT_ID/SECRET/REDIRECT_URI config fields"
```

---

## Task 2: `family_for_strava_sport_type` mapper

**Files:**
- Modify: `app/lib/workout_family.py`
- Test: `tests/test_workout_family.py` (create if absent)

- [ ] **Step 1: Write the failing test**

Create/append `tests/test_workout_family.py`:

```python
from app.lib.workout_family import family_for_strava_sport_type
from app.models.workout import WorkoutFamily


def test_strava_run_types_map_to_running():
    for t in ["Run", "TrailRun", "VirtualRun", "Treadmill"]:
        assert family_for_strava_sport_type(t) == WorkoutFamily.running


def test_strava_strength_maps_to_strength():
    assert family_for_strava_sport_type("WeightTraining") == WorkoutFamily.strength
    assert family_for_strava_sport_type("Workout") == WorkoutFamily.strength


def test_strava_unknown_maps_to_other():
    assert family_for_strava_sport_type("Ride") == WorkoutFamily.other
    assert family_for_strava_sport_type("") == WorkoutFamily.other
```

- [ ] **Step 2: Run test to verify it fails**

Run: `docker compose exec -T api pytest tests/test_workout_family.py -v`
Expected: FAIL — `ImportError: cannot import name 'family_for_strava_sport_type'`

- [ ] **Step 3: Implement the mapper**

Append to `app/lib/workout_family.py`:

```python
_STRAVA_RUNNING_TYPES = {
    "run",
    "trailrun",
    "virtualrun",
    "treadmill",
}

_STRAVA_STRENGTH_TYPES = {"weighttraining", "workout", "crossfit"}


def family_for_strava_sport_type(sport_type: str) -> WorkoutFamily:
    normalized = sport_type.lower().strip()
    if normalized in _STRAVA_RUNNING_TYPES:
        return WorkoutFamily.running
    if normalized in _STRAVA_STRENGTH_TYPES:
        return WorkoutFamily.strength
    return WorkoutFamily.other
```

- [ ] **Step 4: Run test to verify it passes**

Run: `docker compose exec -T api pytest tests/test_workout_family.py -v`
Expected: PASS (all 3)

- [ ] **Step 5: Commit**

```bash
git add app/lib/workout_family.py tests/test_workout_family.py
git commit -m "feat(strava): map Strava sport_type -> WorkoutFamily"
```

---

## Task 3: `CompletedWorkout` new columns

**Files:**
- Modify: `app/models/workout.py:120-123`
- Test: `tests/test_strava_sync.py` (create)

- [ ] **Step 1: Write the failing test**

Create `tests/test_strava_sync.py`:

```python
import uuid
from datetime import date, datetime
from decimal import Decimal

from app.models.workout import CompletedWorkout, WorkoutFamily


async def test_completed_workout_accepts_strava_columns(db):
    athlete_id = uuid.uuid4()
    cw = CompletedWorkout(
        athlete_id=athlete_id,
        strava_activity_id=123456789,
        source="strava",
        activity_date=date(2026, 6, 15),
        started_at=datetime(2026, 6, 15, 7, 0, 0),
        activity_type="Run",
        family=WorkoutFamily.running,
        duration_s=1800,
        distance_m=Decimal("5000.00"),
        avg_cadence=Decimal("172.0"),
        avg_watts=Decimal("260.0"),
        relative_effort=42,
        raw_summary_json={"id": 123456789},
    )
    db.add(cw)
    await db.flush()
    assert cw.strava_activity_id == 123456789
    assert cw.source == "strava"
    assert cw.relative_effort == 42
```

Note: this test references an `athlete_id` not present in `athletes`; `db.flush()` (not commit) does not enforce the FK in SQLite-less Postgres until commit, but to be safe create the athlete first if your DB enforces FKs on flush. Use the `athlete` fixture instead:

```python
async def test_completed_workout_accepts_strava_columns(db, athlete):
    cw = CompletedWorkout(
        athlete_id=athlete.id,
        strava_activity_id=123456789,
        source="strava",
        activity_date=date(2026, 6, 15),
        started_at=datetime(2026, 6, 15, 7, 0, 0),
        activity_type="Run",
        family=WorkoutFamily.running,
        duration_s=1800,
        distance_m=Decimal("5000.00"),
        avg_cadence=Decimal("172.0"),
        avg_watts=Decimal("260.0"),
        relative_effort=42,
        raw_summary_json={"id": 123456789},
    )
    db.add(cw)
    await db.flush()
    assert cw.source == "strava"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `docker compose exec -T api pytest tests/test_strava_sync.py::test_completed_workout_accepts_strava_columns -v`
Expected: FAIL — `TypeError: 'strava_activity_id' is an invalid keyword argument for CompletedWorkout`

- [ ] **Step 3: Add the columns**

In `app/models/workout.py`, inside `CompletedWorkout` after `calories` (`app/models/workout.py:120`), add:

```python
    strava_activity_id: Mapped[int | None] = mapped_column(BigInteger, unique=True, nullable=True)
    source: Mapped[str] = mapped_column(Text, nullable=False, server_default="manual")
    avg_cadence: Mapped[Decimal | None] = mapped_column(Numeric(5, 1), nullable=True)
    avg_watts: Mapped[Decimal | None] = mapped_column(Numeric(6, 1), nullable=True)
    relative_effort: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
```

(`BigInteger`, `Numeric`, `SmallInteger`, `Text` are already imported in this file.)

- [ ] **Step 4: Run test to verify it passes**

Run: `docker compose exec -T api pytest tests/test_strava_sync.py::test_completed_workout_accepts_strava_columns -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add app/models/workout.py tests/test_strava_sync.py
git commit -m "feat(strava): add strava_activity_id/source/cadence/watts/relative_effort to CompletedWorkout"
```

---

## Task 4: `StravaAuthState` model

**Files:**
- Create: `app/models/strava.py`
- Modify: `app/models/__init__.py`
- Test: `tests/test_strava_oauth.py` (create)

- [ ] **Step 1: Write the failing test**

Create `tests/test_strava_oauth.py`:

```python
from datetime import UTC, datetime

from sqlalchemy import select

from app.models.strava import StravaAuthState


async def test_strava_auth_state_persists(db, athlete):
    state = StravaAuthState(
        athlete_id=athlete.id,
        access_token="acc",
        refresh_token="ref",
        expires_at=datetime(2026, 6, 16, 12, 0, 0, tzinfo=UTC),
        athlete_strava_id=987654,
        scope="activity:read_all",
    )
    db.add(state)
    await db.commit()

    got = (
        await db.execute(select(StravaAuthState).where(StravaAuthState.athlete_id == athlete.id))
    ).scalar_one()
    assert got.access_token == "acc"
    assert got.athlete_strava_id == 987654
    assert got.last_successful_sync is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `docker compose exec -T api pytest tests/test_strava_oauth.py::test_strava_auth_state_persists -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.models.strava'`

- [ ] **Step 3: Create the model**

Create `app/models/strava.py`:

```python
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import BigInteger, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class StravaAuthState(Base):
    __tablename__ = "strava_auth_state"

    athlete_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("athletes.id", ondelete="CASCADE"),
        primary_key=True,
    )
    access_token: Mapped[str] = mapped_column(Text, nullable=False)
    refresh_token: Mapped[str] = mapped_column(Text, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(nullable=False)
    athlete_strava_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    scope: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_successful_sync: Mapped[datetime | None] = mapped_column(nullable=True)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_error_at: Mapped[datetime | None] = mapped_column(nullable=True)
```

- [ ] **Step 4: Register the model**

In `app/models/__init__.py`, add an import so `Base.metadata.create_all` discovers the table. Add alongside the other model imports:

```python
from app.models.strava import StravaAuthState  # noqa: F401
```

(If `__init__.py` maintains an `__all__`, append `"StravaAuthState"` to it.)

- [ ] **Step 5: Run test to verify it passes**

Run: `docker compose exec -T api pytest tests/test_strava_oauth.py::test_strava_auth_state_persists -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add app/models/strava.py app/models/__init__.py tests/test_strava_oauth.py
git commit -m "feat(strava): StravaAuthState model (DB-stored tokens)"
```

---

## Task 5: OAuth pure helpers — authorize URL + token parsing + refresh check

**Files:**
- Create: `app/services/strava/__init__.py` (empty)
- Create: `app/services/strava/oauth.py`
- Test: `tests/test_strava_oauth.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/test_strava_oauth.py`:

```python
from datetime import UTC, datetime, timedelta

from app.services.strava import oauth


def test_build_authorize_url():
    url = oauth.build_authorize_url(client_id="42", redirect_uri="https://x.app/strava/callback")
    assert url.startswith("https://www.strava.com/oauth/authorize?")
    assert "client_id=42" in url
    assert "scope=activity%3Aread_all" in url or "scope=activity:read_all" in url
    assert "response_type=code" in url
    assert "redirect_uri=https%3A%2F%2Fx.app%2Fstrava%2Fcallback" in url


def test_tokens_from_response():
    resp = {
        "access_token": "a",
        "refresh_token": "r",
        "expires_at": 1781000000,
        "scope": "activity:read_all",
        "athlete": {"id": 555},
    }
    parsed = oauth.tokens_from_response(resp)
    assert parsed.access_token == "a"
    assert parsed.refresh_token == "r"
    assert parsed.athlete_strava_id == 555
    assert parsed.expires_at == datetime.fromtimestamp(1781000000, tz=UTC)


def test_needs_refresh():
    now = datetime(2026, 6, 16, 12, 0, 0, tzinfo=UTC)
    assert oauth.needs_refresh(now + timedelta(minutes=2), now) is True  # within 5-min buffer
    assert oauth.needs_refresh(now + timedelta(minutes=30), now) is False
    assert oauth.needs_refresh(now - timedelta(minutes=1), now) is True  # already expired
```

- [ ] **Step 2: Run test to verify it fails**

Run: `docker compose exec -T api pytest tests/test_strava_oauth.py -k "authorize_url or tokens_from_response or needs_refresh" -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.services.strava'`

- [ ] **Step 3: Implement**

Create empty `app/services/strava/__init__.py`. Create `app/services/strava/oauth.py`:

```python
from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any
from urllib.parse import urlencode

AUTHORIZE_URL = "https://www.strava.com/oauth/authorize"
SCOPE = "activity:read_all"
REFRESH_BUFFER = timedelta(minutes=5)


@dataclass
class StravaTokens:
    access_token: str
    refresh_token: str
    expires_at: datetime
    scope: str | None = None
    athlete_strava_id: int | None = None


def build_authorize_url(*, client_id: str, redirect_uri: str) -> str:
    params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": SCOPE,
        "approval_prompt": "auto",
    }
    return f"{AUTHORIZE_URL}?{urlencode(params)}"


def tokens_from_response(resp: dict[str, Any]) -> StravaTokens:
    athlete = resp.get("athlete") or {}
    return StravaTokens(
        access_token=resp["access_token"],
        refresh_token=resp["refresh_token"],
        expires_at=datetime.fromtimestamp(int(resp["expires_at"]), tz=UTC),
        scope=resp.get("scope"),
        athlete_strava_id=athlete.get("id"),
    )


def needs_refresh(expires_at: datetime, now: datetime) -> bool:
    return expires_at - now <= REFRESH_BUFFER
```

- [ ] **Step 4: Run test to verify it passes**

Run: `docker compose exec -T api pytest tests/test_strava_oauth.py -k "authorize_url or tokens_from_response or needs_refresh" -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add app/services/strava/__init__.py app/services/strava/oauth.py tests/test_strava_oauth.py
git commit -m "feat(strava): oauth pure helpers (authorize url, token parse, refresh check)"
```

---

## Task 6: Strava HTTP client seam

**Files:**
- Create: `app/services/strava/client.py`
- Test: `tests/test_strava_sync.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/test_strava_sync.py`:

```python
from app.services.strava.client import StravaClient, get_strava_client


def test_get_strava_client_returns_client():
    c = get_strava_client()
    assert isinstance(c, StravaClient)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `docker compose exec -T api pytest tests/test_strava_sync.py::test_get_strava_client_returns_client -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.services.strava.client'`

- [ ] **Step 3: Implement**

Create `app/services/strava/client.py`:

```python
from __future__ import annotations

from typing import Any

import httpx

TOKEN_URL = "https://www.strava.com/oauth/token"
DEAUTH_URL = "https://www.strava.com/oauth/deauthorize"
API_BASE = "https://www.strava.com/api/v3"


class StravaClient:
    """Thin async wrapper around Strava's REST API. The single network seam;
    tests patch get_strava_client() to return a fake (mirrors get_gemini_client)."""

    async def exchange_code(self, *, client_id: str, client_secret: str, code: str) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=15) as http:
            r = await http.post(
                TOKEN_URL,
                data={
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "code": code,
                    "grant_type": "authorization_code",
                },
            )
            r.raise_for_status()
            return r.json()

    async def refresh_token(
        self, *, client_id: str, client_secret: str, refresh_token: str
    ) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=15) as http:
            r = await http.post(
                TOKEN_URL,
                data={
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "refresh_token": refresh_token,
                    "grant_type": "refresh_token",
                },
            )
            r.raise_for_status()
            return r.json()

    async def get_activities(
        self, *, access_token: str, after_epoch: int, page: int = 1, per_page: int = 100
    ) -> list[dict[str, Any]]:
        async with httpx.AsyncClient(timeout=30) as http:
            r = await http.get(
                f"{API_BASE}/athlete/activities",
                headers={"Authorization": f"Bearer {access_token}"},
                params={"after": after_epoch, "page": page, "per_page": per_page},
            )
            r.raise_for_status()
            return r.json()

    async def deauthorize(self, *, access_token: str) -> None:
        async with httpx.AsyncClient(timeout=15) as http:
            r = await http.post(
                DEAUTH_URL, headers={"Authorization": f"Bearer {access_token}"}
            )
            r.raise_for_status()


def get_strava_client() -> StravaClient:
    """Separated for test mocking (mirrors get_gemini_client / get_anthropic_client)."""
    return StravaClient()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `docker compose exec -T api pytest tests/test_strava_sync.py::test_get_strava_client_returns_client -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add app/services/strava/client.py tests/test_strava_sync.py
git commit -m "feat(strava): httpx client seam (exchange/refresh/activities/deauthorize)"
```

---

## Task 7: Activity → CompletedWorkout mapping

**Files:**
- Modify: `app/services/strava/sync.py` (create)
- Test: `tests/test_strava_sync.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/test_strava_sync.py`:

```python
import uuid

from app.services.strava.sync import map_activity
from app.models.workout import WorkoutFamily

SAMPLE = {
    "id": 111222333,
    "sport_type": "Run",
    "type": "Run",
    "distance": 5012.3,
    "moving_time": 1500,
    "elapsed_time": 1560,
    "total_elevation_gain": 42.0,
    "start_date_local": "2026-06-15T07:00:00Z",
    "average_speed": 3.34,
    "has_heartrate": True,
    "average_heartrate": 152.4,
    "max_heartrate": 171.0,
    "average_cadence": 86.0,
    "average_watts": 255.0,
    "suffer_score": 58,
    "calories": 410,
}


def test_map_activity_basic():
    athlete_id = uuid.uuid4()
    cw = map_activity(athlete_id, SAMPLE)
    assert cw.strava_activity_id == 111222333
    assert cw.source == "strava"
    assert cw.family == WorkoutFamily.running
    assert cw.duration_s == 1500
    assert float(cw.distance_m) == 5012.3
    assert cw.avg_hr == 152  # rounded
    assert cw.max_hr == 171
    assert cw.relative_effort == 58
    assert cw.activity_date.isoformat() == "2026-06-15"
    # pace = 1000 / average_speed
    assert cw.avg_pace_s_per_km == round(1000 / 3.34)


def test_map_activity_zero_speed_pace_none():
    athlete_id = uuid.uuid4()
    act = {**SAMPLE, "average_speed": 0, "has_heartrate": False}
    cw = map_activity(athlete_id, act)
    assert cw.avg_pace_s_per_km is None
    assert cw.avg_hr is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `docker compose exec -T api pytest tests/test_strava_sync.py -k map_activity -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.services.strava.sync'`

- [ ] **Step 3: Implement the mapper**

Create `app/services/strava/sync.py`:

```python
from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

from app.lib.workout_family import family_for_strava_sport_type
from app.models.workout import CompletedWorkout


def _parse_started_at(raw: str) -> datetime:
    # Strava ISO8601, may end in 'Z'
    return datetime.fromisoformat(raw.replace("Z", "+00:00"))


def map_activity(athlete_id: uuid.UUID, act: dict[str, Any]) -> CompletedWorkout:
    started_at = _parse_started_at(act["start_date_local"])
    sport = act.get("sport_type") or act.get("type") or "Run"

    avg_speed = act.get("average_speed") or 0
    avg_pace = round(1000 / avg_speed) if avg_speed and avg_speed > 0 else None

    has_hr = act.get("has_heartrate")
    avg_hr = round(act["average_heartrate"]) if has_hr and act.get("average_heartrate") else None
    max_hr = round(act["max_heartrate"]) if has_hr and act.get("max_heartrate") else None

    def _num(key: str) -> Decimal | None:
        v = act.get(key)
        return Decimal(str(v)) if v is not None else None

    return CompletedWorkout(
        athlete_id=athlete_id,
        strava_activity_id=int(act["id"]),
        source="strava",
        activity_date=started_at.date(),
        started_at=started_at,
        activity_type=str(sport),
        family=family_for_strava_sport_type(str(sport)),
        duration_s=int(act.get("moving_time", 0)),
        distance_m=_num("distance"),
        avg_hr=avg_hr,
        max_hr=max_hr,
        avg_pace_s_per_km=avg_pace,
        elevation_gain_m=_num("total_elevation_gain"),
        calories=int(act["calories"]) if act.get("calories") is not None else None,
        avg_cadence=_num("average_cadence"),
        avg_watts=_num("average_watts"),
        relative_effort=int(act["suffer_score"]) if act.get("suffer_score") is not None else None,
        raw_summary_json=act,
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `docker compose exec -T api pytest tests/test_strava_sync.py -k map_activity -v`
Expected: PASS (both)

- [ ] **Step 5: Commit**

```bash
git add app/services/strava/sync.py tests/test_strava_sync.py
git commit -m "feat(strava): map_activity -> CompletedWorkout (pace derivation, hr/cadence/watts/effort)"
```

---

## Task 8: `StravaSyncService.sync` — ingest + dedup (no reconcile)

**Files:**
- Modify: `app/services/strava/sync.py`
- Test: `tests/test_strava_sync.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/test_strava_sync.py`:

```python
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from sqlalchemy import func, select

from app.models.reconciliation import Reconciliation
from app.models.strava import StravaAuthState
from app.models.workout import CompletedWorkout
from app.services.strava import sync as sync_mod


async def _connect(db, athlete):
    db.add(
        StravaAuthState(
            athlete_id=athlete.id,
            access_token="acc",
            refresh_token="ref",
            expires_at=datetime.now(UTC) + timedelta(hours=5),
            athlete_strava_id=1,
            scope="activity:read_all",
        )
    )
    await db.commit()


async def test_sync_ingests_and_dedups_without_reconcile(db, athlete):
    await _connect(db, athlete)
    fake = MagicMock()
    fake.get_activities = AsyncMock(side_effect=[[SAMPLE], []])  # one page then empty

    with patch.object(sync_mod, "get_strava_client", return_value=fake):
        svc = sync_mod.StravaSyncService(db, athlete.id)
        report = await svc.sync()

    assert report.synced_activities == 1
    count = (
        await db.execute(
            select(func.count()).select_from(CompletedWorkout).where(
                CompletedWorkout.athlete_id == athlete.id
            )
        )
    ).scalar_one()
    assert count == 1
    # ingest-only: no reconciliation rows, nothing marked done
    recon_count = (
        await db.execute(select(func.count()).select_from(Reconciliation))
    ).scalar_one()
    assert recon_count == 0

    # second sync with the same activity dedups
    fake.get_activities = AsyncMock(side_effect=[[SAMPLE], []])
    with patch.object(sync_mod, "get_strava_client", return_value=fake):
        report2 = await sync_mod.StravaSyncService(db, athlete.id).sync()
    assert report2.synced_activities == 0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `docker compose exec -T api pytest tests/test_strava_sync.py::test_sync_ingests_and_dedups_without_reconcile -v`
Expected: FAIL — `AttributeError: module ... has no attribute 'StravaSyncService'`

- [ ] **Step 3: Implement the service**

Append to `app/services/strava/sync.py` (add imports at top first):

```python
# add to the existing top-of-file imports:
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.strava import StravaAuthState
from app.services.strava import oauth
from app.services.strava.client import get_strava_client
from app.config import settings
```

```python
@dataclass
class StravaSyncReport:
    synced_activities: int = 0
    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {"synced_activities": self.synced_activities, "errors": self.errors}


class StravaSyncService:
    def __init__(self, db: AsyncSession, athlete_id: uuid.UUID) -> None:
        self.db = db
        self.athlete_id = athlete_id

    async def _state(self) -> StravaAuthState | None:
        return (
            await self.db.execute(
                select(StravaAuthState).where(StravaAuthState.athlete_id == self.athlete_id)
            )
        ).scalar_one_or_none()

    async def _ensure_fresh(self, state: StravaAuthState, client) -> str:
        """Return a valid access token, refreshing inline if near expiry."""
        if oauth.needs_refresh(state.expires_at, datetime.now(UTC)):
            resp = await client.refresh_token(
                client_id=settings.strava_client_id,
                client_secret=settings.strava_client_secret,
                refresh_token=state.refresh_token,
            )
            tokens = oauth.tokens_from_response({**resp, "athlete": {"id": state.athlete_strava_id}})
            state.access_token = tokens.access_token
            state.refresh_token = tokens.refresh_token
            state.expires_at = tokens.expires_at
            await self.db.commit()
        return state.access_token

    async def sync(self, since: date | None = None) -> StravaSyncReport:
        report = StravaSyncReport()
        state = await self._state()
        if state is None:
            return report  # not connected

        client = get_strava_client()
        access = await self._ensure_fresh(state, client)

        after_dt = state.last_successful_sync or (
            datetime.combine(since, datetime.min.time(), tzinfo=UTC)
            if since
            else datetime.now(UTC) - timedelta(days=30)
        )
        after_epoch = int(after_dt.timestamp())

        # Paginate
        activities: list[dict] = []
        page = 1
        while True:
            batch = await client.get_activities(
                access_token=access, after_epoch=after_epoch, page=page, per_page=100
            )
            if not batch:
                break
            activities.extend(batch)
            if len(batch) < 100:
                break
            page += 1

        if not activities:
            state.last_successful_sync = datetime.now(UTC)
            await self.db.commit()
            return report

        ids = [int(a["id"]) for a in activities]
        existing = {
            row[0]
            for row in (
                await self.db.execute(
                    select(CompletedWorkout.strava_activity_id).where(
                        CompletedWorkout.strava_activity_id.in_(ids)
                    )
                )
            ).all()
        }

        for act in activities:
            if int(act["id"]) in existing:
                continue
            self.db.add(map_activity(self.athlete_id, act))
            report.synced_activities += 1

        state.last_successful_sync = datetime.now(UTC)
        await self.db.commit()
        return report
```

- [ ] **Step 4: Run test to verify it passes**

Run: `docker compose exec -T api pytest tests/test_strava_sync.py::test_sync_ingests_and_dedups_without_reconcile -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add app/services/strava/sync.py tests/test_strava_sync.py
git commit -m "feat(strava): StravaSyncService.sync — ingest-only with dedup + inline token refresh"
```

---

## Task 9: Strava schemas

**Files:**
- Create: `app/schemas/strava.py`
- Test: covered by route tests (Task 10–11)

- [ ] **Step 1: Create the schemas**

Create `app/schemas/strava.py`:

```python
from __future__ import annotations

import uuid
from datetime import date, datetime

from pydantic import BaseModel


class StravaConnectOut(BaseModel):
    authorize_url: str


class StravaStatusOut(BaseModel):
    connected: bool
    athlete_strava_id: int | None = None
    last_sync: datetime | None = None
    last_error: str | None = None
    last_error_at: datetime | None = None


class StravaSyncReportOut(BaseModel):
    synced_activities: int
    errors: list[str]


class CandidateOut(BaseModel):
    completed_id: uuid.UUID
    activity_date: date
    activity_type: str
    distance_mi: float | None
    duration_min: int
    avg_pace_str: str | None
    source: str


class LinkCompletedRequest(BaseModel):
    completed_id: uuid.UUID
```

- [ ] **Step 2: Commit**

```bash
git add app/schemas/strava.py
git commit -m "feat(strava): response/request schemas"
```

---

## Task 10: Strava routes — connect / status / disconnect + router registration

**Files:**
- Create: `app/routes/strava.py`
- Modify: `app/main.py:37` (add `from ...` import + `include_router`)
- Test: `tests/test_strava_routes.py` (create)

- [ ] **Step 1: Write the failing test**

Create `tests/test_strava_routes.py`:

```python
from datetime import UTC, datetime, timedelta

import pytest

from app.config import settings
from app.models.strava import StravaAuthState


@pytest.fixture(autouse=True)
def _strava_config(monkeypatch):
    monkeypatch.setattr(settings, "strava_client_id", "42")
    monkeypatch.setattr(settings, "strava_client_secret", "secret")
    monkeypatch.setattr(settings, "strava_redirect_uri", "https://x.app/strava/callback")


async def test_connect_returns_authorize_url(client, athlete, auth_headers):
    r = await client.get("/strava/connect", headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["authorize_url"].startswith("https://www.strava.com/oauth/authorize?")


async def test_connect_503_when_unconfigured(client, athlete, auth_headers, monkeypatch):
    monkeypatch.setattr(settings, "strava_client_id", "")
    r = await client.get("/strava/connect", headers=auth_headers)
    assert r.status_code == 503


async def test_status_not_connected(client, athlete, auth_headers):
    r = await client.get("/strava/status", headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["connected"] is False


async def test_disconnect_deletes_state(client, db, athlete, auth_headers):
    from unittest.mock import AsyncMock, MagicMock, patch

    import app.routes.strava as strava_routes

    db.add(
        StravaAuthState(
            athlete_id=athlete.id,
            access_token="acc",
            refresh_token="ref",
            expires_at=datetime.now(UTC) + timedelta(hours=5),
        )
    )
    await db.commit()

    fake = MagicMock()
    fake.deauthorize = AsyncMock(return_value=None)
    with patch.object(strava_routes, "get_strava_client", return_value=fake):
        r = await client.delete("/strava/disconnect", headers=auth_headers)
    assert r.status_code == 200

    r2 = await client.get("/strava/status", headers=auth_headers)
    assert r2.json()["connected"] is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `docker compose exec -T api pytest tests/test_strava_routes.py -v`
Expected: FAIL — 404s (router not registered) / import error

- [ ] **Step 3: Implement the routes**

Create `app/routes/strava.py`:

```python
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import RedirectResponse
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.deps import get_current_athlete, get_db
from app.models.athlete import Athlete
from app.models.strava import StravaAuthState
from app.schemas.strava import StravaConnectOut, StravaStatusOut, StravaSyncReportOut
from app.services.strava import oauth
from app.services.strava.client import get_strava_client
from app.services.strava.sync import StravaSyncService

router = APIRouter(prefix="/strava", tags=["strava"])


def _require_config() -> None:
    if not (settings.strava_client_id and settings.strava_client_secret and settings.strava_redirect_uri):
        raise HTTPException(status_code=503, detail="Strava is not configured")


@router.get("/connect", response_model=StravaConnectOut)
async def connect(athlete: Athlete = Depends(get_current_athlete)):
    _require_config()
    url = oauth.build_authorize_url(
        client_id=settings.strava_client_id, redirect_uri=settings.strava_redirect_uri
    )
    return StravaConnectOut(authorize_url=url)


@router.get("/callback")
async def callback(
    code: str,
    athlete: Athlete = Depends(get_current_athlete),
    db: AsyncSession = Depends(get_db),
):
    _require_config()
    client = get_strava_client()
    try:
        resp = await client.exchange_code(
            client_id=settings.strava_client_id,
            client_secret=settings.strava_client_secret,
            code=code,
        )
    except Exception as e:  # noqa: BLE001 — CORS-safe 502 per project gotcha
        raise HTTPException(status_code=502, detail=f"Strava token exchange failed: {e}") from e

    tokens = oauth.tokens_from_response(resp)
    state = (
        await db.execute(select(StravaAuthState).where(StravaAuthState.athlete_id == athlete.id))
    ).scalar_one_or_none()
    if state is None:
        state = StravaAuthState(athlete_id=athlete.id)
        db.add(state)
    state.access_token = tokens.access_token
    state.refresh_token = tokens.refresh_token
    state.expires_at = tokens.expires_at
    state.scope = tokens.scope
    state.athlete_strava_id = tokens.athlete_strava_id
    state.last_error = None
    state.last_error_at = None
    await db.commit()

    # Send the user back into the PWA.
    return RedirectResponse(url=settings.web_origin or "/")


@router.get("/status", response_model=StravaStatusOut)
async def status(
    athlete: Athlete = Depends(get_current_athlete),
    db: AsyncSession = Depends(get_db),
):
    state = (
        await db.execute(select(StravaAuthState).where(StravaAuthState.athlete_id == athlete.id))
    ).scalar_one_or_none()
    if state is None:
        return StravaStatusOut(connected=False)
    return StravaStatusOut(
        connected=True,
        athlete_strava_id=state.athlete_strava_id,
        last_sync=state.last_successful_sync,
        last_error=state.last_error,
        last_error_at=state.last_error_at,
    )


@router.post("/sync", response_model=StravaSyncReportOut)
async def sync(
    athlete: Athlete = Depends(get_current_athlete),
    db: AsyncSession = Depends(get_db),
):
    _require_config()
    try:
        report = await StravaSyncService(db, athlete.id).sync()
    except Exception as e:  # noqa: BLE001 — CORS-safe 502
        raise HTTPException(status_code=502, detail=f"Strava sync failed: {e}") from e
    return StravaSyncReportOut(**report.to_dict())


@router.delete("/disconnect")
async def disconnect(
    athlete: Athlete = Depends(get_current_athlete),
    db: AsyncSession = Depends(get_db),
):
    state = (
        await db.execute(select(StravaAuthState).where(StravaAuthState.athlete_id == athlete.id))
    ).scalar_one_or_none()
    if state is not None:
        client = get_strava_client()
        try:
            await client.deauthorize(access_token=state.access_token)
        except Exception:  # noqa: BLE001 — best-effort; still drop our row
            pass
        await db.execute(delete(StravaAuthState).where(StravaAuthState.athlete_id == athlete.id))
        await db.commit()
    return {"ok": True}
```

In `app/main.py`, mirror the existing router imports/registration (`app/main.py:37-42`):

```python
from app.routes.strava import router as strava_router
```
```python
app.include_router(strava_router)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `docker compose exec -T api pytest tests/test_strava_routes.py -v`
Expected: PASS (all 4)

- [ ] **Step 5: Commit**

```bash
git add app/routes/strava.py app/main.py tests/test_strava_routes.py
git commit -m "feat(strava): connect/callback/status/sync/disconnect routes (CORS-safe 502/503)"
```

---

## Task 11: Sync route + CORS-safe error test

**Files:**
- Test: `tests/test_strava_routes.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/test_strava_routes.py`:

```python
async def test_sync_upstream_failure_returns_502(client, db, athlete, auth_headers):
    from unittest.mock import AsyncMock, MagicMock, patch

    import app.services.strava.sync as sync_mod

    db.add(
        StravaAuthState(
            athlete_id=athlete.id,
            access_token="acc",
            refresh_token="ref",
            expires_at=datetime.now(UTC) + timedelta(hours=5),
        )
    )
    await db.commit()

    fake = MagicMock()
    fake.get_activities = AsyncMock(side_effect=RuntimeError("boom"))
    with patch.object(sync_mod, "get_strava_client", return_value=fake):
        r = await client.post("/strava/sync", headers=auth_headers)
    assert r.status_code == 502


async def test_sync_503_when_unconfigured(client, athlete, auth_headers, monkeypatch):
    monkeypatch.setattr(settings, "strava_client_secret", "")
    r = await client.post("/strava/sync", headers=auth_headers)
    assert r.status_code == 503
```

- [ ] **Step 2: Run test to verify it fails/passes**

Run: `docker compose exec -T api pytest tests/test_strava_routes.py -k "502 or 503" -v`
Expected: PASS (the route from Task 10 already converts errors to 502 and gates 503). If `test_sync_upstream_failure_returns_502` fails because the token is fresh and `_ensure_fresh` is skipped, that's intended — `get_activities` raises and the route catches it → 502.

- [ ] **Step 3: Commit**

```bash
git add tests/test_strava_routes.py
git commit -m "test(strava): sync returns CORS-safe 502 on upstream error, 503 unconfigured"
```

---

## Task 12: Linkage endpoints — candidates + link-completed

**Files:**
- Modify: `app/routes/workouts.py` (add two endpoints + imports)
- Test: `tests/test_workout_linkage.py` (create)

- [ ] **Step 1: Write the failing test**

Create `tests/test_workout_linkage.py`:

```python
import uuid
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

from sqlalchemy import select

from app.config import settings
from app.models.plan import Cycle, Plan
from app.models.reconciliation import Reconciliation
from app.models.strava import StravaAuthState
from app.models.workout import CompletedWorkout, PlannedWorkout, WorkoutFamily, WorkoutStatus


async def _first_planned(db):
    return (
        await db.execute(select(PlannedWorkout).where(PlannedWorkout.status == WorkoutStatus.planned).limit(1))
    ).scalar_one()


async def _athlete_id(db):
    from app.models.athlete import Athlete

    return (await db.execute(select(Athlete).limit(1))).scalar_one().id


def _completed(athlete_id, d: date, sid: int) -> CompletedWorkout:
    return CompletedWorkout(
        athlete_id=athlete_id,
        strava_activity_id=sid,
        source="strava",
        activity_date=d,
        started_at=datetime.combine(d, datetime.min.time()),
        activity_type="Run",
        family=WorkoutFamily.running,
        duration_s=1800,
        distance_m=Decimal("5000.00"),
        raw_summary_json={"id": sid},
    )


async def test_link_completed_sets_done_and_confidence_1(seeded_db, seeded_auth_headers, client):
    db = seeded_db
    athlete_id = await _athlete_id(db)
    planned = await _first_planned(db)
    cw = _completed(athlete_id, planned.scheduled_date, 555)
    db.add(cw)
    await db.commit()
    await db.refresh(cw)

    r = await client.post(
        f"/workouts/{planned.id}/link-completed",
        headers=seeded_auth_headers,
        json={"completed_id": str(cw.id)},
    )
    assert r.status_code == 200
    await db.refresh(planned)
    assert planned.status == WorkoutStatus.done
    recon = (
        await db.execute(select(Reconciliation).where(Reconciliation.completed_id == cw.id))
    ).scalar_one()
    assert recon.planned_id == planned.id
    assert float(recon.match_confidence) == 1.0


async def test_link_rejects_foreign_completed_id(seeded_db, seeded_auth_headers, client):
    db = seeded_db
    planned = await _first_planned(db)
    # completed belonging to a DIFFERENT athlete
    other = uuid.uuid4()
    from app.models.athlete import Athlete

    db.add(Athlete(id=other, name="Other", email="other@x.dev", password_hash="x"))
    await db.flush()
    cw = _completed(other, planned.scheduled_date, 777)
    db.add(cw)
    await db.commit()
    await db.refresh(cw)

    r = await client.post(
        f"/workouts/{planned.id}/link-completed",
        headers=seeded_auth_headers,
        json={"completed_id": str(cw.id)},
    )
    assert r.status_code == 404


async def test_link_rejects_double_link(seeded_db, seeded_auth_headers, client):
    db = seeded_db
    athlete_id = await _athlete_id(db)
    planned = await _first_planned(db)
    cw = _completed(athlete_id, planned.scheduled_date, 888)
    db.add(cw)
    await db.flush()
    db.add(Reconciliation(athlete_id=athlete_id, planned_id=None, completed_id=cw.id, match_confidence=None))
    await db.commit()
    await db.refresh(cw)

    r = await client.post(
        f"/workouts/{planned.id}/link-completed",
        headers=seeded_auth_headers,
        json={"completed_id": str(cw.id)},
    )
    assert r.status_code == 409


async def test_candidates_returns_nearest_unlinked(seeded_db, seeded_auth_headers, client, monkeypatch):
    monkeypatch.setattr(settings, "strava_client_id", "42")
    monkeypatch.setattr(settings, "strava_client_secret", "s")
    monkeypatch.setattr(settings, "strava_redirect_uri", "https://x.app/cb")
    db = seeded_db
    athlete_id = await _athlete_id(db)
    planned = await _first_planned(db)
    # connect strava so candidates can (no-op) sync
    db.add(
        StravaAuthState(
            athlete_id=athlete_id,
            access_token="acc",
            refresh_token="ref",
            expires_at=datetime.now(UTC) + timedelta(hours=5),
        )
    )
    near = _completed(athlete_id, planned.scheduled_date, 1)
    far = _completed(athlete_id, planned.scheduled_date + timedelta(days=20), 2)
    db.add_all([near, far])
    await db.commit()

    import app.routes.workouts as wr

    fake = MagicMock()
    fake.get_activities = AsyncMock(return_value=[])  # sync is a no-op
    with patch.object(wr, "get_strava_client", return_value=fake):
        r = await client.get(
            f"/workouts/{planned.id}/strava-candidates", headers=seeded_auth_headers
        )
    assert r.status_code == 200
    body = r.json()
    # only the near one is within +-7 days
    ids = [c["completed_id"] for c in body]
    assert str(near.id) in ids
    assert str(far.id) not in ids
```

- [ ] **Step 2: Run test to verify it fails**

Run: `docker compose exec -T api pytest tests/test_workout_linkage.py -v`
Expected: FAIL — 404 (routes not defined)

- [ ] **Step 3: Implement the endpoints**

In `app/routes/workouts.py`, add imports near the existing ones:

```python
from datetime import timedelta

from app.models.strava import StravaAuthState  # noqa: F401  (ownership scope reference)
from app.schemas.strava import CandidateOut, LinkCompletedRequest
from app.services.strava.client import get_strava_client  # noqa: F401  (patched in tests)
from app.services.strava.sync import StravaSyncService
```

Add a pace formatter helper near the other module helpers (if `_format_pace` does not already exist):

```python
def _format_pace_from_completed(cw: CompletedWorkout) -> str | None:
    if cw.avg_pace_s_per_km is None:
        return None
    # convert s/km -> mm:ss per mile
    s_per_mi = round(cw.avg_pace_s_per_km * 1.609344)
    return f"{s_per_mi // 60}:{s_per_mi % 60:02d}"
```

Add the two endpoints (anywhere within the router, e.g. after `log_completed`):

```python
@router.get("/{workout_id}/strava-candidates", response_model=list[CandidateOut])
async def strava_candidates(
    workout_id: uuid.UUID,
    athlete: Athlete = Depends(get_current_athlete),
    db: AsyncSession = Depends(get_db),
):
    planned = (
        await db.execute(
            select(PlannedWorkout)
            .join(Cycle, PlannedWorkout.cycle_id == Cycle.id)
            .join(Plan, Cycle.plan_id == Plan.id)
            .where(PlannedWorkout.id == workout_id, Plan.athlete_id == athlete.id)
        )
    ).scalar_one_or_none()
    if planned is None:
        raise HTTPException(status_code=404, detail="Workout not found")

    # Pull fresh activities first (best-effort; ignore upstream failure here so the
    # picker still shows already-ingested runs).
    try:
        await StravaSyncService(db, athlete.id).sync()
    except Exception:  # noqa: BLE001
        pass

    linked_ids = select(Reconciliation.completed_id).where(Reconciliation.completed_id.is_not(None))
    lo = planned.scheduled_date - timedelta(days=7)
    hi = planned.scheduled_date + timedelta(days=7)
    rows = (
        (
            await db.execute(
                select(CompletedWorkout).where(
                    CompletedWorkout.athlete_id == athlete.id,
                    CompletedWorkout.activity_date >= lo,
                    CompletedWorkout.activity_date <= hi,
                    CompletedWorkout.id.not_in(linked_ids),
                )
            )
        )
        .scalars()
        .all()
    )
    rows.sort(key=lambda cw: abs((cw.activity_date - planned.scheduled_date).days))
    rows = rows[:5]

    return [
        CandidateOut(
            completed_id=cw.id,
            activity_date=cw.activity_date,
            activity_type=cw.activity_type,
            distance_mi=round(float(cw.distance_m) / 1609.344, 2) if cw.distance_m else None,
            duration_min=round(cw.duration_s / 60),
            avg_pace_str=_format_pace_from_completed(cw),
            source=cw.source,
        )
        for cw in rows
    ]


@router.post("/{workout_id}/link-completed", response_model=LogCompletedResponse)
async def link_completed(
    workout_id: uuid.UUID,
    body: LinkCompletedRequest,
    athlete: Athlete = Depends(get_current_athlete),
    db: AsyncSession = Depends(get_db),
):
    planned = (
        await db.execute(
            select(PlannedWorkout)
            .join(Cycle, PlannedWorkout.cycle_id == Cycle.id)
            .join(Plan, Cycle.plan_id == Plan.id)
            .where(PlannedWorkout.id == workout_id, Plan.athlete_id == athlete.id)
        )
    ).scalar_one_or_none()
    if planned is None:
        raise HTTPException(status_code=404, detail="Workout not found")
    if planned.status in (WorkoutStatus.done, WorkoutStatus.skipped):
        raise HTTPException(status_code=409, detail=f"Cannot link a {planned.status.value} workout")

    # Re-validate ownership of the completed workout (untrusted client input).
    completed = (
        await db.execute(
            select(CompletedWorkout).where(
                CompletedWorkout.id == body.completed_id,
                CompletedWorkout.athlete_id == athlete.id,
            )
        )
    ).scalar_one_or_none()
    if completed is None:
        raise HTTPException(status_code=404, detail="Completed workout not found")

    already = (
        await db.execute(
            select(Reconciliation).where(Reconciliation.completed_id == completed.id)
        )
    ).scalar_one_or_none()
    if already is not None:
        raise HTTPException(status_code=409, detail="Activity already linked")

    recon = Reconciliation(
        athlete_id=athlete.id,
        planned_id=planned.id,
        completed_id=completed.id,
        match_confidence=Decimal("1.0"),
    )
    db.add(recon)
    planned.status = WorkoutStatus.done
    await db.commit()
    await db.refresh(planned)
    await db.refresh(completed)
    await db.refresh(recon)

    invalidate_for_athlete(athlete.id)

    return LogCompletedResponse(
        planned=PlannedWorkoutOut.model_validate(planned),
        completed=CompletedWorkoutOut.model_validate(completed),
        reconciliation=ReconciliationOut.model_validate(recon),
    )
```

Note: `LogCompletedResponse`, `PlannedWorkoutOut`, `CompletedWorkoutOut`, `ReconciliationOut`, `Decimal`, `Cycle`, `Plan`, `Reconciliation`, `invalidate_for_athlete` are already imported in `workouts.py` (used by `log_completed`). `CompletedWorkoutOut` must expose the new columns — verify it uses `from_attributes`; if it's an explicit field list, add `source`, `avg_cadence`, `avg_watts`, `relative_effort`, `strava_activity_id` (optional) so serialization doesn't drop them.

- [ ] **Step 4: Run tests to verify they pass**

Run: `docker compose exec -T api pytest tests/test_workout_linkage.py -v`
Expected: PASS (all 4)

- [ ] **Step 5: Commit**

```bash
git add app/routes/workouts.py tests/test_workout_linkage.py
git commit -m "feat(strava): mark-complete linkage — strava-candidates + link-completed (ownership re-validated)"
```

---

## Task 13: Alembic migration (real DB only)

**Files:**
- Create: `alembic/versions/<rev>_strava_integration.py`

- [ ] **Step 1: Generate a revision stub**

Run: `docker compose exec -T api alembic revision -m "strava integration"`
This prints the new file path under `alembic/versions/`. Open it.

- [ ] **Step 2: Hand-write the migration**

Replace the generated `upgrade()`/`downgrade()` with (keep the auto-generated `revision`/`down_revision` header lines intact):

```python
import sqlalchemy as sa
from alembic import op


def upgrade() -> None:
    op.create_table(
        "strava_auth_state",
        sa.Column("athlete_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("access_token", sa.Text(), nullable=False),
        sa.Column("refresh_token", sa.Text(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("athlete_strava_id", sa.BigInteger(), nullable=True),
        sa.Column("scope", sa.Text(), nullable=True),
        sa.Column("last_successful_sync", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("last_error_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["athlete_id"], ["athletes.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("athlete_id"),
    )

    op.add_column("completed_workouts", sa.Column("strava_activity_id", sa.BigInteger(), nullable=True))
    op.create_unique_constraint(
        "uq_completed_strava_activity_id", "completed_workouts", ["strava_activity_id"]
    )
    op.add_column(
        "completed_workouts",
        sa.Column("source", sa.Text(), nullable=False, server_default="manual"),
    )
    op.add_column("completed_workouts", sa.Column("avg_cadence", sa.Numeric(5, 1), nullable=True))
    op.add_column("completed_workouts", sa.Column("avg_watts", sa.Numeric(6, 1), nullable=True))
    op.add_column("completed_workouts", sa.Column("relative_effort", sa.SmallInteger(), nullable=True))

    # Backfill source for existing rows: garmin if it has a garmin id, else manual.
    op.execute(
        "UPDATE completed_workouts SET source = 'garmin' WHERE garmin_activity_id IS NOT NULL"
    )


def downgrade() -> None:
    op.drop_column("completed_workouts", "relative_effort")
    op.drop_column("completed_workouts", "avg_watts")
    op.drop_column("completed_workouts", "avg_cadence")
    op.drop_column("completed_workouts", "source")
    op.drop_constraint("uq_completed_strava_activity_id", "completed_workouts", type_="unique")
    op.drop_column("completed_workouts", "strava_activity_id")
    op.drop_table("strava_auth_state")
```

- [ ] **Step 3: Apply and verify**

Run: `docker compose exec -T api alembic upgrade head`
Expected: no error. Then verify a round-trip:
Run: `docker compose exec -T api alembic downgrade -1 && docker compose exec -T api alembic upgrade head`
Expected: both succeed.

- [ ] **Step 4: Commit**

```bash
git add alembic/versions/
git commit -m "feat(strava): migration — strava_auth_state + CompletedWorkout columns + source backfill"
```

---

## Task 14: Full-suite verification + lint

**Files:** none (verification)

- [ ] **Step 1: Run the entire backend suite**

Run: `docker compose exec -T api pytest -q`
Expected: all green (128 prior + the new Strava tests).

- [ ] **Step 2: Lint**

Run: `docker compose exec -T api ruff check app tests`
Expected: clean. Fix any E402 (hoist imports) or unused-import findings, re-run.

- [ ] **Step 3: Commit any lint fixes**

```bash
git add -A
git commit -m "chore(strava): lint + full-suite green"
```

---

## Manual / deploy follow-ups (not code tasks)

- Register the API application + callback URL (`STRAVA_REDIRECT_URI`) in Strava's developer settings.
- Set `STRAVA_CLIENT_ID`, `STRAVA_CLIENT_SECRET`, `STRAVA_REDIRECT_URI` on Railway.
- **Live smoke-test** (the unit tests mock Strava): connect via OAuth against your real account, `POST /strava/sync`, confirm activities ingest, then MARK DONE → candidate picker → link.
- Write the **mobile follow-up plan** (Settings Strava card + MARK DONE picker, `useStrava`/`useStravaCandidates`/`useLinkCompleted`, `tsc --noEmit` gate).

---

## Self-Review

- **Spec coverage:** OAuth (T5,T10) · token refresh (T8) · ingest-only sync + dedup (T8) · mapping incl. pace/HR/cadence/watts/effort (T7) · `source`/`strava_activity_id` columns (T3) · auth-state table (T4) · mark-complete candidates + explicit link with ownership re-validation + double-link reject (T12) · CORS-safe 502/503 (T10,T11) · disconnect/deauthorize (T10) · migration + backfill (T13) · config (T1) · family mapping (T2). Mobile UX is deferred to the follow-up plan (documented). ✓
- **Type consistency:** `StravaSyncService(db, athlete_id)`, `map_activity(athlete_id, act)`, `get_strava_client()`, `StravaTokens`, `tokens_from_response`, `needs_refresh`, `CandidateOut`, `LinkCompletedRequest` are used identically across tasks. ✓
- **Placeholder scan:** every code step contains complete code; the only `<rev>` is the Alembic-generated revision id (intentional). ✓
