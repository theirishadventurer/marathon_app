"""Tests for app.services.plan_reseed (compute_reseed_impact + apply_reseed)."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

import pytest
from sqlalchemy import select


@pytest.mark.asyncio
async def test_compute_reseed_impact_3_weeks_late(seeded_db):
    """Reseeding 3 weeks after the original start drops cycle-1 incomplete planned rows."""
    from app.models.athlete import Athlete
    from app.services.plan_reseed import compute_reseed_impact

    athlete = (await seeded_db.execute(select(Athlete).limit(1))).scalar_one()

    # Default Cycle 1 start is 2026-05-25. Reseed to 2026-06-15 (3 weeks late).
    new_start = date(2026, 6, 15)
    impact = await compute_reseed_impact(seeded_db, athlete.id, new_start)

    # Three weeks of cycle 1 planned rows would drop (~3*7 = 21 rows).
    assert impact.planned_dropped >= 15
    # After reseed Cycle 1 spans 19 weeks (race 10/25, ceil((132 days)/7) = 19).
    assert impact.new_cycle1_weeks == 19
    assert impact.new_cycle1_start == new_start
    assert impact.new_cycle1_end == date(2026, 10, 25)


@pytest.mark.asyncio
async def test_compute_reseed_impact_does_not_mutate(seeded_db):
    from app.models.athlete import Athlete
    from app.models.workout import PlannedWorkout
    from app.services.plan_reseed import compute_reseed_impact

    athlete = (await seeded_db.execute(select(Athlete).limit(1))).scalar_one()

    rows_before = (await seeded_db.execute(select(PlannedWorkout))).scalars().all()
    n_before = len(rows_before)

    await compute_reseed_impact(seeded_db, athlete.id, date(2026, 6, 15))

    rows_after = (await seeded_db.execute(select(PlannedWorkout))).scalars().all()
    assert len(rows_after) == n_before


@pytest.mark.asyncio
async def test_compute_reseed_impact_counts_completed_kept_and_dropped(seeded_db):
    """Completed workouts inside [new_start, last_race_date] are kept; others dropped."""
    from app.models.athlete import Athlete
    from app.models.workout import CompletedWorkout, WorkoutFamily
    from app.services.plan_reseed import compute_reseed_impact

    athlete = (await seeded_db.execute(select(Athlete).limit(1))).scalar_one()

    # Insert completed workouts before/after new_start
    pre = CompletedWorkout(
        athlete_id=athlete.id,
        activity_date=date(2026, 6, 1),
        started_at=datetime(2026, 6, 1, 9, 0),
        activity_type="running",
        family=WorkoutFamily.running,
        duration_s=1800,
        distance_m=Decimal("5000.0"),
        raw_summary_json={"source": "manual"},
    )
    post = CompletedWorkout(
        athlete_id=athlete.id,
        activity_date=date(2026, 6, 22),
        started_at=datetime(2026, 6, 22, 9, 0),
        activity_type="running",
        family=WorkoutFamily.running,
        duration_s=2400,
        distance_m=Decimal("7000.0"),
        raw_summary_json={"source": "manual"},
    )
    seeded_db.add(pre)
    seeded_db.add(post)
    await seeded_db.commit()

    impact = await compute_reseed_impact(seeded_db, athlete.id, date(2026, 6, 15))
    assert impact.completed_kept >= 1  # post
    assert impact.completed_dropped >= 1  # pre


@pytest.mark.asyncio
async def test_apply_reseed_drops_incomplete_and_emits_fresh(seeded_db):
    """apply_reseed deletes cycle-1 incomplete planned rows and emits new ones."""
    from app.models.athlete import Athlete
    from app.models.plan import Cycle, Plan
    from app.models.workout import PlannedWorkout, WorkoutStatus
    from app.services.plan_reseed import apply_reseed

    athlete = (await seeded_db.execute(select(Athlete).limit(1))).scalar_one()

    new_start = date(2026, 6, 15)
    impact = await apply_reseed(seeded_db, athlete.id, new_start)

    # New Cycle 1 emitted with start = new_start
    cycle1 = (
        await seeded_db.execute(select(Cycle).join(Plan).where(Cycle.sequence == 1).limit(1))
    ).scalar_one()
    assert cycle1.start_date == new_start

    # A workout exists exactly on the new start date in cycle 1
    has_new = (
        (
            await seeded_db.execute(
                select(PlannedWorkout).where(
                    PlannedWorkout.cycle_id == cycle1.id,
                    PlannedWorkout.scheduled_date == new_start,
                )
            )
        )
        .scalars()
        .first()
    )
    assert has_new is not None

    # All cycle-1 planned/moved rows now have scheduled_date >= new_start
    cycle1_planned = (
        (
            await seeded_db.execute(
                select(PlannedWorkout).where(
                    PlannedWorkout.cycle_id == cycle1.id,
                    PlannedWorkout.status.in_([WorkoutStatus.planned, WorkoutStatus.moved]),
                )
            )
        )
        .scalars()
        .all()
    )
    assert all(w.scheduled_date >= new_start for w in cycle1_planned)

    assert impact.new_cycle1_weeks == 19


@pytest.mark.asyncio
async def test_apply_reseed_keeps_done_planned_after_new_start(seeded_db):
    """planned_workouts with status=done AND scheduled_date>=new_start survive."""
    from app.models.athlete import Athlete
    from app.models.plan import Cycle, Plan
    from app.models.workout import PlannedWorkout, WorkoutStatus
    from app.services.plan_reseed import apply_reseed

    athlete = (await seeded_db.execute(select(Athlete).limit(1))).scalar_one()

    # Mark a single post-new-start workout as done
    target = (
        (
            await seeded_db.execute(
                select(PlannedWorkout)
                .join(Cycle)
                .join(Plan)
                .where(
                    Plan.athlete_id == athlete.id,
                    Cycle.sequence == 1,
                    PlannedWorkout.scheduled_date == date(2026, 6, 18),
                )
                .limit(1)
            )
        )
        .scalars()
        .first()
    )
    assert target is not None, "Setup precondition failed"
    target_id = target.id
    target.status = WorkoutStatus.done
    await seeded_db.commit()

    await apply_reseed(seeded_db, athlete.id, date(2026, 6, 15))

    survivor = (
        (await seeded_db.execute(select(PlannedWorkout).where(PlannedWorkout.id == target_id)))
        .scalars()
        .first()
    )
    assert survivor is not None
    assert survivor.status == WorkoutStatus.done


@pytest.mark.asyncio
async def test_apply_reseed_drops_done_before_new_start(seeded_db):
    """planned_workouts with scheduled_date < new_start are deleted regardless of status."""
    from app.models.athlete import Athlete
    from app.models.plan import Cycle, Plan
    from app.models.workout import PlannedWorkout, WorkoutStatus
    from app.services.plan_reseed import apply_reseed

    athlete = (await seeded_db.execute(select(Athlete).limit(1))).scalar_one()

    # Mark a pre-new-start workout as done
    target = (
        (
            await seeded_db.execute(
                select(PlannedWorkout)
                .join(Cycle)
                .join(Plan)
                .where(
                    Plan.athlete_id == athlete.id,
                    Cycle.sequence == 1,
                    PlannedWorkout.scheduled_date < date(2026, 6, 15),
                )
                .limit(1)
            )
        )
        .scalars()
        .first()
    )
    target_id = target.id
    target.status = WorkoutStatus.done
    await seeded_db.commit()

    await apply_reseed(seeded_db, athlete.id, date(2026, 6, 15))

    survivor = (
        (await seeded_db.execute(select(PlannedWorkout).where(PlannedWorkout.id == target_id)))
        .scalars()
        .first()
    )
    assert survivor is None


@pytest.mark.asyncio
async def test_apply_reseed_writes_plan_history(seeded_db):
    from app.models.athlete import Athlete
    from app.models.plan_history import PlanHistory
    from app.services.plan_reseed import apply_reseed

    athlete = (await seeded_db.execute(select(Athlete).limit(1))).scalar_one()
    await apply_reseed(seeded_db, athlete.id, date(2026, 6, 15))

    history = (
        (
            await seeded_db.execute(
                select(PlanHistory).where(PlanHistory.action == "start_date_reseed")
            )
        )
        .scalars()
        .all()
    )
    assert len(history) >= 1
    payload = history[0].payload_json
    assert payload["old_start"] == "2026-05-25"
    assert payload["new_start"] == "2026-06-15"
    assert "planned_dropped" in payload
    assert "new_cycle1_weeks" in payload


@pytest.mark.asyncio
async def test_apply_reseed_discards_pending_proposals(seeded_db):
    """Pending agent_messages proposals are marked discarded with reason=plan_shifted."""
    from app.models.agent import AgentKind, AgentMessage, MessageRole
    from app.models.athlete import Athlete
    from app.services.plan_reseed import apply_reseed

    athlete = (await seeded_db.execute(select(Athlete).limit(1))).scalar_one()

    msg = AgentMessage(
        athlete_id=athlete.id,
        agent=AgentKind.plan_adapter,
        role=MessageRole.assistant,
        content_md="propose move",
        proposal_state_json={"state": "pending", "kind": "move"},
    )
    seeded_db.add(msg)
    await seeded_db.commit()
    msg_id = msg.id

    impact = await apply_reseed(seeded_db, athlete.id, date(2026, 6, 15))
    assert impact.proposals_discarded >= 1

    refreshed = (
        await seeded_db.execute(select(AgentMessage).where(AgentMessage.id == msg_id))
    ).scalar_one()
    assert refreshed.proposal_state_json["state"] == "discarded"
    assert refreshed.proposal_state_json["discard_reason"] == "plan_shifted"


@pytest.mark.asyncio
async def test_apply_reseed_updates_plan_start_date(seeded_db):
    from app.models.athlete import Athlete
    from app.models.plan import Plan
    from app.services.plan_reseed import apply_reseed

    athlete = (await seeded_db.execute(select(Athlete).limit(1))).scalar_one()
    await apply_reseed(seeded_db, athlete.id, date(2026, 6, 15))

    plan = (
        await seeded_db.execute(select(Plan).where(Plan.athlete_id == athlete.id))
    ).scalar_one()
    assert plan.start_date == date(2026, 6, 15)
