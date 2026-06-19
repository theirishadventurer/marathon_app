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
