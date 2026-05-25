from datetime import date, datetime
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import select


def test_week_rollup_schema_round_trip():
    from app.schemas.plan import WeekRollup

    rollup = WeekRollup(
        week_number=1,
        week_start=date(2026, 4, 13),
        week_end=date(2026, 4, 19),
        planned_count=7,
        done_count=7,
        skipped_count=0,
        moved_count=0,
        planned_mi=Decimal("18.0"),
        actual_mi=Decimal("18.4"),
        is_cutback=False,
        is_peak=False,
        has_race=False,
        status="done",
    )
    dumped = rollup.model_dump()
    assert dumped["status"] == "done"
    assert dumped["planned_mi"] == Decimal("18.0")


def test_plan_full_out_schema_round_trip():
    from app.schemas.plan import CycleFull, PlanFullOut

    cycle_id = uuid4()
    plan_id = uuid4()
    cycle = CycleFull(
        id=cycle_id,
        name="Phase 1 - MCM",
        sequence=1,
        race_name="Marine Corps Marathon",
        race_date=date(2026, 10, 25),
        start_date=date(2026, 4, 13),
        end_date=date(2026, 10, 25),
        peak_week_target=23,
        race_planned_id=uuid4(),
        weeks=[],
    )
    plan = PlanFullOut(
        plan_name="Marathon Trilogy 2026-2027",
        plan_id=plan_id,
        start_date=date(2026, 4, 13),
        end_date=date(2027, 4, 12),
        cycles=[cycle],
    )
    dumped = plan.model_dump()
    assert dumped["plan_name"] == "Marathon Trilogy 2026-2027"
    assert dumped["cycles"][0]["peak_week_target"] == 23


def test_plan_stats_out_schema_round_trip():
    from app.schemas.plan import (
        NextMilestone,
        PeakWeekSummary,
        PlanStatsOut,
    )

    stats = PlanStatsOut(
        scope="cycle",
        cycle_id=uuid4(),
        on_plan_pct=0.92,
        done_count=47,
        skipped_count=4,
        planned_to_date_count=51,
        planned_mi=Decimal("187.0"),
        actual_mi=Decimal("42.0"),
        streak_days=11,
        next_milestone=NextMilestone(
            kind="peak",
            label="WK 23 - 21mi long",
            date=date(2026, 9, 19),
        ),
        peak_week=PeakWeekSummary(
            week_number=23,
            planned_mi=Decimal("42.0"),
            long_run_mi=Decimal("21.0"),
        ),
        computed_at=datetime(2026, 5, 6, 14, 0, 0),
    )
    dumped = stats.model_dump()
    assert dumped["streak_days"] == 11
    assert dumped["next_milestone"]["kind"] == "peak"


@pytest.mark.asyncio
async def test_build_plan_full_returns_three_cycles_and_week_rollups(seeded_db):
    from app.models.athlete import Athlete
    from app.services.plan_aggregator import build_plan_full

    athlete = (await seeded_db.execute(select(Athlete).limit(1))).scalar_one()
    plan = await build_plan_full(seeded_db, athlete.id)

    assert plan.plan_name == "Marathon Trilogy 2026-2027"
    assert len(plan.cycles) == 3
    p1 = plan.cycles[0]
    assert p1.sequence == 1
    assert p1.peak_week_target == 20
    assert len(p1.weeks) == 22
    assert p1.weeks[0].planned_count >= 1
    assert all(w.status in ("done", "partial", "current", "upcoming", "skipped") for w in p1.weeks)


@pytest.mark.asyncio
async def test_build_plan_full_marks_peak_and_race(seeded_db):
    from app.models.athlete import Athlete
    from app.services.plan_aggregator import build_plan_full

    athlete = (await seeded_db.execute(select(Athlete).limit(1))).scalar_one()
    plan = await build_plan_full(seeded_db, athlete.id)
    p1 = plan.cycles[0]
    peak_weeks = [w for w in p1.weeks if w.is_peak]
    race_weeks = [w for w in p1.weeks if w.has_race]
    assert len(peak_weeks) == 1
    assert peak_weeks[0].week_number == 20
    assert len(race_weeks) >= 1


@pytest.mark.asyncio
async def test_plan_full_endpoint_happy_path(client, seeded_auth_headers):
    response = await client.get("/plan/full", headers=seeded_auth_headers)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["plan_name"] == "Marathon Trilogy 2026-2027"
    assert len(body["cycles"]) == 3
    p1 = body["cycles"][0]
    assert p1["sequence"] == 1
    assert p1["peak_week_target"] == 20
    assert len(p1["weeks"]) == 22
    week_one = p1["weeks"][0]
    assert "planned_mi" in week_one
    assert "actual_mi" in week_one
    assert week_one["status"] in ("done", "partial", "current", "upcoming", "skipped")


@pytest.mark.asyncio
async def test_plan_full_endpoint_requires_auth(client):
    response = await client.get("/plan/full")
    assert response.status_code in (401, 403)


@pytest.mark.asyncio
async def test_plan_full_cache_invalidated_on_workout_edit(
    client,
    seeded_auth_headers,
    seeded_db,
):
    """After PATCH /workouts/{id}, /plan/full must reflect the changed type."""
    from sqlalchemy import select

    from app.models.workout import PlannedWorkout

    workout = (
        await seeded_db.execute(
            select(PlannedWorkout).where(PlannedWorkout.type == "strength_a").limit(1)
        )
    ).scalar_one()
    wid = str(workout.id)

    r1 = await client.get("/plan/full", headers=seeded_auth_headers)
    assert r1.status_code == 200

    edit = await client.patch(
        f"/workouts/{wid}",
        json={"type": "easy"},
        headers=seeded_auth_headers,
    )
    assert edit.status_code == 200, edit.text

    r2 = await client.get("/plan/full", headers=seeded_auth_headers)
    assert r2.status_code == 200
