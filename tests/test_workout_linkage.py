import uuid
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

from sqlalchemy import select

from app.config import settings
from app.models.reconciliation import Reconciliation
from app.models.strava import StravaAuthState
from app.models.workout import CompletedWorkout, PlannedWorkout, WorkoutFamily, WorkoutStatus


async def _first_planned(db):
    return (
        await db.execute(
            select(PlannedWorkout)
            .where(PlannedWorkout.status == WorkoutStatus.planned)
            .limit(1)
        )
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
    db.add(
        Reconciliation(
            athlete_id=athlete_id, planned_id=None, completed_id=cw.id, match_confidence=None
        )
    )
    await db.commit()
    await db.refresh(cw)

    r = await client.post(
        f"/workouts/{planned.id}/link-completed",
        headers=seeded_auth_headers,
        json={"completed_id": str(cw.id)},
    )
    assert r.status_code == 409


async def test_candidates_returns_nearest_unlinked(
    seeded_db, seeded_auth_headers, client, monkeypatch
):
    monkeypatch.setattr(settings, "strava_client_id", "42")
    monkeypatch.setattr(settings, "strava_client_secret", "s")
    monkeypatch.setattr(settings, "strava_redirect_uri", "https://x.app/cb")
    db = seeded_db
    athlete_id = await _athlete_id(db)
    planned = await _first_planned(db)
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
    # Capture IDs before the request: rollback() in the route on a shared test
    # session expires ORM objects, so capture scalars now.
    near_id = str(near.id)
    far_id = str(far.id)

    import app.routes.workouts as wr
    import app.services.strava.sync as sync_mod_local

    fake = MagicMock()
    fake.get_activities = AsyncMock(return_value=[])
    # Patch both the route module and the sync module so the real Strava client
    # is never called (either path would cause a 401 that triggers rollback).
    with patch.object(wr, "get_strava_client", return_value=fake), \
         patch.object(sync_mod_local, "get_strava_client", return_value=fake):
        r = await client.get(
            f"/workouts/{planned.id}/strava-candidates", headers=seeded_auth_headers
        )
    assert r.status_code == 200
    body = r.json()
    ids = [c["completed_id"] for c in body]
    assert near_id in ids
    assert far_id not in ids


# ── C2 (candidates): sync failure must NOT poison the session ─────────────────

async def test_candidates_survives_sync_failure(
    seeded_db, seeded_auth_headers, client, monkeypatch
):
    """When the inline sync() raises, the session is rolled back and the candidate
    query still returns 200 with already-present unlinked completed rows."""
    monkeypatch.setattr(settings, "strava_client_id", "42")
    monkeypatch.setattr(settings, "strava_client_secret", "s")
    monkeypatch.setattr(settings, "strava_redirect_uri", "https://x.app/cb")

    db = seeded_db
    athlete_id = await _athlete_id(db)
    planned = await _first_planned(db)

    # Insert a completed row that should appear in candidates
    cw = _completed(athlete_id, planned.scheduled_date, 9001)
    db.add(cw)
    # Connect strava so sync is attempted
    db.add(
        StravaAuthState(
            athlete_id=athlete_id,
            access_token="acc",
            refresh_token="ref",
            expires_at=datetime.now(UTC) + timedelta(hours=5),
        )
    )
    await db.commit()

    # Make get_activities raise so the inline sync fails
    import app.routes.workouts as wr

    fake = MagicMock()
    fake.get_activities = AsyncMock(side_effect=RuntimeError("strava down"))
    with patch.object(wr, "get_strava_client", return_value=fake):
        r = await client.get(
            f"/workouts/{planned.id}/strava-candidates", headers=seeded_auth_headers
        )

    assert r.status_code == 200
    body = r.json()
    ids = [c["completed_id"] for c in body]
    assert str(cw.id) in ids  # already-ingested row is still returned
