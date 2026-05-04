import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.athlete import Athlete
from app.models.plan import Cycle, Plan
from app.models.workout import PlannedWorkout


@pytest.mark.asyncio
async def test_plan_parser_parses_plan_md():
    from app.seed.plan_parser import parse_plan

    data = parse_plan("PLAN.md")
    assert data["athlete"]["name"] != ""
    assert len(data["cycles"]) == 3
    assert data["cycles"][0]["race_name"] == "Marine Corps Marathon"
    assert data["cycles"][1]["race_name"] == "Walt Disney World Marathon"
    assert data["cycles"][2]["race_name"] == "Coastal Delaware Marathon"
    assert data["philosophy"] != ""
    total_workouts = sum(len(c["workouts"]) for c in data["cycles"])
    assert total_workouts == 364, f"Expected 364 workouts, got {total_workouts}"


@pytest.mark.asyncio
async def test_seed_creates_correct_counts(db: AsyncSession):
    from app.seed.load_plan import seed_plan

    await seed_plan(db, plan_path="PLAN.md", password="testpass")
    athlete_count = (await db.execute(select(func.count()).select_from(Athlete))).scalar()
    assert athlete_count == 1
    plan_count = (await db.execute(select(func.count()).select_from(Plan))).scalar()
    assert plan_count == 1
    cycle_count = (await db.execute(select(func.count()).select_from(Cycle))).scalar()
    assert cycle_count == 3
    workout_count = (await db.execute(select(func.count()).select_from(PlannedWorkout))).scalar()
    assert workout_count == 364


@pytest.mark.asyncio
async def test_seed_is_idempotent(db: AsyncSession):
    from app.seed.load_plan import seed_plan

    await seed_plan(db, plan_path="PLAN.md", password="testpass")
    await seed_plan(db, plan_path="PLAN.md", password="testpass")
    workout_count = (await db.execute(select(func.count()).select_from(PlannedWorkout))).scalar()
    assert workout_count == 364
