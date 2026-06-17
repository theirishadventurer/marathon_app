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
