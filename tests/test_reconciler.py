from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.lib.workout_family import family_for_planned
from app.models.athlete import Athlete
from app.models.plan import Cycle, Plan
from app.models.reconciliation import Reconciliation
from app.models.workout import (
    CompletedWorkout,
    PlannedWorkout,
    WorkoutFamily,
    WorkoutStatus,
    WorkoutType,
)
from app.services.reconciler import reconcile


# ── helpers ───────────────────────────────────────────────────────────


async def _create_plan_with_workout(
    db: AsyncSession,
    athlete_id,
    workout_date: date,
    workout_type: WorkoutType = WorkoutType.easy,
    distance_mi: Decimal = Decimal("5.0"),
) -> PlannedWorkout:
    plan = Plan(
        athlete_id=athlete_id,
        name="Test Plan",
        start_date=date(2026, 4, 13),
        end_date=date(2027, 4, 11),
        philosophy_md="test",
    )
    db.add(plan)
    await db.flush()

    cycle = Cycle(
        plan_id=plan.id,
        name="Test Cycle",
        sequence=1,
        race_name="Test Race",
        race_date=date(2026, 10, 25),
        start_date=date(2026, 4, 13),
        end_date=date(2026, 10, 25),
    )
    db.add(cycle)
    await db.flush()

    pw = PlannedWorkout(
        cycle_id=cycle.id,
        scheduled_date=workout_date,
        original_date=workout_date,
        week_number=1,
        type=workout_type,
        family=family_for_planned(workout_type),
        distance_mi=distance_mi,
        duration_min=45,
        title="Test",
        description_md="Test",
        intent_md="Test",
    )
    db.add(pw)
    await db.flush()
    return pw


def _make_completed(
    athlete_id,
    activity_date: date,
    family: WorkoutFamily = WorkoutFamily.running,
    distance_m: Decimal = Decimal("8046.72"),
    garmin_id: int = 1,
) -> CompletedWorkout:
    return CompletedWorkout(
        athlete_id=athlete_id,
        garmin_activity_id=garmin_id,
        activity_date=activity_date,
        started_at=datetime(activity_date.year, activity_date.month, activity_date.day, 7, 0),
        activity_type="running",
        family=family,
        duration_s=2700,
        distance_m=distance_m,
        raw_summary_json={"source": "test"},
    )


# ── tests ─────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_single_match(db: AsyncSession, athlete: Athlete):
    d = date(2026, 5, 1)
    pw = await _create_plan_with_workout(db, athlete.id, d)
    cw = _make_completed(athlete.id, d)
    db.add(cw)
    await db.flush()

    report = await reconcile(db, athlete.id)

    assert report["matched"] == 1
    assert report["bonus"] == 0

    rec = (
        await db.execute(select(Reconciliation).where(Reconciliation.completed_id == cw.id))
    ).scalar_one()
    assert rec.planned_id == pw.id
    assert rec.match_confidence == Decimal("1.00")

    await db.refresh(pw)
    assert pw.status == WorkoutStatus.done


@pytest.mark.asyncio
async def test_no_match_creates_bonus(db: AsyncSession, athlete: Athlete):
    d = date(2026, 5, 1)
    cw = _make_completed(athlete.id, d, garmin_id=2)
    db.add(cw)
    await db.flush()

    report = await reconcile(db, athlete.id)

    assert report["bonus"] == 1
    assert report["matched"] == 0

    rec = (
        await db.execute(select(Reconciliation).where(Reconciliation.completed_id == cw.id))
    ).scalar_one()
    assert rec.planned_id is None


@pytest.mark.asyncio
async def test_idempotent(db: AsyncSession, athlete: Athlete):
    d = date(2026, 5, 1)
    pw = await _create_plan_with_workout(db, athlete.id, d)
    cw = _make_completed(athlete.id, d, garmin_id=3)
    db.add(cw)
    await db.flush()

    await reconcile(db, athlete.id)
    report2 = await reconcile(db, athlete.id)

    assert report2["matched"] == 0
    assert report2["bonus"] == 0
    assert report2["skipped"] == 0

    count = (
        await db.execute(
            select(Reconciliation).where(Reconciliation.completed_id == cw.id)
        )
    ).scalars().all()
    assert len(count) == 1
