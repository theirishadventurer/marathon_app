"""CLI entry point: seed the database from PLAN.md.

Usage:
    python -m app.seed.load_plan
"""

from __future__ import annotations

import asyncio
import uuid
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import hash_password
from app.lib.workout_family import family_for_planned
from app.models.athlete import Athlete
from app.models.plan import Cycle, Plan
from app.models.workout import PlannedWorkout, WorkoutType
from app.seed.plan_parser import parse_plan

PLAN_NAME = "Marathon Trilogy 2026-2027"
DEFAULT_PASSWORD = "changeme123"


async def seed_plan(
    db: AsyncSession,
    *,
    plan_path: str = "PLAN.md",
    password: str = DEFAULT_PASSWORD,
) -> dict[str, int]:
    """Seed athlete, plan, cycles, and planned workouts from PLAN.md.

    Idempotent: running twice produces the same result with no duplicates.
    Returns summary counts.
    """
    data = parse_plan(plan_path)
    athlete_data = data["athlete"]

    # --- Upsert athlete by email ---
    result = await db.execute(select(Athlete).where(Athlete.email == athlete_data["email"]))
    athlete = result.scalar_one_or_none()
    if athlete is None:
        athlete = Athlete(
            id=uuid.uuid4(),
            name=athlete_data["name"],
            email=athlete_data["email"],
            password_hash=hash_password(password),
            hr_zones_json=athlete_data["hr_zones"],
            pace_targets_json=athlete_data["pace_targets"],
            injury_notes_md=athlete_data["injury_notes"],
        )
        db.add(athlete)
        await db.flush()

    # --- Upsert plan by athlete_id + name ---
    result = await db.execute(
        select(Plan).where(Plan.athlete_id == athlete.id, Plan.name == PLAN_NAME)
    )
    plan = result.scalar_one_or_none()
    if plan is None:
        plan = Plan(
            id=uuid.uuid4(),
            athlete_id=athlete.id,
            name=PLAN_NAME,
            start_date=data["cycles"][0]["start_date"],
            end_date=data["cycles"][-1]["race_date"],
            philosophy_md=data["philosophy"],
        )
        db.add(plan)
        await db.flush()

    # --- Upsert cycles and create workouts ---
    total_workouts = 0
    for cycle_data in data["cycles"]:
        result = await db.execute(
            select(Cycle).where(
                Cycle.plan_id == plan.id,
                Cycle.sequence == cycle_data["sequence"],
            )
        )
        cycle = result.scalar_one_or_none()
        if cycle is None:
            cycle = Cycle(
                id=uuid.uuid4(),
                plan_id=plan.id,
                name=cycle_data["name"],
                sequence=cycle_data["sequence"],
                race_name=cycle_data["race_name"],
                race_date=cycle_data["race_date"],
                start_date=cycle_data["start_date"],
                end_date=cycle_data["end_date"],
            )
            db.add(cycle)
            await db.flush()

        # Check if workouts already exist for this cycle (skip if so)
        existing = await db.execute(
            select(PlannedWorkout.id).where(PlannedWorkout.cycle_id == cycle.id).limit(1)
        )
        if existing.scalar_one_or_none() is not None:
            # Workouts already seeded for this cycle — count them
            from sqlalchemy import func

            count_result = await db.execute(
                select(func.count())
                .select_from(PlannedWorkout)
                .where(PlannedWorkout.cycle_id == cycle.id)
            )
            total_workouts += count_result.scalar()
            continue

        # Create planned workouts
        peak_week: int | None = None
        peak_long_mi: Decimal | None = None
        for w in cycle_data["workouts"]:
            wtype = WorkoutType(w["type"])
            family = family_for_planned(wtype)

            pw = PlannedWorkout(
                id=uuid.uuid4(),
                cycle_id=cycle.id,
                scheduled_date=w["date"],
                original_date=w["date"],
                week_number=w["week_number"],
                type=wtype,
                family=family,
                distance_mi=w["distance_mi"],
                duration_min=w["duration_min"],
                title=w["title"],
                description_md=w["description_md"],
                intent_md=w["intent_md"],
            )
            db.add(pw)
            total_workouts += 1

            # Track peak: week with the longest non-race long run
            if (
                wtype == WorkoutType.long
                and w["distance_mi"] is not None
                and (peak_long_mi is None or w["distance_mi"] > peak_long_mi)
            ):
                peak_long_mi = w["distance_mi"]
                peak_week = w["week_number"]

        if peak_week is not None and cycle.peak_week_target is None:
            cycle.peak_week_target = peak_week

    await db.commit()

    return {
        "athletes": 1,
        "plans": 1,
        "cycles": len(data["cycles"]),
        "planned_workouts": total_workouts,
    }


async def main() -> None:
    from app.db import async_session_factory

    async with async_session_factory() as session:
        counts = await seed_plan(session)
        print(
            f"Loaded {counts['athletes']} athlete, "
            f"{counts['plans']} plan, "
            f"{counts['cycles']} cycles, "
            f"{counts['planned_workouts']} planned workouts."
        )


if __name__ == "__main__":
    asyncio.run(main())
