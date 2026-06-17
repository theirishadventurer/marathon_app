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
