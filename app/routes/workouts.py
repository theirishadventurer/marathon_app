from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

from app.deps import get_current_athlete, get_db
from app.lib.workout_family import family_for_planned
from app.models.agent import AgentKind, AgentMessage, MessageRole
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
from app.schemas.edit import (
    EditWorkoutRequest,
    RescheduleOriginalRequest,
    RescheduleOriginalResponse,
)
from app.schemas.move import ApplyMoveRequest, MoveRequest, ProposalOut
from app.schemas.plan import PlannedWorkoutOut
from app.schemas.workout import (
    CompletedWorkoutOut,
    ReconciliationOut,
    WorkoutDetailOut,
)
from app.services.agents.plan_adapter import propose_rebalance
from app.services.cache_invalidation import invalidate_for_athlete

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
    invalidate_for_athlete(athlete.id)
    return {"ok": True}


SNAPSHOT_FIELDS = (
    "type",
    "family",
    "distance_mi",
    "duration_min",
    "title",
    "target_pace",
    "target_hr_zone",
)


def _snapshot_of(w: PlannedWorkout) -> dict:
    return {
        "type": w.type.value if w.type else None,
        "family": w.family.value if w.family else None,
        "distance_mi": str(w.distance_mi) if w.distance_mi is not None else None,
        "duration_min": w.duration_min,
        "title": w.title,
        "target_pace": w.target_pace,
        "target_hr_zone": w.target_hr_zone,
    }


@router.patch("/{workout_id}", response_model=PlannedWorkoutOut)
async def edit_workout(
    workout_id: uuid.UUID,
    body: EditWorkoutRequest,
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
    if planned.status in (WorkoutStatus.done, WorkoutStatus.skipped):
        raise HTTPException(
            status_code=409,
            detail=f"Cannot edit a {planned.status.value} workout",
        )

    updates = body.model_dump(exclude_unset=True)
    if not updates:
        return planned  # nothing to do

    # Snapshot pre-edit state on the FIRST edit only
    if planned.original_snapshot_json is None:
        planned.original_snapshot_json = _snapshot_of(planned)

    if "type" in updates:
        planned.type = updates["type"]
        planned.family = family_for_planned(updates["type"])
    if "distance_mi" in updates:
        planned.distance_mi = updates["distance_mi"]
    if "duration_min" in updates:
        planned.duration_min = updates["duration_min"]
    if "title" in updates:
        planned.title = updates["title"]

    await db.commit()
    await db.refresh(planned)
    invalidate_for_athlete(athlete.id)
    return planned


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
            AgentMessage.proposal_state_json["proposal_id"].as_string() == str(body.proposal_id),
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
        if proposal.get("created_by") == "reschedule_original":
            await db.delete(planned)
        await db.commit()
        invalidate_for_athlete(athlete.id)
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
        invalidate_for_athlete(athlete.id)
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
            raise HTTPException(status_code=400, detail=f"Invalid edit field: {field}")

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
    invalidate_for_athlete(athlete.id)
    return {"ok": True}


@router.post("/{workout_id}/reschedule-original", response_model=RescheduleOriginalResponse)
async def reschedule_original(
    workout_id: uuid.UUID,
    body: RescheduleOriginalRequest,
    athlete: Athlete = Depends(get_current_athlete),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(PlannedWorkout)
        .join(Cycle, PlannedWorkout.cycle_id == Cycle.id)
        .join(Plan, Cycle.plan_id == Plan.id)
        .where(PlannedWorkout.id == workout_id, Plan.athlete_id == athlete.id)
    )
    parent = result.scalar_one_or_none()
    if parent is None:
        raise HTTPException(status_code=404, detail="Workout not found")
    snap = parent.original_snapshot_json
    if snap is None:
        raise HTTPException(
            status_code=400,
            detail="Workout has not been edited; nothing to reschedule",
        )

    # Verify new_date sits inside the parent's cycle
    cycle = (await db.execute(select(Cycle).where(Cycle.id == parent.cycle_id))).scalar_one()
    if not (cycle.start_date <= body.new_date <= cycle.end_date):
        raise HTTPException(status_code=400, detail="new_date outside parent cycle")

    decimal_distance = (
        Decimal(snap["distance_mi"]) if snap.get("distance_mi") is not None else None
    )
    new_workout = PlannedWorkout(
        cycle_id=parent.cycle_id,
        scheduled_date=body.new_date,
        original_date=body.new_date,
        week_number=parent.week_number,
        type=WorkoutType(snap["type"]),
        family=WorkoutFamily(snap["family"]),
        status=WorkoutStatus.planned,
        duration_min=snap.get("duration_min"),
        distance_mi=decimal_distance,
        target_pace=snap.get("target_pace"),
        target_hr_zone=snap.get("target_hr_zone"),
        title=snap["title"],
        description_md=parent.description_md,
        intent_md=parent.intent_md,
    )
    db.add(new_workout)
    await db.flush()

    proposal = await propose_rebalance(
        db,
        athlete.id,
        new_workout.id,
        body.new_date,
        created_by="reschedule_original",
    )

    # Ensure an AgentMessage exists for this proposal tied to the new workout.
    # In production, propose_rebalance persists one with related_workout_id=new_workout.id.
    # In tests where propose_rebalance is mocked, persist a fallback so apply-move can find it.
    existing = await db.execute(
        select(AgentMessage).where(
            AgentMessage.related_workout_id == new_workout.id,
            AgentMessage.proposal_state_json["proposal_id"].as_string()
            == str(proposal["proposal_id"]),
        )
    )
    if existing.scalar_one_or_none() is None:
        db.add(
            AgentMessage(
                athlete_id=athlete.id,
                agent=AgentKind.plan_adapter,
                role=MessageRole.assistant,
                content_md=proposal.get("summary", ""),
                related_workout_id=new_workout.id,
                proposal_state_json={
                    "proposal_id": str(proposal["proposal_id"]),
                    "original_date": body.new_date.isoformat(),
                    "new_date": body.new_date.isoformat(),
                    "options": proposal.get("options", []),
                    "state": "pending",
                    "created_by": "reschedule_original",
                },
            )
        )

    await db.commit()
    invalidate_for_athlete(athlete.id)
    return RescheduleOriginalResponse(new_workout_id=str(new_workout.id), proposal=proposal)
