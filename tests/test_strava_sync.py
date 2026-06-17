import uuid
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

from sqlalchemy import func, select

from app.models.reconciliation import Reconciliation
from app.models.strava import StravaAuthState
from app.models.workout import CompletedWorkout, WorkoutFamily
from app.services.strava import sync as sync_mod
from app.services.strava.client import StravaClient, get_strava_client
from app.services.strava.sync import StravaSyncError, map_activity


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
    assert cw.strava_activity_id == 123456789
    assert cw.source == "strava"
    assert cw.relative_effort == 42


def test_get_strava_client_returns_client():
    c = get_strava_client()
    assert isinstance(c, StravaClient)


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
    assert cw.avg_pace_s_per_km == round(1000 / 3.34)


def test_map_activity_zero_speed_pace_none():
    athlete_id = uuid.uuid4()
    act = {**SAMPLE, "average_speed": 0, "has_heartrate": False}
    cw = map_activity(athlete_id, act)
    assert cw.avg_pace_s_per_km is None
    assert cw.avg_hr is None


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
    recon_count = (
        await db.execute(select(func.count()).select_from(Reconciliation))
    ).scalar_one()
    assert recon_count == 0  # ingest-only: no reconciliation, nothing marked done

    fake.get_activities = AsyncMock(side_effect=[[SAMPLE], []])
    with patch.object(sync_mod, "get_strava_client", return_value=fake):
        report2 = await sync_mod.StravaSyncService(db, athlete.id).sync()
    assert report2.synced_activities == 0  # dedup


async def test_sync_refreshes_expired_token(db, athlete):
    # Connect with an already-expired token so _ensure_fresh must refresh.
    db.add(
        StravaAuthState(
            athlete_id=athlete.id,
            access_token="old",
            refresh_token="oldref",
            expires_at=datetime.now(UTC) - timedelta(minutes=1),
            athlete_strava_id=1,
            scope="activity:read_all",
        )
    )
    await db.commit()

    fake = MagicMock()
    fake.refresh_token = AsyncMock(
        return_value={
            "access_token": "newacc",
            "refresh_token": "newref",
            "expires_at": int(datetime.now(UTC).timestamp()) + 21600,
            "scope": "activity:read_all",
        }
    )
    fake.get_activities = AsyncMock(return_value=[])  # no activities; we only care about refresh

    with patch.object(sync_mod, "get_strava_client", return_value=fake):
        await sync_mod.StravaSyncService(db, athlete.id).sync()

    fake.refresh_token.assert_awaited_once()
    # the access token used for get_activities must be the refreshed one
    _, kwargs = fake.get_activities.call_args
    assert kwargs["access_token"] == "newacc"
    # and it was persisted
    refreshed = (
        await db.execute(select(StravaAuthState).where(StravaAuthState.athlete_id == athlete.id))
    ).scalar_one()
    assert refreshed.access_token == "newacc"
    assert refreshed.refresh_token == "newref"


async def test_sync_paginates_multiple_pages(db, athlete):
    await _connect(db, athlete)  # fresh token

    def _page(start, count):
        out = []
        for i in range(start, start + count):
            a = dict(SAMPLE)
            a["id"] = 900000 + i
            out.append(a)
        return out

    full_page = _page(0, 100)   # exactly per_page -> triggers another fetch
    short_page = _page(100, 5)  # < 100 -> loop stops after this
    fake = MagicMock()
    fake.get_activities = AsyncMock(side_effect=[full_page, short_page])

    with patch.object(sync_mod, "get_strava_client", return_value=fake):
        report = await sync_mod.StravaSyncService(db, athlete.id).sync()

    assert report.synced_activities == 105
    assert fake.get_activities.await_count == 2
    count = (
        await db.execute(
            select(func.count()).select_from(CompletedWorkout).where(
                CompletedWorkout.athlete_id == athlete.id
            )
        )
    ).scalar_one()
    assert count == 105


# ── C1: malformed activity must not abort the whole batch ──────────────────────

async def test_sync_skips_malformed_activity_keeps_valid(db, athlete):
    """A missing start_date_local on one activity must not discard the valid one."""
    await _connect(db, athlete)
    bad = {"id": 999}  # missing start_date_local → map_activity raises KeyError
    batch = [SAMPLE, bad]

    fake = MagicMock()
    fake.get_activities = AsyncMock(side_effect=[batch, []])

    with patch.object(sync_mod, "get_strava_client", return_value=fake):
        svc = sync_mod.StravaSyncService(db, athlete.id)
        report = await svc.sync()

    assert report.synced_activities == 1
    assert len(report.errors) >= 1  # malformed activity recorded as error
    # last_successful_sync was advanced
    state = (
        await db.execute(
            select(StravaAuthState).where(StravaAuthState.athlete_id == athlete.id)
        )
    ).scalar_one()
    assert state.last_successful_sync is not None


