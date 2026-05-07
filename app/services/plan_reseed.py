"""Reseed-mode start-date support for the active marathon plan.

Per Session 2.7 Phase 0 decision (Q0.1, Option β), shifting the plan start
date does NOT preserve previously-planned-but-undone workouts via a delta
shift. Instead Cycle 1 is re-emitted from a new anchor: completed/done/skipped
rows in range survive, but planned/moved rows in Cycle 1 are dropped and a
fresh template slice is laid down.

This module exposes two functions consumed by the route layer:

* ``compute_reseed_impact`` — read-only preview (powers ``?dry_run=true``).
* ``apply_reseed`` — write path that mutates the DB and writes a
  ``plan_history`` row.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import date
from uuid import UUID

from sqlalchemy import delete, func, select, text
from sqlalchemy.exc import NoResultFound
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

from app.lib.workout_family import family_for_planned
from app.models.agent import AgentMessage
from app.models.plan import Cycle, Plan
from app.models.plan_history import PlanHistory
from app.models.workout import (
    CompletedWorkout,
    PlannedWorkout,
    WorkoutStatus,
    WorkoutType,
)
from app.seed.plan_parser import parse_plan

PLAN_PATH = "PLAN.md"


@dataclass
class ReseedImpact:
    """Counts produced by a reseed preview or apply.

    All counts are non-negative integers; dates describe the new cycle 1 layout.
    """

    completed_kept: int
    completed_dropped: int
    done_planned_kept: int
    skipped_planned_kept: int
    planned_dropped: int
    proposals_discarded: int
    new_cycle1_weeks: int
    new_cycle1_start: date
    new_cycle1_end: date


async def _active_plan(db: AsyncSession, athlete_id: UUID) -> Plan:
    plan = (
        await db.execute(
            select(Plan).where(Plan.athlete_id == athlete_id, Plan.is_active.is_(True)).limit(1)
        )
    ).scalar_one_or_none()
    if plan is None:
        raise NoResultFound(f"no active plan for athlete {athlete_id}")
    return plan


async def _cycle_one(db: AsyncSession, plan_id: UUID) -> Cycle:
    cycle = (
        await db.execute(
            select(Cycle).where(Cycle.plan_id == plan_id, Cycle.sequence == 1).limit(1)
        )
    ).scalar_one_or_none()
    if cycle is None:
        raise NoResultFound(f"no cycle 1 for plan {plan_id}")
    return cycle


async def compute_reseed_impact(
    db: AsyncSession, athlete_id: UUID, new_start_date: date
) -> ReseedImpact:
    """Preview the effect of reseeding to ``new_start_date``. Read-only."""
    plan = await _active_plan(db, athlete_id)
    cycle1 = await _cycle_one(db, plan.id)

    last_race_date = plan.end_date

    # CompletedWorkout buckets — kept if activity_date in [new_start, last_race]
    completed_kept = (
        await db.execute(
            select(func.count())
            .select_from(CompletedWorkout)
            .where(
                CompletedWorkout.athlete_id == athlete_id,
                CompletedWorkout.activity_date >= new_start_date,
                CompletedWorkout.activity_date <= last_race_date,
            )
        )
    ).scalar() or 0
    completed_total = (
        await db.execute(
            select(func.count())
            .select_from(CompletedWorkout)
            .where(CompletedWorkout.athlete_id == athlete_id)
        )
    ).scalar() or 0
    completed_dropped = max(0, completed_total - completed_kept)

    # PlannedWorkout in Cycle 1: keep done/skipped >= new_start; drop planned/moved
    done_planned_kept = (
        await db.execute(
            select(func.count())
            .select_from(PlannedWorkout)
            .where(
                PlannedWorkout.cycle_id == cycle1.id,
                PlannedWorkout.status == WorkoutStatus.done,
                PlannedWorkout.scheduled_date >= new_start_date,
            )
        )
    ).scalar() or 0
    skipped_planned_kept = (
        await db.execute(
            select(func.count())
            .select_from(PlannedWorkout)
            .where(
                PlannedWorkout.cycle_id == cycle1.id,
                PlannedWorkout.status == WorkoutStatus.skipped,
                PlannedWorkout.scheduled_date >= new_start_date,
            )
        )
    ).scalar() or 0
    # Rows that will be deleted: planned/moved anywhere in cycle 1, plus
    # done/skipped rows whose scheduled_date is BEFORE new_start (they fall
    # out of the active program per Q0.1).
    planned_dropped = (
        await db.execute(
            select(func.count())
            .select_from(PlannedWorkout)
            .where(
                PlannedWorkout.cycle_id == cycle1.id,
                (
                    PlannedWorkout.status.in_([WorkoutStatus.planned, WorkoutStatus.moved])
                    | (PlannedWorkout.scheduled_date < new_start_date)
                ),
            )
        )
    ).scalar() or 0

    # Pending proposals discarded
    proposals_discarded = (
        await db.execute(
            select(func.count())
            .select_from(AgentMessage)
            .where(
                AgentMessage.athlete_id == athlete_id,
                text("proposal_state_json->>'state' = 'pending'"),
            )
        )
    ).scalar() or 0

    # New cycle 1 length from the parser (drives template slicing)
    parsed = parse_plan(PLAN_PATH, cycle_one_start_date=new_start_date)
    new_cycle1 = parsed["cycles"][0]
    week_numbers = sorted({w["week_number"] for w in new_cycle1["workouts"]})

    return ReseedImpact(
        completed_kept=int(completed_kept),
        completed_dropped=int(completed_dropped),
        done_planned_kept=int(done_planned_kept),
        skipped_planned_kept=int(skipped_planned_kept),
        planned_dropped=int(planned_dropped),
        proposals_discarded=int(proposals_discarded),
        new_cycle1_weeks=len(week_numbers),
        new_cycle1_start=new_cycle1["start_date"],
        new_cycle1_end=new_cycle1["end_date"],
    )


async def apply_reseed(db: AsyncSession, athlete_id: UUID, new_start_date: date) -> ReseedImpact:
    """Apply the reseed: delete out-of-range cycle-1 rows, emit fresh ones,
    discard pending proposals, write plan_history, update plan.start_date.
    Returns the resulting :class:`ReseedImpact`.
    """
    impact = await compute_reseed_impact(db, athlete_id, new_start_date)
    plan = await _active_plan(db, athlete_id)
    cycle1 = await _cycle_one(db, plan.id)

    old_start = cycle1.start_date

    # 1. Delete cycle-1 rows that should not survive:
    #    - any planned/moved (regardless of scheduled_date)
    #    - any done/skipped scheduled BEFORE the new start
    await db.execute(
        delete(PlannedWorkout).where(
            PlannedWorkout.cycle_id == cycle1.id,
            (
                PlannedWorkout.status.in_([WorkoutStatus.planned, WorkoutStatus.moved])
                | (PlannedWorkout.scheduled_date < new_start_date)
            ),
        )
    )

    # 2. Re-emit fresh planned_workouts for cycle 1 from the parser
    parsed = parse_plan(PLAN_PATH, cycle_one_start_date=new_start_date)
    new_cycle1_data = parsed["cycles"][0]
    cycle1.start_date = new_cycle1_data["start_date"]
    # end_date stays = race_date (unchanged) but mirror parser for safety
    cycle1.end_date = new_cycle1_data["end_date"]

    for w in new_cycle1_data["workouts"]:
        wtype = WorkoutType(w["type"])
        family = family_for_planned(wtype)
        db.add(
            PlannedWorkout(
                id=uuid.uuid4(),
                cycle_id=cycle1.id,
                scheduled_date=w["date"],
                original_date=w["date"],
                week_number=w["week_number"],
                type=wtype,
                family=family,
                status=WorkoutStatus.planned,
                duration_min=w["duration_min"],
                distance_mi=w["distance_mi"],
                title=w["title"],
                description_md=w["description_md"],
                intent_md=w["intent_md"],
            )
        )

    # 3. Update plan.start_date to track cycle 1
    plan.start_date = new_start_date

    # 4. Discard pending proposals
    pending = (
        (
            await db.execute(
                select(AgentMessage).where(
                    AgentMessage.athlete_id == athlete_id,
                    text("proposal_state_json->>'state' = 'pending'"),
                )
            )
        )
        .scalars()
        .all()
    )
    for msg in pending:
        state = dict(msg.proposal_state_json or {})
        state["state"] = "discarded"
        state["discard_reason"] = "plan_shifted"
        msg.proposal_state_json = state
        flag_modified(msg, "proposal_state_json")

    # 5. Write plan_history row
    db.add(
        PlanHistory(
            plan_id=plan.id,
            action="start_date_reseed",
            payload_json={
                "old_start": old_start.isoformat(),
                "new_start": new_start_date.isoformat(),
                "completed_kept": impact.completed_kept,
                "completed_dropped": impact.completed_dropped,
                "done_planned_kept": impact.done_planned_kept,
                "skipped_planned_kept": impact.skipped_planned_kept,
                "planned_dropped": impact.planned_dropped,
                "proposals_discarded": impact.proposals_discarded,
                "new_cycle1_weeks": impact.new_cycle1_weeks,
                "new_cycle1_start": impact.new_cycle1_start.isoformat(),
                "new_cycle1_end": impact.new_cycle1_end.isoformat(),
            },
        )
    )

    await db.commit()
    return impact
