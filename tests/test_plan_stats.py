import pytest
from sqlalchemy import select


@pytest.mark.asyncio
async def test_build_plan_stats_returns_cycle_kpis(seeded_db):
    from app.models.athlete import Athlete
    from app.services.plan_aggregator import build_plan_stats

    athlete = (await seeded_db.execute(select(Athlete).limit(1))).scalar_one()
    stats = await build_plan_stats(seeded_db, athlete.id, scope="cycle")

    assert stats.scope == "cycle"
    assert stats.cycle_id is not None
    assert 0.0 <= stats.on_plan_pct <= 1.0
    assert stats.done_count >= 0
    assert stats.skipped_count >= 0
    assert stats.streak_days >= 0
    assert stats.next_milestone is None or stats.next_milestone.kind in (
        "peak",
        "race",
        "decision",
    )


@pytest.mark.asyncio
async def test_streak_walker_counts_consecutive_done_days(seeded_db):
    """If we mark today's planned workout as done, the streak should be at least 1."""
    from datetime import date as date_cls

    from app.models.athlete import Athlete
    from app.models.workout import PlannedWorkout, WorkoutStatus
    from app.services.plan_aggregator import build_plan_stats

    athlete = (await seeded_db.execute(select(Athlete).limit(1))).scalar_one()
    today = date_cls.today()
    today_workouts = (
        (
            await seeded_db.execute(
                select(PlannedWorkout).where(PlannedWorkout.scheduled_date == today)
            )
        )
        .scalars()
        .all()
    )
    for w in today_workouts:
        w.status = WorkoutStatus.done
    await seeded_db.commit()

    stats = await build_plan_stats(seeded_db, athlete.id, scope="cycle")
    assert stats.streak_days >= 1


@pytest.mark.asyncio
async def test_plan_stats_endpoint_returns_kpis(client, seeded_auth_headers):
    response = await client.get(
        "/plan/stats",
        params={"scope": "cycle"},
        headers=seeded_auth_headers,
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["scope"] == "cycle"
    assert "on_plan_pct" in body
    assert "done_count" in body
    assert "skipped_count" in body
    assert "streak_days" in body
    assert "planned_mi" in body
    assert "actual_mi" in body


@pytest.mark.asyncio
async def test_plan_stats_endpoint_defaults_to_cycle(client, seeded_auth_headers):
    response = await client.get("/plan/stats", headers=seeded_auth_headers)
    assert response.status_code == 200
    assert response.json()["scope"] == "cycle"


@pytest.mark.asyncio
async def test_plan_stats_endpoint_requires_auth(client):
    response = await client.get("/plan/stats")
    assert response.status_code in (401, 403)


@pytest.mark.asyncio
async def test_plan_stats_endpoint_400_on_invalid_scope(client, seeded_auth_headers):
    response = await client.get(
        "/plan/stats",
        params={"scope": "garbage"},
        headers=seeded_auth_headers,
    )
    assert response.status_code == 400
