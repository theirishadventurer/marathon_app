from __future__ import annotations

import uuid
from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

from app.models.agent import AgentMessage
from app.models.plan import Cycle, Plan
from app.models.workout import PlannedWorkout, WorkoutStatus


class ProposalNotFound(Exception):
    """Raised when no proposal matches the (proposal_id, athlete) pair (→ HTTP 404)."""


class ProposalApplyError(Exception):
    """Raised on an invalid choice/edit (→ HTTP 400)."""


async def _owned_workout(
    db: AsyncSession, athlete_id: uuid.UUID, workout_id: uuid.UUID
) -> PlannedWorkout | None:
    return (
        await db.execute(
            select(PlannedWorkout)
            .join(Cycle, PlannedWorkout.cycle_id == Cycle.id)
            .join(Plan, Cycle.plan_id == Plan.id)
            .where(PlannedWorkout.id == workout_id, Plan.athlete_id == athlete_id)
        )
    ).scalar_one_or_none()


async def apply_proposal(
    db: AsyncSession,
    athlete_id: uuid.UUID,
    proposal_id: uuid.UUID,
    choice: str,
) -> None:
    """Apply or cancel a proposal.

    Looks the proposal up by ``proposal_id`` scoped to the athlete via
    ``AgentMessage.athlete_id`` (NOT by workout_id — chat proposals have no
    workout-scoped route). Re-validates every edit's ``workout_id`` against the
    athlete before mutating — never trusts LLM-emitted IDs (spec §3.2).

    Drag proposals carry ``new_date`` + a primary ``related_workout_id``; for
    ``just_move`` and ``option_*`` the primary workout is moved to ``new_date``
    first (preserving the existing ``apply-move`` behavior). Chat proposals have
    no ``new_date``, so only the option's edits are applied.
    """
    msg = (
        await db.execute(
            select(AgentMessage).where(
                AgentMessage.athlete_id == athlete_id,
                AgentMessage.proposal_state_json["proposal_id"].as_string() == str(proposal_id),
            )
        )
    ).scalar_one_or_none()
    if msg is None:
        raise ProposalNotFound(f"Proposal {proposal_id} not found for athlete")

    proposal = msg.proposal_state_json
    related_id = msg.related_workout_id
    new_date_str = proposal.get("new_date")

    if choice == "cancel":
        proposal["state"] = "discarded"
        flag_modified(msg, "proposal_state_json")
        # reschedule_original cleanup parity: delete the orphaned shadow workout.
        if proposal.get("created_by") == "reschedule_original" and related_id is not None:
            orphan = await _owned_workout(db, athlete_id, related_id)
            if orphan is not None:
                await db.delete(orphan)
        await db.commit()
        return

    # Drag proposals: move the primary (related) workout to new_date first. This
    # runs for both just_move and option_* (matches the original apply-move).
    if new_date_str is not None and related_id is not None:
        primary = await _owned_workout(db, athlete_id, related_id)
        if primary is None:
            raise ProposalApplyError("Primary workout not found or not owned by athlete")
        primary.scheduled_date = date.fromisoformat(new_date_str)
        primary.status = WorkoutStatus.moved

    if choice == "just_move":
        if new_date_str is None or related_id is None:
            raise ProposalApplyError("just_move requires new_date + related workout")
        proposal["state"] = "applied"
        proposal["applied_choice"] = "just_move"
        flag_modified(msg, "proposal_state_json")
        await db.commit()
        return

    if choice not in ("option_a", "option_b"):
        raise ProposalApplyError(f"Invalid choice: {choice}")

    chosen = next((o for o in proposal.get("options", []) if o["id"] == choice), None)
    if chosen is None:
        raise ProposalApplyError("Option not found in proposal")

    for edit in chosen.get("edits", []):
        field = edit.get("field")
        if field not in ("scheduled_date", "status"):
            raise ProposalApplyError(f"Invalid edit field: {field}")
        try:
            edit_workout_id = uuid.UUID(edit["workout_id"])
        except (KeyError, ValueError) as e:
            raise ProposalApplyError("Invalid workout_id in edit") from e

        # SECURITY (§3.2): re-validate ownership before mutating. Never trust LLM IDs.
        target = await _owned_workout(db, athlete_id, edit_workout_id)
        if target is None:
            raise ProposalApplyError(
                f"Workout {edit_workout_id} not found or not owned by athlete"
            )

        value = edit["new_value"]
        if field == "scheduled_date":
            target.scheduled_date = date.fromisoformat(value)
            target.status = WorkoutStatus.moved
        else:  # status
            if value not in {"planned", "moved", "skipped"}:
                raise ProposalApplyError(f"Invalid status value: {value}")
            target.status = WorkoutStatus(value)

    proposal["state"] = "applied"
    proposal["applied_choice"] = choice
    flag_modified(msg, "proposal_state_json")
    await db.commit()
