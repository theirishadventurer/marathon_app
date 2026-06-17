from datetime import UTC, datetime, timedelta

from sqlalchemy import select

from app.models.strava import StravaAuthState
from app.services.strava import oauth


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
    assert oauth.needs_refresh(now + timedelta(minutes=2), now) is True
    assert oauth.needs_refresh(now + timedelta(minutes=30), now) is False
    assert oauth.needs_refresh(now - timedelta(minutes=1), now) is True