# ── H1: duplicate id within one batch must not crash ──────────────────────────

async def test_sync_dedups_within_batch(db, athlete):
    """Same activity id twice in one fetched page → only 1 row inserted, no crash."""
    await _connect(db, athlete)
    batch = [SAMPLE, SAMPLE]  # identical id twice

    fake = MagicMock()
    fake.get_activities = AsyncMock(side_effect=[batch, []])

    with patch.object(sync_mod, "get_strava_client", return_value=fake):
        report = await sync_mod.StravaSyncService(db, athlete.id).sync()

    assert report.synced_activities == 1
    count = (
        await db.execute(
            select(func.count()).select_from(CompletedWorkout).where(
                CompletedWorkout.athlete_id == athlete.id
            )
        )
    ).scalar_one()
    assert count == 1


# ── M1: near-zero speed must not overflow SmallInteger pace ───────────────────

async def test_sync_clamps_extreme_pace(db, athlete):
    """average_speed=0.01 would give pace=100 000 s/km → overflow. Must yield None."""
    await _connect(db, athlete)
    slow_act = {**SAMPLE, "id": 77777, "average_speed": 0.01}
    batch = [slow_act]

    fake = MagicMock()
    fake.get_activities = AsyncMock(side_effect=[batch, []])

    with patch.object(sync_mod, "get_strava_client", return_value=fake):
        report = await sync_mod.StravaSyncService(db, athlete.id).sync()

    assert report.synced_activities == 1
    cw = (
        await db.execute(
            select(CompletedWorkout).where(CompletedWorkout.strava_activity_id == 77777)
        )
    ).scalar_one()
    assert cw.avg_pace_s_per_km is None  # clamped, not crashed


# ── C2/M2: refresh failure must set last_error and raise StravaSyncError ──────

async def test_sync_refresh_failure_sets_last_error(db, athlete):
    """When refresh_token() raises, last_error is persisted and StravaSyncError raised."""
    db.add(
        StravaAuthState(
            athlete_id=athlete.id,
            access_token="old",
            refresh_token="oldref",
            expires_at=datetime.now(UTC) - timedelta(minutes=1),  # expired → needs refresh
            athlete_strava_id=1,
            scope="activity:read_all",
        )
    )
    await db.commit()

    fake = MagicMock()
    fake.refresh_token = AsyncMock(side_effect=RuntimeError("network error"))

    with patch.object(sync_mod, "get_strava_client", return_value=fake):
        svc = sync_mod.StravaSyncService(db, athlete.id)
        raised = False
        try:
            await svc.sync()
        except StravaSyncError:
            raised = True

    assert raised, "StravaSyncError should have been raised"

    # Reload state in a fresh query — session must still be usable
    state = (
        await db.execute(
            select(StravaAuthState).where(StravaAuthState.athlete_id == athlete.id)
        )
    ).scalar_one()
    assert state.last_error is not None
    assert "network error" in state.last_error
    assert state.last_error_at is not None


# ── Round-2 QA: clamp distance_m / calories / avg_hr / max_hr ────────────────

def test_map_activity_clamps_out_of_range_numerics():
    act = {
        **SAMPLE,
        "distance": 99999999.0,       # exceeds Numeric(8,2) max 999999.99
        "calories": 100000,            # exceeds SmallInteger max 32767
        "average_heartrate": 70000.0,  # exceeds SmallInteger
        "max_heartrate": 70000.0,
        "has_heartrate": True,
    }
    cw = map_activity(uuid.uuid4(), act)
    assert cw.distance_m is None
    assert cw.calories is None
    assert cw.avg_hr is None
    assert cw.max_hr is None
    # row is still constructible (no exception raised)


async def test_sync_survives_out_of_range_activity(db, athlete):
    await _connect(db, athlete)
    bad = {**SAMPLE, "id": 424242, "distance": 99999999.0, "calories": 100000}
    fake = MagicMock()
    fake.get_activities = AsyncMock(side_effect=[[bad], []])
    with patch.object(sync_mod, "get_strava_client", return_value=fake):
        report = await sync_mod.StravaSyncService(db, athlete.id).sync()
    assert report.synced_activities == 1  # ingested with clamped Nones, no crash
    cnt = (
        await db.execute(
            select(func.count())
            .select_from(CompletedWorkout)
            .where(CompletedWorkout.athlete_id == athlete.id)
        )
    ).scalar_one()
    assert cnt == 1
