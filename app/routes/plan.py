from __future__ import annotations

import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import get_current_athlete, get_db
from app.models.athlete import Athlete
from app.models.plan import Cycle, Plan
from app.models.workout import PlannedWorkout
from app.schemas.plan import (
    CycleOut,
    CycleProgress,
    DayWorkouts,
    PlanCurrentOut,
    PlanFullOut,
    PlannedWorkoutOut,
    PlanStatsOut,
    TodayOut,
    WeekOut,
)
from app.services.plan_aggregator import build_plan_full, build_plan_stats

router = APIRouter(prefix="/plan", tags=["plan"])


async def _active_plan(db: AsyncSession, athlete_id) -> Plan | None:
    result = await db.execute(
        select(Plan)
        .where(Plan.athlete_id == athlete_id, Plan.is_active == True)  # noqa: E712
        .limit(1)
    )
    return result.scalar_one_or_none()


async def _active_cycle(db: AsyncSession, plan_id, today: datetime.date) -> Cycle | None:
    # Cycle where start_date <= today <= end_date
    result = await db.execute(
        select(Cycle)
        .where(Cycle.plan_id == plan_id, Cycle.start_date <= today, Cycle.end_date >= today)
        .order_by(Cycle.sequence)
        .limit(1)
    )
    cycle = result.scalar_one_or_none()
    if cycle is not None:
        return cycle
    # Between cycles: return latest cycle that has started
    result = await db.execute(
        select(Cycle)
        .where(Cycle.plan_id == plan_id, Cycle.start_date <= today)
        .order_by(Cycle.start_date.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


@router.get("/current", response_model=PlanCurrentOut)
async def plan_current(
    athlete: Athlete = Depends(get_current_athlete),
    db: AsyncSession = Depends(get_db),
):
    plan = await _active_plan(db, athlete.id)
    if plan is None:
        raise HTTPException(status_code=404, detail="No active plan")

    today = datetime.date.today()
    cycle = await _active_cycle(db, plan.id, today)

    cycle_out = CycleOut.model_validate(cycle) if cycle else None
    progress = None
    if cycle is not None:
        total_days = (cycle.end_date - cycle.start_date).days
        total_weeks = max(1, (total_days + 6) // 7)
        elapsed_days = (today - cycle.start_date).days
        current_week = min(total_weeks, max(1, (elapsed_days // 7) + 1))
        days_to_race = (cycle.race_date - today).days
        progress = CycleProgress(
            week=current_week, total_weeks=total_weeks, days_to_race=days_to_race
        )

    return PlanCurrentOut(
        plan_name=plan.name,
        plan_id=plan.id,
        active_cycle=cycle_out,
        cycle_progress=progress,
    )


@router.get("/today", response_model=TodayOut)
async def plan_today(
    athlete: Athlete = Depends(get_current_athlete),
    db: AsyncSession = Depends(get_db),
):
    today = datetime.date.today()
    plan = await _active_plan(db, athlete.id)
    workouts: list[PlannedWorkout] = []
    if plan is not None:
        result = await db.execute(
            select(PlannedWorkout)
            .join(Cycle, PlannedWorkout.cycle_id == Cycle.id)
            .where(Cycle.plan_id == plan.id, PlannedWorkout.scheduled_date == today)
            .order_by(PlannedWorkout.scheduled_date)
        )
        workouts = list(result.scalars().all())

    return TodayOut(
        date=today,
        workouts=[PlannedWorkoutOut.model_validate(w) for w in workouts],
        coach_brief=None,
    )


@router.get("/week", response_model=WeekOut)
async def plan_week(
    date: datetime.date | None = Query(default=None),
    athlete: Athlete = Depends(get_current_athlete),
    db: AsyncSession = Depends(get_db),
):
    target = date or datetime.date.today()
    # Monday of the week
    week_start = target - datetime.timedelta(days=target.weekday())
    week_end = week_start + datetime.timedelta(days=6)

    plan = await _active_plan(db, athlete.id)
    workouts: list[PlannedWorkout] = []
    if plan is not None:
        result = await db.execute(
            select(PlannedWorkout)
            .join(Cycle, PlannedWorkout.cycle_id == Cycle.id)
            .where(
                Cycle.plan_id == plan.id,
                PlannedWorkout.scheduled_date >= week_start,
                PlannedWorkout.scheduled_date <= week_end,
            )
            .order_by(PlannedWorkout.scheduled_date)
        )
        workouts = list(result.scalars().all())

    # Build 7 days
    days = []
    for i in range(7):
        d = week_start + datetime.timedelta(days=i)
        day_workouts = [
            PlannedWorkoutOut.model_validate(w) for w in workouts if w.scheduled_date == d
        ]
        days.append(DayWorkouts(date=d, workouts=day_workouts))

    return WeekOut(week_start=week_start, days=days)


@router.get("/full", response_model=PlanFullOut)
async def plan_full(
    athlete: Athlete = Depends(get_current_athlete),
    db: AsyncSession = Depends(get_db),
):
    return await build_plan_full(db, athlete.id)


@router.get("/stats", response_model=PlanStatsOut)
async def plan_stats(
    scope: str = "cycle",
    athlete: Athlete = Depends(get_current_athlete),
    db: AsyncSession = Depends(get_db),
):
    if scope not in ("cycle", "plan"):
        raise HTTPException(status_code=400, detail="scope must be 'cycle' or 'plan'")
    return await build_plan_stats(db, athlete.id, scope=scope)  # type: ignore[arg-type]
