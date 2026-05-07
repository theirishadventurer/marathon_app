from __future__ import annotations

from datetime import date, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import select


@pytest.mark.asyncio
async def test_recent_completed_requires_auth(client):
    response = await client.get("/workouts/completed/recent")
    assert response.status_code in (401, 403)


@pytest.mark.asyncio
async def test_recent_completed_returns_most_recent_n(
    client,
    seeded_auth_headers,
    seeded_db,
):
    """Seed several completed workouts, verify endpoint returns them most-recent first."""
    from app.models.athlete import Athlete
    from app.models.workout import CompletedWorkout, WorkoutFamily

    athlete = (await seeded_db.execute(select(Athlete).limit(1))).scalar_one()

    base = datetime(2026, 5, 1, 8, 0, 0)
    for i in range(7):
        seeded_db.add(
            CompletedWorkout(
                athlete_id=athlete.id,
                garmin_activity_id=1000 + i,
                activity_date=date(2026, 5, 1) + timedelta(days=i),
                started_at=base + timedelta(days=i),
                activity_type="running",
                family=WorkoutFamily.running,
                duration_s=3000 + i * 60,
                distance_m=Decimal("8000.00"),
                avg_hr=140 + i,
                max_hr=None,
                avg_pace_s_per_km=400,
                elevation_gain_m=None,
                calories=None,
                raw_summary_json={"source": "test"},
            )
        )
    await seeded_db.commit()

    response = await client.get(
        "/workouts/completed/recent?limit=5",
        headers=seeded_auth_headers,
    )
    assert response.status_code == 200, response.text
    rows = response.json()
    assert len(rows) == 5
    # Most recent first — i=6 has the latest started_at
    assert rows[0]["garmin_activity_id"] == 1006
    assert rows[1]["garmin_activity_id"] == 1005
    assert rows[4]["garmin_activity_id"] == 1002


@pytest.mark.asyncio
async def test_recent_completed_default_limit_is_5(
    client,
    seeded_auth_headers,
    seeded_db,
):
    from app.models.athlete import Athlete
    from app.models.workout import CompletedWorkout, WorkoutFamily

    athlete = (await seeded_db.execute(select(Athlete).limit(1))).scalar_one()
    base = datetime(2026, 5, 1, 8, 0, 0)
    for i in range(8):
        seeded_db.add(
            CompletedWorkout(
                athlete_id=athlete.id,
                garmin_activity_id=2000 + i,
                activity_date=date(2026, 5, 1) + timedelta(days=i),
                started_at=base + timedelta(days=i),
                activity_type="running",
                family=WorkoutFamily.running,
                duration_s=3000,
                distance_m=Decimal("8000.00"),
                avg_hr=140,
                max_hr=None,
                avg_pace_s_per_km=400,
                elevation_gain_m=None,
                calories=None,
                raw_summary_json={"source": "test"},
            )
        )
    await seeded_db.commit()

    response = await client.get(
        "/workouts/completed/recent",
        headers=seeded_auth_headers,
    )
    assert response.status_code == 200
    assert len(response.json()) == 5


@pytest.mark.asyncio
async def test_recent_completed_clamps_limit_high(
    client,
    seeded_auth_headers,
):
    response = await client.get(
        "/workouts/completed/recent?limit=500",
        headers=seeded_auth_headers,
    )
    # Should NOT 400 — clamped to 50
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_recent_completed_clamps_limit_low(
    client,
    seeded_auth_headers,
):
    response = await client.get(
        "/workouts/completed/recent?limit=0",
        headers=seeded_auth_headers,
    )
    # 0 → clamped to 1 (return at most 1, even empty list is OK)
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_recent_completed_scoped_to_athlete(
    client,
    seeded_auth_headers,
    seeded_db,
):
    """Other athletes' completed workouts must not leak."""
    from app.auth import hash_password
    from app.models.athlete import Athlete
    from app.models.workout import CompletedWorkout, WorkoutFamily

    other = Athlete(
        id=uuid4(),
        name="Other",
        email="other@x.dev",
        password_hash=hash_password("x"),
        hr_zones_json={},
        pace_targets_json={},
        injury_notes_md="",
    )
    seeded_db.add(other)
    await seeded_db.commit()

    seeded_db.add(
        CompletedWorkout(
            athlete_id=other.id,
            garmin_activity_id=9999,
            activity_date=date(2026, 5, 5),
            started_at=datetime(2026, 5, 5, 9, 0, 0),
            activity_type="running",
            family=WorkoutFamily.running,
            duration_s=3000,
            distance_m=Decimal("8000.00"),
            avg_hr=145,
            max_hr=None,
            avg_pace_s_per_km=400,
            elevation_gain_m=None,
            calories=None,
            raw_summary_json={"source": "test"},
        )
    )
    await seeded_db.commit()

    response = await client.get(
        "/workouts/completed/recent",
        headers=seeded_auth_headers,
    )
    assert response.status_code == 200
    rows = response.json()
    assert all(row["garmin_activity_id"] != 9999 for row in rows)


@pytest.mark.asyncio
async def test_recent_completed_busted_by_log_completed(
    client,
    seeded_auth_headers,
    seeded_db,
):
    """After Feat A's POST log-completed, the recent-completed cache is busted
    so the new completion appears."""
    from app.models.workout import PlannedWorkout, WorkoutStatus, WorkoutType

    # Prime the cache (likely empty)
    r1 = await client.get(
        "/workouts/completed/recent",
        headers=seeded_auth_headers,
    )
    assert r1.status_code == 200
    n_before = len(r1.json())

    # Log a completion
    workout = (
        await seeded_db.execute(
            select(PlannedWorkout)
            .where(PlannedWorkout.type == WorkoutType.easy)
            .where(PlannedWorkout.status == WorkoutStatus.planned)
            .limit(1)
        )
    ).scalar_one()
    log = await client.post(
        f"/workouts/{workout.id}/log-completed",
        json={"distance_mi": 5.0, "duration_min": 50},
        headers=seeded_auth_headers,
    )
    assert log.status_code == 200, log.text

    # Recent endpoint reflects the new row
    r2 = await client.get(
        "/workouts/completed/recent",
        headers=seeded_auth_headers,
    )
    assert r2.status_code == 200
    n_after = len(r2.json())
    assert n_after == n_before + 1
