from __future__ import annotations

import datetime
import time
import uuid
from dataclasses import asdict
from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import get_current_athlete, get_db
from app.models.athlete import Athlete
from app.models.plan import Cycle, Plan
from app.models.reconciliation import Reconciliation
from app.models.workout import CompletedWorkout, PlannedWorkout, WorkoutStatus, WorkoutType
from app.schemas.plan import (
    CycleOut,
    CycleProgress,
    DayWorkouts,
    PlanCurrentOut,
    PlanFullOut,
    PlannedActualOut,
    PlannedWorkoutOut,
    PlanStatsOut,
    StartDateImpact,
    StartDateRequest,
    StartDateResponse,
    TodayOut,
    WeekOut,
)
from app.services.cache_invalidation import invalidate_for_athlete
from app.services.coach_brief import compose_coach_brief
from app.services.plan_aggregator import build_plan_full, build_plan_stats
from app.services.plan_reseed import apply_reseed, compute_reseed_impact

router = APIRouter(prefix="/plan", tags=["plan"])


# 60s per-athlete cache for the heuristic coach brief on /plan/today.
# Cleared by cache_invalidation umbrella on any athlete-state mutation.
_COACH_BRIEF_CACHE: dict[uuid.UUID, tuple[float, str | None]] = {}
_COACH_BRIEF_TTL_S = 60.0


def _clear_coach_brief_cache(athlete_id: uuid.UUID) -> None:
    _COACH_BRIEF_CACHE.pop(athlete_id, None)


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


async def _build_plan_current(db: AsyncSession, athlete_id: UUID) -> PlanCurrentOut | None:
    """Build the PlanCurrentOut payload, or None if there's no active plan."""
    plan = await _active_plan(db, athlete_id)
    if plan is None:
        return None

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


@router.get("/current", response_model=PlanCurrentOut)
async def plan_current(
    athlete: Athlete = Depends(get_current_athlete),
    db: AsyncSession = Depends(get_db),
):
    payload = await _build_plan_current(db, athlete.id)
    if payload is None:
        raise HTTPException(status_code=404, detail="No active plan")
    return payload


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

    # Coach brief — heuristic, 60s per-athlete cache.
    cached = _COACH_BRIEF_CACHE.get(athlete.id)
    now = time.monotonic()
    if cached is not None and now - cached[0] < _COACH_BRIEF_TTL_S:
        brief = cached[1]
    else:
        brief = await _build_coach_brief(db, athlete, plan, workouts, today)
        _COACH_BRIEF_CACHE[athlete.id] = (time.monotonic(), brief)

    return TodayOut(
        date=today,
        workouts=[PlannedWorkoutOut.model_validate(w) for w in workouts],
        coach_brief=brief,
    )


