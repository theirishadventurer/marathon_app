from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Literal
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.plan import Cycle, Plan
from app.models.reconciliation import Reconciliation
from app.models.workout import (
    CompletedWorkout,
    PlannedWorkout,
    WorkoutStatus,
    WorkoutType,
)
from app.schemas.plan import (
    CycleFull,
    PlanFullOut,
    WeekRollup,
)

_METERS_PER_MILE = Decimal("1609.344")


async def build_plan_full(db: AsyncSession, athlete_id: UUID) -> PlanFullOut:
    """One indexed query for week rollups + a separate reconciled-actuals
    join, returned as a plan -> cycles -> weeks tree."""

    plan = (
        await db.execute(
            select(Plan).where(Plan.athlete_id == athlete_id, Plan.is_active.is_(True)).limit(1)
        )
    ).scalar_one_or_none()
    if plan is None:
        raise ValueError(f"No active plan for athlete {athlete_id}")

    cycles = (
        (await db.execute(select(Cycle).where(Cycle.plan_id == plan.id).order_by(Cycle.sequence)))
        .scalars()
        .all()
    )

    rollup_rows = (
        await db.execute(
            select(
                PlannedWorkout.cycle_id.label("cycle_id"),
                PlannedWorkout.week_number.label("week_number"),
                func.count().label("planned_count"),
                func.count()
                .filter(PlannedWorkout.status == WorkoutStatus.done)
                .label("done_count"),
                func.count()
                .filter(PlannedWorkout.status == WorkoutStatus.skipped)
                .label("skipped_count"),
                func.count()
                .filter(PlannedWorkout.status == WorkoutStatus.moved)
                .label("moved_count"),
                func.coalesce(func.sum(PlannedWorkout.distance_mi), 0).label("planned_mi"),
                func.min(PlannedWorkout.scheduled_date).label("week_start"),
                func.max(PlannedWorkout.scheduled_date).label("week_end"),
                func.bool_or(PlannedWorkout.type == WorkoutType.race).label("has_race"),
            )
            .join(Cycle, Cycle.id == PlannedWorkout.cycle_id)
            .where(Cycle.plan_id == plan.id)
            .group_by(PlannedWorkout.cycle_id, PlannedWorkout.week_number)
            .order_by(PlannedWorkout.cycle_id, PlannedWorkout.week_number)
        )
    ).all()

    actual_rows = (
        await db.execute(
            select(
                PlannedWorkout.cycle_id.label("cycle_id"),
                PlannedWorkout.week_number.label("week_number"),
                func.coalesce(func.sum(CompletedWorkout.distance_m), 0).label("actual_m"),
            )
            .join(Reconciliation, Reconciliation.planned_id == PlannedWorkout.id)
            .join(CompletedWorkout, CompletedWorkout.id == Reconciliation.completed_id)
            .join(Cycle, Cycle.id == PlannedWorkout.cycle_id)
            .where(Cycle.plan_id == plan.id)
            .group_by(PlannedWorkout.cycle_id, PlannedWorkout.week_number)
        )
    ).all()

    actual_mi_by_key: dict[tuple[UUID, int], Decimal] = {}
    for row in actual_rows:
        key = (row.cycle_id, row.week_number)
        meters = Decimal(str(row.actual_m or 0))
        actual_mi_by_key[key] = (meters / _METERS_PER_MILE).quantize(Decimal("0.1"))

    race_planned_id_by_cycle = await _race_planned_id_by_cycle(db, plan.id)

    today = date.today()
    cycles_full: list[CycleFull] = []
    for cycle in cycles:
        weeks_for_cycle = [r for r in rollup_rows if r.cycle_id == cycle.id]
        weeks_for_cycle.sort(key=lambda r: r.week_number)

        prior_three: list[Decimal] = []
        weeks: list[WeekRollup] = []
        for r in weeks_for_cycle:
            planned_mi = Decimal(str(r.planned_mi or 0))
            actual_mi = actual_mi_by_key.get((cycle.id, r.week_number), Decimal("0.0"))
            is_peak = (
                cycle.peak_week_target is not None and r.week_number == cycle.peak_week_target
            )
            is_cutback = _is_cutback(planned_mi, prior_three)
            status = _week_status(
                week_start=r.week_start,
                week_end=r.week_end,
                planned_count=r.planned_count,
                done_count=r.done_count,
                skipped_count=r.skipped_count,
                today=today,
            )

            weeks.append(
                WeekRollup(
                    week_number=r.week_number,
                    week_start=r.week_start,
                    week_end=r.week_end,
                    planned_count=r.planned_count,
                    done_count=r.done_count,
                    skipped_count=r.skipped_count,
                    moved_count=r.moved_count,
                    planned_mi=planned_mi,
                    actual_mi=actual_mi,
                    is_cutback=is_cutback,
                    is_peak=is_peak,
                    has_race=bool(r.has_race),
                    status=status,
                )
            )

            prior_three.append(planned_mi)
            if len(prior_three) > 3:
                prior_three.pop(0)

        cycles_full.append(
            CycleFull(
                id=cycle.id,
                name=cycle.name,
                sequence=cycle.sequence,
                race_name=cycle.race_name,
                race_date=cycle.race_date,
                start_date=cycle.start_date,
                end_date=cycle.end_date,
                peak_week_target=cycle.peak_week_target,
                race_planned_id=race_planned_id_by_cycle.get(cycle.id),
                weeks=weeks,
            )
        )

    return PlanFullOut(
        plan_name=plan.name,
        plan_id=plan.id,
        start_date=plan.start_date,
        end_date=plan.end_date,
        cycles=cycles_full,
    )


async def _race_planned_id_by_cycle(db: AsyncSession, plan_id: UUID) -> dict[UUID, UUID]:
    rows = (
        await db.execute(
            select(PlannedWorkout.cycle_id, PlannedWorkout.id)
            .join(Cycle, Cycle.id == PlannedWorkout.cycle_id)
            .where(Cycle.plan_id == plan_id, PlannedWorkout.type == WorkoutType.race)
        )
    ).all()
    return {row.cycle_id: row.id for row in rows}


def _is_cutback(planned_mi: Decimal, prior_three: list[Decimal]) -> bool:
    if len(prior_three) < 3 or planned_mi == 0:
        return False
    avg = sum(prior_three, Decimal(0)) / Decimal(3)
    return planned_mi < avg * Decimal("0.75")


def _week_status(
    *,
    week_start: date,
    week_end: date,
    planned_count: int,
    done_count: int,
    skipped_count: int,
    today: date,
) -> Literal["done", "partial", "current", "upcoming", "skipped"]:
    if today < week_start:
        return "upcoming"
    if week_start <= today <= week_end:
        return "current"
    if planned_count == 0:
        return "upcoming"
    if done_count == planned_count:
        return "done"
    if skipped_count > 0 or done_count == 0:
        return "skipped" if done_count == 0 else "partial"
    return "partial"
