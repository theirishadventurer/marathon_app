from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import get_current_athlete, get_db
from app.models.athlete import Athlete
from app.models.plan import Cycle, Plan
from app.models.reconciliation import Reconciliation
from app.models.workout import CompletedWorkout, PlannedWorkout
from app.schemas.plan import PlannedWorkoutOut
from app.schemas.workout import (
    CompletedWorkoutOut,
    ReconciliationOut,
    WorkoutDetailOut,
)

router = APIRouter(prefix="/workouts", tags=["workouts"])


@router.get("/{workout_id}", response_model=WorkoutDetailOut)
async def workout_detail(
    workout_id: uuid.UUID,
    athlete: Athlete = Depends(get_current_athlete),
    db: AsyncSession = Depends(get_db),
):
    # Find planned workout and verify it belongs to this athlete
    result = await db.execute(
        select(PlannedWorkout)
        .join(Cycle, PlannedWorkout.cycle_id == Cycle.id)
        .join(Plan, Cycle.plan_id == Plan.id)
        .where(PlannedWorkout.id == workout_id, Plan.athlete_id == athlete.id)
    )
    planned = result.scalar_one_or_none()
    if planned is None:
        raise HTTPException(status_code=404, detail="Workout not found")

    # Look for reconciliation
    result = await db.execute(
        select(Reconciliation).where(Reconciliation.planned_id == planned.id)
    )
    recon = result.scalar_one_or_none()

    completed = None
    if recon is not None and recon.completed_id is not None:
        result = await db.execute(
            select(CompletedWorkout).where(CompletedWorkout.id == recon.completed_id)
        )
        completed = result.scalar_one_or_none()

    return WorkoutDetailOut(
        planned=PlannedWorkoutOut.model_validate(planned),
        completed=CompletedWorkoutOut.model_validate(completed) if completed else None,
        reconciliation=ReconciliationOut.model_validate(recon) if recon else None,
    )
