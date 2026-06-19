from decimal import Decimal

import pytest
from sqlalchemy import func, select

from app.config import settings
from app.models.metrics import DailyMetric
from app.models.workout import CompletedWorkout

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


async def test_ingest_creates_and_dedups(client, db, ingest_configured):
    hdr = {"X-Ingest-Token": "test-ingest-token"}
    body = {"activities": [ACTIVITY], "metrics": [METRIC]}
    r1 = await client.post("/garmin/ingest", json=body, headers=hdr)
    assert r1.status_code == 200
    assert r1.json()["synced_activities"] == 1
    assert r1.json()["synced_metrics"] == 1
    r2 = await client.post("/garmin/ingest", json=body, headers=hdr)
    assert r2.status_code == 200
    assert r2.json()["skipped"] == 0
    assert r2.json()["synced_activities"] == 0  # deduped
    # Metrics merge means second POST still counts as 1 synced (merge path)
    # but DB must have exactly ONE CompletedWorkout and ONE DailyMetric
    workout_count = (await db.execute(select(func.count()).select_from(CompletedWorkout))).scalar()
    metric_count = (await db.execute(select(func.count()).select_from(DailyMetric))).scalar()
    assert workout_count == 1
    assert metric_count == 1


async def test_ingest_skips_malformed_activity(client, ingest_configured):
    hdr = {"X-Ingest-Token": "test-ingest-token"}
    body = {"activities": [{"startTimeLocal": "2026-06-10 07:30:00"}], "metrics": []}
    r = await client.post("/garmin/ingest", json=body, headers=hdr)
    assert r.status_code == 200
    assert r.json()["synced_activities"] == 0
    assert r.json()["skipped"] == 1


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


# --- New tests (M2a, M2b, I2) ---


async def test_ingest_503_when_athlete_email_unconfigured(client, monkeypatch, ingest_configured):
    """M2a: token present but garmin_ingest_athlete_email blank → 503."""
    monkeypatch.setattr(settings, "garmin_ingest_athlete_email", "")
    r = await client.post(
        "/garmin/ingest",
        json={"activities": [], "metrics": []},
        headers={"X-Ingest-Token": "test-ingest-token"},
    )
    assert r.status_code == 503


async def test_ingest_400_when_athlete_email_unknown(client, monkeypatch, ingest_configured):
    """M2b: token present but athlete email not in DB → 400."""
    monkeypatch.setattr(settings, "garmin_ingest_athlete_email", "nobody@nowhere.test")
    r = await client.post(
        "/garmin/ingest",
        json={"activities": [], "metrics": []},
        headers={"X-Ingest-Token": "test-ingest-token"},
    )
    assert r.status_code == 400


async def test_ingest_metric_backfills_late_fields(client, db, ingest_configured):
    """I2: second POST merges non-null fields into the existing DailyMetric row."""
    hdr = {"X-Ingest-Token": "test-ingest-token"}
    # First ingest: just resting HR for 2026-06-11
    r1 = await client.post(
        "/garmin/ingest",
        json={"metrics": [{"calendarDate": "2026-06-11", "restingHeartRate": 48}]},
        headers=hdr,
    )
    assert r1.status_code == 200
    assert r1.json()["synced_metrics"] == 1

    # Second ingest: same date + late-arriving sleep + HRV fields
    r2 = await client.post(
        "/garmin/ingest",
        json={
            "metrics": [
                {
                    "calendarDate": "2026-06-11",
                    "restingHeartRate": 48,
                    "sleepScore": 82,
                    "hrvOvernight": 55,
                }
            ]
        },
        headers=hdr,
    )
    assert r2.status_code == 200
    assert r2.json()["synced_metrics"] == 1  # merge counts as synced

    # DB must still have exactly ONE row for that date, with all three fields set
    from datetime import date

    result = await db.execute(
        select(DailyMetric).where(DailyMetric.metric_date == date(2026, 6, 11))
    )
    stored = result.scalar_one()
    assert stored.resting_hr == 48
    assert stored.sleep_score == 82
    assert stored.hrv_overnight_ms is not None