async def _build_coach_brief(
    db: AsyncSession,
    athlete: Athlete,
    plan: Plan | None,
    workouts: list[PlannedWorkout],
    today: datetime.date,
) -> str | None:
    """Assemble inputs and call ``compose_coach_brief``.

    Pulls yesterday's matched completion, last-5-day adherence, and the
    active cycle's race info. Returns the brief string or ``None``.
    """
    yesterday = today - datetime.timedelta(days=1)
    yesterday_completion: CompletedWorkout | None = None
    days_to_race: int | None = None
    race_name: str | None = None
    last_5_days_adherence: float | None = None

    if plan is not None:
        # Yesterday's completion via reconciliation
        result = await db.execute(
            select(CompletedWorkout)
            .join(Reconciliation, Reconciliation.completed_id == CompletedWorkout.id)
            .join(PlannedWorkout, Reconciliation.planned_id == PlannedWorkout.id)
            .join(Cycle, PlannedWorkout.cycle_id == Cycle.id)
            .where(
                Cycle.plan_id == plan.id,
                PlannedWorkout.scheduled_date == yesterday,
            )
            .order_by(CompletedWorkout.started_at.desc())
            .limit(1)
        )
        yesterday_completion = result.scalar_one_or_none()

        # Last 5 days' adherence: ratio of done-or-moved over scheduled
        # non-rest planned rows in [today-5, today-1].
        window_start = today - datetime.timedelta(days=5)
        adh_result = await db.execute(
            select(PlannedWorkout)
            .join(Cycle, PlannedWorkout.cycle_id == Cycle.id)
            .where(
                Cycle.plan_id == plan.id,
                PlannedWorkout.scheduled_date >= window_start,
                PlannedWorkout.scheduled_date <= yesterday,
                PlannedWorkout.type != WorkoutType.rest,
            )
        )
        adh_rows = list(adh_result.scalars().all())
        if adh_rows:
            done = sum(
                1 for r in adh_rows if r.status in (WorkoutStatus.done, WorkoutStatus.moved)
            )
            last_5_days_adherence = done / len(adh_rows)

        # Active cycle for race info
        cycle = await _active_cycle(db, plan.id, today)
        if cycle is not None:
            race_name = cycle.race_name
            days_to_race = (cycle.race_date - today).days

    return compose_coach_brief(
        today=today,
        todays_workouts=workouts,
        yesterday_completion=yesterday_completion,
        days_to_race=days_to_race,
        last_5_days_adherence=last_5_days_adherence,
        race_name=race_name,
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

    # For done workouts: pull matched CompletedWorkout via Reconciliation so
    # the WorkoutCard can render actuals instead of planned values.
    # Empty workouts → empty map; safe.
    completed_by_planned_id: dict[uuid.UUID, CompletedWorkout] = {}
    if workouts:
        planned_ids = [w.id for w in workouts]
        recon_rows = (
            await db.execute(
                select(Reconciliation, CompletedWorkout)
                .join(CompletedWorkout, Reconciliation.completed_id == CompletedWorkout.id)
                .where(
                    Reconciliation.athlete_id == athlete.id,
                    Reconciliation.planned_id.in_(planned_ids),
                )
            )
        ).all()
        for recon, completed in recon_rows:
            if recon.planned_id is not None:
                completed_by_planned_id[recon.planned_id] = completed

    def _build_out(w: PlannedWorkout) -> PlannedWorkoutOut:
        out = PlannedWorkoutOut.model_validate(w)
        cw = completed_by_planned_id.get(w.id)
        if cw is not None:
            distance_mi: Decimal | None = None
            if cw.distance_m is not None:
                # meters → miles (1609.344 m/mi); quantize to 2dp for display stability
                distance_mi = (cw.distance_m / Decimal("1609.344")).quantize(Decimal("0.01"))
            out.actual = PlannedActualOut(
                distance_mi=distance_mi,
                duration_s=cw.duration_s,
                started_at=cw.started_at,
            )
        return out

    # Build 7 days
    days = []
    for i in range(7):
        d = week_start + datetime.timedelta(days=i)
        day_workouts = [_build_out(w) for w in workouts if w.scheduled_date == d]
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


@router.post("/start-date", response_model=StartDateResponse)
async def update_start_date(
    body: StartDateRequest,
    dry_run: bool = Query(default=False),
    athlete: Athlete = Depends(get_current_athlete),
    db: AsyncSession = Depends(get_db),
):
    """Reseed the plan to a new Cycle 1 start date (Session 2.7 Phase 0 Q0.1).

    With ``?dry_run=true`` returns the impact preview only — no DB writes.
    Otherwise applies the reseed: drops Cycle-1 incomplete planned/moved
    rows (and any pre-new-start done/skipped), re-emits a fresh Cycle 1
    from PLAN.md anchored at ``new_start_date``, discards pending agent
    proposals, writes a ``plan_history`` row, and busts athlete caches.
    """
    if body.new_start_date < datetime.date.today():
        raise HTTPException(status_code=400, detail="new_start_date must be today or later")

    if dry_run:
        impact = await compute_reseed_impact(db, athlete.id, body.new_start_date)
        return StartDateResponse(
            dry_run=True,
            impact=StartDateImpact(**asdict(impact)),
            plan=None,
        )

    impact = await apply_reseed(db, athlete.id, body.new_start_date)
    invalidate_for_athlete(athlete.id)

    plan_view = await _build_plan_current(db, athlete.id)
    return StartDateResponse(
        dry_run=False,
        impact=StartDateImpact(**asdict(impact)),
        plan=plan_view,
    )
