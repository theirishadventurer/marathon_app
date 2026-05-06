from __future__ import annotations

import time
from datetime import UTC, date, datetime
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
    NextMilestone,
    PeakWeekSummary,
    PlanFullOut,
    PlanStatsOut,
    WeekRollup,
)

_METERS_PER_MILE = Decimal("1609.344")

_PLAN_FULL_CACHE: dict[UUID, tuple[float, PlanFullOut]] = {}
_PLAN_STATS_CACHE: dict[tuple[UUID, str], tuple[float, PlanStatsOut]] = {}
_CACHE_TTL_S = 60.0


def invalidate_plan_cache(athlete_id: UUID) -> None:
    """Bust both caches for an athlete after any plan-mutating action."""
    _PLAN_FULL_CACHE.pop(athlete_id, None)
    keys_to_drop = [k for k in _PLAN_STATS_CACHE if k[0] == athlete_id]
    for k in keys_to_drop:
        _PLAN_STATS_CACHE.pop(k, None)


async def build_plan_full(db: AsyncSession, athlete_id: UUID) -> PlanFullOut:
    """One indexed query for week rollups + a separate reconciled-actuals
    join, returned as a plan -> cycles -> weeks tree."""
    cached = _PLAN_FULL_CACHE.get(athlete_id)
    now = time.monotonic()
    if cached is not None and now - cached[0] < _CACHE_TTL_S:
        return cached[1]

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

    result = PlanFullOut(
        plan_name=plan.name,
        plan_id=plan.id,
        start_date=plan.start_date,
        end_date=plan.end_date,
        cycles=cycles_full,
    )
    _PLAN_FULL_CACHE[athlete_id] = (time.monotonic(), result)
    return result


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


async def build_plan_stats(
    db: AsyncSession,
    athlete_id: UUID,
    scope: Literal["cycle", "plan"] = "cycle",
) -> PlanStatsOut:
    """Compute KPIs for the active cycle (default) or whole plan."""
    cache_key = (athlete_id, scope)
    cached = _PLAN_STATS_CACHE.get(cache_key)
    now = time.monotonic()
    if cached is not None and now - cached[0] < _CACHE_TTL_S:
        return cached[1]

    plan = (
        await db.execute(
            select(Plan).where(Plan.athlete_id == athlete_id, Plan.is_active.is_(True)).limit(1)
        )
    ).scalar_one_or_none()
    if plan is None:
        raise ValueError(f"No active plan for athlete {athlete_id}")

    today = date.today()

    if scope == "cycle":
        cycle = await _active_cycle(db, plan.id, today)
        if cycle is None:
            result = _empty_stats(scope, today)
            _PLAN_STATS_CACHE[cache_key] = (time.monotonic(), result)
            return result
        cycle_id_for_filter: UUID | None = cycle.id
    else:
        cycle_id_for_filter = None
        cycle = None

    counts_q = (
        select(
            func.count().filter(PlannedWorkout.status == WorkoutStatus.done).label("done"),
            func.count().filter(PlannedWorkout.status == WorkoutStatus.skipped).label("skipped"),
            func.count()
            .filter(
                PlannedWorkout.status.in_(
                    [WorkoutStatus.done, WorkoutStatus.skipped, WorkoutStatus.moved]
                )
            )
            .label("settled"),
            func.count().label("total_to_date"),
            func.coalesce(func.sum(PlannedWorkout.distance_mi), 0).label("planned_mi_total"),
        )
        .join(Cycle, Cycle.id == PlannedWorkout.cycle_id)
        .where(Cycle.plan_id == plan.id, PlannedWorkout.scheduled_date <= today)
    )
    if cycle_id_for_filter is not None:
        counts_q = counts_q.where(PlannedWorkout.cycle_id == cycle_id_for_filter)
    row = (await db.execute(counts_q)).one()

    on_plan_pct = (row.done / row.settled) if row.settled else 0.0

    actual_q = (
        select(func.coalesce(func.sum(CompletedWorkout.distance_m), 0).label("actual_m"))
        .select_from(PlannedWorkout)
        .join(Reconciliation, Reconciliation.planned_id == PlannedWorkout.id)
        .join(CompletedWorkout, CompletedWorkout.id == Reconciliation.completed_id)
        .join(Cycle, Cycle.id == PlannedWorkout.cycle_id)
        .where(Cycle.plan_id == plan.id, PlannedWorkout.scheduled_date <= today)
    )
    if cycle_id_for_filter is not None:
        actual_q = actual_q.where(PlannedWorkout.cycle_id == cycle_id_for_filter)
    actual_m = (await db.execute(actual_q)).scalar_one() or 0
    actual_mi = (Decimal(str(actual_m)) / _METERS_PER_MILE).quantize(Decimal("0.1"))

    streak_days = await _compute_streak(db, plan.id, cycle_id_for_filter, today)

    next_milestone, peak_week = await _next_milestone(db, plan.id, cycle, today)

    result = PlanStatsOut(
        scope=scope,
        cycle_id=cycle.id if cycle is not None else None,
        on_plan_pct=float(on_plan_pct),
        done_count=row.done,
        skipped_count=row.skipped,
        planned_to_date_count=row.total_to_date,
        planned_mi=Decimal(str(row.planned_mi_total or 0)),
        actual_mi=actual_mi,
        streak_days=streak_days,
        next_milestone=next_milestone,
        peak_week=peak_week,
        computed_at=datetime.now(UTC),
    )
    _PLAN_STATS_CACHE[cache_key] = (time.monotonic(), result)
    return result


