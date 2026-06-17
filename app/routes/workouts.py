from __future__ import annotations

import re
import time
import uuid
from datetime import datetime, timedelta
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

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
from app.schemas.strava import CandidateOut, LinkCompletedRequest
from app.schemas.workout import (
    CompletedWorkoutOut,
    LogCompletedRequest,
    LogCompletedResponse,
    ReconciliationOut,
    WorkoutDetailOut,
)
from app.services.agents.plan_adapter import propose_rebalance
from app.services.cache_invalidation import invalidate_for_athlete
from app.services.proposal_apply import (
    ProposalApplyError,
    ProposalNotFound,
    apply_proposal,
)
from app.services.strava.client import get_strava_client  # noqa: F401  (patched in tests)
from app.services.strava.sync import StravaSyncService

_PACE_RE = re.compile(r"^(\d{1,2}):(\d{2})$")


def _parse_pace_to_s_per_km(pace_str: str) -> int:
    m = _PACE_RE.match(pace_str)
    if not m:
        raise HTTPException(status_code=400, detail="avg_pace_str must be mm:ss")
    s_per_mi = int(m.group(1)) * 60 + int(m.group(2))
    return round(s_per_mi / 1.609344)


def _activity_type_for(family: WorkoutFamily) -> str:
    return {
        WorkoutFamily.running: "running",
        WorkoutFamily.strength: "strength_training",
        WorkoutFamily.other: "other",
    }[family]


def _format_pace_from_completed(cw: CompletedWorkout) -> str | None:
    if cw.avg_pace_s_per_km is None:
        return None
    s_per_mi = round(cw.avg_pace_s_per_km * 1.609344)
    return f"{s_per_mi // 60}:{s_per_mi % 60:02d}"


router = APIRouter(prefix="/workouts", tags=["workouts"])


# 60s in-process per-athlete cache for the "recent completed" endpoint.
# Keyed by (athlete_id, limit). Cleared by cache_invalidation umbrella on
# any athlete-state mutation (log-completed, edit, move, etc.).
_RECENT_COMPLETED_CACHE: dict[tuple[uuid.UUID, int], tuple[float, list[dict]]] = {}
_RECENT_TTL_S = 60.0


def _clear_recent_completed_cache(athlete_id: uuid.UUID) -> None:
    keys = [k for k in _RECENT_COMPLETED_CACHE if k[0] == athlete_id]
    for k in keys:
        _RECENT_COMPLETED_CACHE.pop(k, None)


@router.get("/completed/recent", response_model=list[CompletedWorkoutOut])
async def recent_completed(
    limit: int = 5,
    athlete: Athlete = Depends(get_current_athlete),
    db: AsyncSession = Depends(get_db),
):
    limit = max(1, min(limit, 50))
    key = (athlete.id, limit)
    cached = _RECENT_COMPLETED_CACHE.get(key)
    now = time.monotonic()
    if cached is not None and now - cached[0] < _RECENT_TTL_S:
        return cached[1]

    result = await db.execute(
        select(CompletedWorkout)
        .where(CompletedWorkout.athlete_id == athlete.id)
        .order_by(CompletedWorkout.started_at.desc())
        .limit(limit)
    )
    rows = result.scalars().all()
    serialized = [CompletedWorkoutOut.model_validate(r).model_dump(mode="json") for r in rows]
    _RECENT_COMPLETED_CACHE[key] = (time.monotonic(), serialized)
    return serialized


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
    if "description_md" in updates:
        planned.description_md = updates["description_md"]
    if "intent_md" in updates:
        planned.intent_md = updates["intent_md"]

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
    # 1. Workout 404 check (preserves the route's existing contract).
    result = await db.execute(
        select(PlannedWorkout)
        .join(Cycle, PlannedWorkout.cycle_id == Cycle.id)
        .join(Plan, Cycle.plan_id == Plan.id)
        .where(PlannedWorkout.id == workout_id, Plan.athlete_id == athlete.id)
    )
    if result.scalar_one_or_none() is None:
        raise HTTPException(status_code=404, detail="Workout not found")

    # 2. Delegate apply/cancel to the shared service (ownership re-validated within).
    try:
        await apply_proposal(db, athlete.id, body.proposal_id, body.choice)
    except ProposalNotFound:
        raise HTTPException(status_code=404, detail="Proposal not found") from None
    except ProposalApplyError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

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


@router.post("/{workout_id}/log-completed", response_model=LogCompletedResponse)
async def log_completed(
    workout_id: uuid.UUID,
    body: LogCompletedRequest,
    athlete: Athlete = Depends(get_current_athlete),
    db: AsyncSession = Depends(get_db),
):
    """Manually mark a planned workout as completed.

    Used when the user logs a workout that was not synced from Garmin
    (e.g. treadmill run, strength session, missed-sync). Creates a
    CompletedWorkout (with garmin_activity_id=NULL) and a Reconciliation
    row at confidence 1.0, and flips the planned workout to status=done.
    """
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
            detail=f"Cannot log a {planned.status.value} workout",
        )

    # Pace handling: explicit string takes precedence; else derive from
    # distance + duration if both present; else None (e.g. strength).
    if body.avg_pace_str is not None:
        avg_pace_s_per_km: int | None = _parse_pace_to_s_per_km(body.avg_pace_str)
    elif body.distance_mi is not None and body.distance_mi > 0:
        distance_km = body.distance_mi * 1.609344
        avg_pace_s_per_km = round((body.duration_min * 60) / distance_km)
    else:
        avg_pace_s_per_km = None

    distance_m = (
        Decimal(str(round(body.distance_mi * 1609.344, 2)))
        if body.distance_mi is not None
        else None
    )

    completed = CompletedWorkout(
        athlete_id=athlete.id,
        garmin_activity_id=None,
        activity_date=planned.scheduled_date,
        started_at=datetime.combine(planned.scheduled_date, datetime.min.time()),
        activity_type=_activity_type_for(planned.family),
        family=planned.family,
        duration_s=body.duration_min * 60,
        distance_m=distance_m,
        avg_hr=body.avg_hr,
        max_hr=None,
        avg_pace_s_per_km=avg_pace_s_per_km,
        elevation_gain_m=None,
        calories=None,
        raw_summary_json={"source": "manual_log"},
    )
    db.add(completed)
    await db.flush()

    recon = Reconciliation(
        athlete_id=athlete.id,
        planned_id=planned.id,
        completed_id=completed.id,
        match_confidence=Decimal("1.0"),
        deviation_notes_md=body.notes or "",
        agent_review_md=None,
        agent_reviewed_at=None,
    )
    db.add(recon)

    planned.status = WorkoutStatus.done

    await db.commit()
    await db.refresh(planned)
    await db.refresh(completed)
    await db.refresh(recon)

    invalidate_for_athlete(athlete.id)

    return LogCompletedResponse(
        planned=PlannedWorkoutOut.model_validate(planned),
        completed=CompletedWorkoutOut.model_validate(completed),
        reconciliation=ReconciliationOut.model_validate(recon),
    )


