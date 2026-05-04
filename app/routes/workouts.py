from __future__ import annotations

import uuid
from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

from app.deps import get_current_athlete, get_db
from app.models.agent import AgentMessage
from app.models.athlete import Athlete
from app.models.plan import Cycle, Plan
from app.models.reconciliation import Reconciliation
from app.models.workout import CompletedWorkout, PlannedWorkout, WorkoutStatus
from app.schemas.move import ApplyMoveRequest, MoveRequest, ProposalOut
from app.schemas.plan import PlannedWorkoutOut
from app.schemas.workout import (
    CompletedWorkoutOut,
    ReconciliationOut,
    WorkoutDetailOut,
)
from app.services.agents.plan_adapter import propose_rebalance

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


@router.patch("/{workout_id}/skip")
async def skip_workout(
    workout_id: uuid.UUID,
    athlete: Athlete = Depends(get_current_athlete),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(PlannedWorkout)
        .join(Cycle, PlannedWorkout.cycle_id == Cycle.id)
        .join(Plan, Cycle.plan_id == Plan.id)
        .where(PlannedWorkout.id == workout_id, Plan.athlete_id == athlete.id)
    )
    planned = result.scalar_one_or_none()
    if planned is None:
        raise HTTPException(status_code=404, detail="Workout not found")

    planned.status = WorkoutStatus.skipped
    await db.commit()
    return {"ok": True}


@router.patch("/{workout_id}/move", response_model=ProposalOut)
async def move_workout(
    workout_id: uuid.UUID,
    body: MoveRequest,
    athlete: Athlete = Depends(get_current_athlete),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(PlannedWorkout)
        .join(Cycle, PlannedWorkout.cycle_id == Cycle.id)
        .join(Plan, Cycle.plan_id == Plan.id)
        .where(PlannedWorkout.id == workout_id, Plan.athlete_id == athlete.id)
    )
    planned = result.scalar_one_or_none()
    if planned is None:
        raise HTTPException(status_code=404, detail="Workout not found")

    proposal = await propose_rebalance(db, athlete.id, workout_id, body.new_date)
    return ProposalOut(**proposal)


@router.post("/{workout_id}/apply-move")
async def apply_move(
    workout_id: uuid.UUID,
    body: ApplyMoveRequest,
    athlete: Athlete = Depends(get_current_athlete),
    db: AsyncSession = Depends(get_db),
):
    # 1. Find the workout
    result = await db.execute(
        select(PlannedWorkout)
        .join(Cycle, PlannedWorkout.cycle_id == Cycle.id)
        .join(Plan, Cycle.plan_id == Plan.id)
        .where(PlannedWorkout.id == workout_id, Plan.athlete_id == athlete.id)
    )
    planned = result.scalar_one_or_none()
    if planned is None:
        raise HTTPException(status_code=404, detail="Workout not found")

    # 2. Find the AgentMessage with matching proposal
    result = await db.execute(
        select(AgentMessage).where(
            AgentMessage.related_workout_id == workout_id,
            AgentMessage.proposal_state_json["proposal_id"].as_string()
            == str(body.proposal_id),
        )
    )
    msg = result.scalar_one_or_none()
    if msg is None:
        raise HTTPException(status_code=404, detail="Proposal not found")

    proposal = msg.proposal_state_json
    choice = body.choice

    if choice == "cancel":
        proposal["state"] = "discarded"
        flag_modified(msg, "proposal_state_json")
        await db.commit()
        return {"ok": True}

    # For just_move, option_a, option_b: move the primary workout
    new_date = date.fromisoformat(proposal["new_date"])
    planned.scheduled_date = new_date
    planned.status = WorkoutStatus.moved

    if choice == "just_move":
        proposal["state"] = "applied"
        proposal["applied_choice"] = "just_move"
        flag_modified(msg, "proposal_state_json")
        await db.commit()
        return {"ok": True}

    if choice not in ("option_a", "option_b"):
        raise HTTPException(status_code=400, detail="Invalid choice")

    # Find the chosen option
    chosen = None
    for opt in proposal.get("options", []):
        if opt["id"] == choice:
            chosen = opt
            break
    if chosen is None:
        raise HTTPException(status_code=400, detail="Option not found in proposal")

    # Apply edits from the chosen option
    for edit in chosen.get("edits", []):
        edit_workout_id = uuid.UUID(edit["workout_id"])
        field = edit["field"]
        value = edit["new_value"]

        if field not in ("scheduled_date", "status"):
            raise HTTPException(
                status_code=400, detail=f"Invalid edit field: {field}"
            )

        # Find the target workout and verify it belongs to this athlete
        result = await db.execute(
            select(PlannedWorkout)
            .join(Cycle, PlannedWorkout.cycle_id == Cycle.id)
            .join(Plan, Cycle.plan_id == Plan.id)
            .where(
                PlannedWorkout.id == edit_workout_id,
                Plan.athlete_id == athlete.id,
            )
        )
        target = result.scalar_one_or_none()
        if target is None:
            raise HTTPException(
                status_code=400,
                detail=f"Workout {edit_workout_id} not found or not owned by athlete",
            )

        if field == "scheduled_date":
            target.scheduled_date = date.fromisoformat(value)
            target.status = WorkoutStatus.moved
        elif field == "status":
            valid_statuses = {"planned", "moved", "skipped"}
            if value not in valid_statuses:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid status value: {value}",
                )
            target.status = WorkoutStatus(value)

    proposal["state"] = "applied"
    proposal["applied_choice"] = choice
    flag_modified(msg, "proposal_state_json")
    await db.commit()
    return {"ok": True}