def _empty_stats(scope: Literal["cycle", "plan"], today: date) -> PlanStatsOut:
    return PlanStatsOut(
        scope=scope,
        cycle_id=None,
        on_plan_pct=0.0,
        done_count=0,
        skipped_count=0,
        planned_to_date_count=0,
        planned_mi=Decimal("0"),
        actual_mi=Decimal("0"),
        streak_days=0,
        next_milestone=None,
        peak_week=None,
        computed_at=datetime.now(UTC),
    )


async def _active_cycle(db: AsyncSession, plan_id: UUID, today: date) -> Cycle | None:
    cycle = (
        await db.execute(
            select(Cycle)
            .where(
                Cycle.plan_id == plan_id,
                Cycle.start_date <= today,
                Cycle.end_date >= today,
            )
            .order_by(Cycle.sequence)
            .limit(1)
        )
    ).scalar_one_or_none()
    if cycle is not None:
        return cycle
    return (
        await db.execute(
            select(Cycle)
            .where(Cycle.plan_id == plan_id, Cycle.start_date <= today)
            .order_by(Cycle.start_date.desc())
            .limit(1)
        )
    ).scalar_one_or_none()


async def _compute_streak(
    db: AsyncSession,
    plan_id: UUID,
    cycle_id: UUID | None,
    today: date,
) -> int:
    """Walk back from today; a day counts if every planned row that day has
    status in (done, moved). First day with a `skipped` row breaks the streak.
    A day with no planned rows breaks (gap stops counting)."""
    q = (
        select(PlannedWorkout.scheduled_date, PlannedWorkout.status)
        .join(Cycle, Cycle.id == PlannedWorkout.cycle_id)
        .where(Cycle.plan_id == plan_id, PlannedWorkout.scheduled_date <= today)
        .order_by(PlannedWorkout.scheduled_date.desc())
    )
    if cycle_id is not None:
        q = q.where(PlannedWorkout.cycle_id == cycle_id)
    rows = (await db.execute(q)).all()

    by_day: dict[date, list[WorkoutStatus]] = {}
    for r in rows:
        by_day.setdefault(r.scheduled_date, []).append(r.status)

    streak = 0
    cursor = today
    while True:
        statuses = by_day.get(cursor)
        if statuses is None:
            break
        if any(s == WorkoutStatus.skipped for s in statuses):
            break
        if all(s in (WorkoutStatus.done, WorkoutStatus.moved) for s in statuses):
            streak += 1
            cursor = date.fromordinal(cursor.toordinal() - 1)
            continue
        break
    return streak


async def _next_milestone(
    db: AsyncSession,
    plan_id: UUID,
    cycle: Cycle | None,
    today: date,
) -> tuple[NextMilestone | None, PeakWeekSummary | None]:
    if cycle is None:
        return None, None

    days_to_race = (cycle.race_date - today).days
    peak_week = None
    if cycle.peak_week_target is not None:
        peak_rows = (
            await db.execute(
                select(
                    func.coalesce(func.sum(PlannedWorkout.distance_mi), 0).label("planned_mi"),
                    func.max(PlannedWorkout.distance_mi)
                    .filter(PlannedWorkout.type == WorkoutType.long)
                    .label("long_run_mi"),
                    func.min(PlannedWorkout.scheduled_date).label("week_start"),
                ).where(
                    PlannedWorkout.cycle_id == cycle.id,
                    PlannedWorkout.week_number == cycle.peak_week_target,
                )
            )
        ).one()
        peak_planned_mi = Decimal(str(peak_rows.planned_mi or 0))
        peak_week = PeakWeekSummary(
            week_number=cycle.peak_week_target,
            planned_mi=peak_planned_mi,
            long_run_mi=Decimal(str(peak_rows.long_run_mi))
            if peak_rows.long_run_mi is not None
            else None,
        )

        if days_to_race <= 21:
            milestone = NextMilestone(
                kind="race",
                label=f"{cycle.race_name} {days_to_race}d",
                date=cycle.race_date,
            )
        elif peak_rows.week_start is not None and peak_rows.week_start >= today:
            long_run_label = (
                f" - {peak_rows.long_run_mi}mi long" if peak_rows.long_run_mi is not None else ""
            )
            milestone = NextMilestone(
                kind="peak",
                label=f"WK {cycle.peak_week_target}{long_run_label}",
                date=peak_rows.week_start,
            )
        else:
            milestone = NextMilestone(
                kind="race",
                label=f"{cycle.race_name} {days_to_race}d",
                date=cycle.race_date,
            )
    else:
        milestone = NextMilestone(
            kind="race",
            label=f"{cycle.race_name} {days_to_race}d",
            date=cycle.race_date,
        )

    return milestone, peak_week