@router.get("/{workout_id}/strava-candidates", response_model=list[CandidateOut])
async def strava_candidates(
    workout_id: uuid.UUID,
    athlete: Athlete = Depends(get_current_athlete),
    db: AsyncSession = Depends(get_db),
):
    planned = (
        await db.execute(
            select(PlannedWorkout)
            .join(Cycle, PlannedWorkout.cycle_id == Cycle.id)
            .join(Plan, Cycle.plan_id == Plan.id)
            .where(PlannedWorkout.id == workout_id, Plan.athlete_id == athlete.id)
        )
    ).scalar_one_or_none()
    if planned is None:
        raise HTTPException(status_code=404, detail="Workout not found")

    # Capture scalar values before sync; a session error in sync should not
    # prevent the candidate query from running.
    scheduled_date = planned.scheduled_date
    athlete_id = athlete.id

    try:
        await StravaSyncService(db, athlete_id).sync()
    except Exception:  # noqa: BLE001
        # C2: expunge any pending (un-committed) objects so the candidate SELECT
        # can auto-flush cleanly. We avoid a full rollback because that would
        # expire all loaded ORM objects in the same session.
        for obj in list(db.new):
            db.expunge(obj)

    linked_ids = select(Reconciliation.completed_id).where(
        Reconciliation.completed_id.is_not(None)
    )
    lo = scheduled_date - timedelta(days=7)
    hi = scheduled_date + timedelta(days=7)
    rows = (
        (
            await db.execute(
                select(CompletedWorkout).where(
                    CompletedWorkout.athlete_id == athlete_id,
                    CompletedWorkout.activity_date >= lo,
                    CompletedWorkout.activity_date <= hi,
                    CompletedWorkout.id.not_in(linked_ids),
                )
            )
        )
        .scalars()
        .all()
    )
    rows.sort(key=lambda cw: abs((cw.activity_date - scheduled_date).days))
    rows = rows[:5]

    return [
        CandidateOut(
            completed_id=cw.id,
            activity_date=cw.activity_date,
            activity_type=cw.activity_type,
            distance_mi=round(float(cw.distance_m) / 1609.344, 2) if cw.distance_m else None,
            duration_min=round(cw.duration_s / 60),
            avg_pace_str=_format_pace_from_completed(cw),
            source=cw.source,
        )
        for cw in rows
    ]


@router.post("/{workout_id}/link-completed", response_model=LogCompletedResponse)
async def link_completed(
    workout_id: uuid.UUID,
    body: LinkCompletedRequest,
    athlete: Athlete = Depends(get_current_athlete),
    db: AsyncSession = Depends(get_db),
):
    planned = (
        await db.execute(
            select(PlannedWorkout)
            .join(Cycle, PlannedWorkout.cycle_id == Cycle.id)
            .join(Plan, Cycle.plan_id == Plan.id)
            .where(PlannedWorkout.id == workout_id, Plan.athlete_id == athlete.id)
        )
    ).scalar_one_or_none()
    if planned is None:
        raise HTTPException(status_code=404, detail="Workout not found")
    if planned.status in (WorkoutStatus.done, WorkoutStatus.skipped):
        raise HTTPException(
            status_code=409, detail=f"Cannot link a {planned.status.value} workout"
        )

    completed = (
        await db.execute(
            select(CompletedWorkout).where(
                CompletedWorkout.id == body.completed_id,
                CompletedWorkout.athlete_id == athlete.id,
            )
        )
    ).scalar_one_or_none()
    if completed is None:
        raise HTTPException(status_code=404, detail="Completed workout not found")

    already = (
        await db.execute(
            select(Reconciliation).where(Reconciliation.completed_id == completed.id)
        )
    ).scalar_one_or_none()
    if already is not None:
        raise HTTPException(status_code=409, detail="Activity already linked")

    recon = Reconciliation(
        athlete_id=athlete.id,
        planned_id=planned.id,
        completed_id=completed.id,
        match_confidence=Decimal("1.0"),
    )
    db.add(recon)
    planned.status = WorkoutStatus.done
    await db.commit()
    await db.refresh(planned)
    await db.refresh(completed)
    await db.refresh(recon)

    invalidate_for_athlete(athlete.id)

    return LogCompletedResponse(
        planned=PlannedWorkoutOut.model_validate(planned),
        completed=CompletedWorkoutOut.model_validate(completed),
        reconciliation=ReconciliationOut.model_validate(recon),
    )
