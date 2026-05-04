from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.plan import Cycle, Plan
from app.models.reconciliation import Reconciliation
from app.models.workout import (
    CompletedWorkout,
    PlannedWorkout,
    WorkoutStatus,
)

MI_TO_M = Decimal("1609.34")


async def reconcile(db: AsyncSession, athlete_id) -> dict[str, Any]:
    """Match completed workouts to planned workouts by date + family."""
    matched = 0
    bonus = 0
    skipped = 0

    # ── 1. Find all unmatched completed workouts ──────────────────────
    existing_completed_ids = (
        select(Reconciliation.completed_id)
        .where(Reconciliation.completed_id.is_not(None))
    )
    unmatched_completed = (
        await db.execute(
            select(CompletedWorkout)
            .where(
                CompletedWorkout.athlete_id == athlete_id,
                CompletedWorkout.id.not_in(existing_completed_ids),
            )
        )
    ).scalars().all()

    # ── 2. For each unmatched completed workout, find candidates ──────
    for cw in unmatched_completed:
        # Subquery: planned_ids that already have a reconciliation
        reconciled_planned_ids = (
            select(Reconciliation.planned_id)
            .where(Reconciliation.planned_id.is_not(None))
        )

        # Find candidate planned workouts via join to cycle -> plan
        candidates_q = (
            select(PlannedWorkout)
            .join(Cycle, PlannedWorkout.cycle_id == Cycle.id)
            .join(Plan, Cycle.plan_id == Plan.id)
            .where(
                Plan.athlete_id == athlete_id,
                PlannedWorkout.scheduled_date == cw.activity_date,
                PlannedWorkout.family == cw.family,
                PlannedWorkout.status.in_([WorkoutStatus.planned, WorkoutStatus.moved]),
                PlannedWorkout.id.not_in(reconciled_planned_ids),
            )
        )
        candidates: list[PlannedWorkout] = list(
            (await db.execute(candidates_q)).scalars().all()
        )

        if len(candidates) == 0:
            # Bonus / unscheduled run
            db.add(Reconciliation(
                athlete_id=athlete_id,
                planned_id=None,
                completed_id=cw.id,
                match_confidence=None,
            ))
            bonus += 1

        elif len(candidates) == 1:
            pw = candidates[0]
            db.add(Reconciliation(
                athlete_id=athlete_id,
                planned_id=pw.id,
                completed_id=cw.id,
                match_confidence=Decimal("1.00"),
            ))
            pw.status = WorkoutStatus.done
            matched += 1

        else:
            # 2+ matches: pick closest by distance, fall back to duration
            best = _pick_best_candidate(candidates, cw)
            db.add(Reconciliation(
                athlete_id=athlete_id,
                planned_id=best.id,
                completed_id=cw.id,
                match_confidence=Decimal("0.70"),
            ))
            best.status = WorkoutStatus.done
            matched += 1

    # ── 3. Detect skipped workouts ────────────────────────────────────
    yesterday = date.today() - timedelta(days=1)
    reconciled_planned_ids_2 = (
        select(Reconciliation.planned_id)
        .where(Reconciliation.planned_id.is_not(None))
    )
    skipped_q = (
        select(PlannedWorkout)
        .join(Cycle, PlannedWorkout.cycle_id == Cycle.id)
        .join(Plan, Cycle.plan_id == Plan.id)
        .where(
            Plan.athlete_id == athlete_id,
            PlannedWorkout.scheduled_date < yesterday,
            PlannedWorkout.status.in_([WorkoutStatus.planned, WorkoutStatus.moved]),
            PlannedWorkout.id.not_in(reconciled_planned_ids_2),
        )
    )
    skipped_workouts: list[PlannedWorkout] = list(
        (await db.execute(skipped_q)).scalars().all()
    )
    for pw in skipped_workouts:
        db.add(Reconciliation(
            athlete_id=athlete_id,
            planned_id=pw.id,
            completed_id=None,
            match_confidence=None,
        ))
        pw.status = WorkoutStatus.skipped
        skipped += 1

    await db.flush()
    return {"matched": matched, "bonus": bonus, "skipped": skipped}


def _pick_best_candidate(
    candidates: list[PlannedWorkout],
    completed: CompletedWorkout,
) -> PlannedWorkout:
    """Pick the candidate closest by distance; fall back to duration."""
    completed_m = completed.distance_m

    if completed_m is not None:
        def dist_delta(pw: PlannedWorkout) -> Decimal:
            if pw.distance_mi is not None:
                return abs(pw.distance_mi * MI_TO_M - completed_m)
            return Decimal("999999")
        return min(candidates, key=dist_delta)

    # Fallback: duration
    completed_min = completed.duration_s / 60

    def dur_delta(pw: PlannedWorkout) -> float:
        if pw.duration_min is not None:
            return abs(pw.duration_min - completed_min)
        return 999999.0

    return min(candidates, key=dur_delta)
