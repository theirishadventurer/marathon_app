from sqlalchemy import select

from app.models.athlete import Athlete
from app.services.agent_context import build_athlete_context


async def test_build_context_has_snapshot_and_markdown(seeded_db):
    athlete = (await seeded_db.execute(select(Athlete).limit(1))).scalar_one()
    ctx = await build_athlete_context(seeded_db, athlete.id)
    assert isinstance(ctx.snapshot, dict)
    assert isinstance(ctx.markdown, str)
    assert ctx.markdown  # non-empty
    # snapshot carries plan + progress sections
    assert "plan" in ctx.snapshot
    assert ctx.snapshot["plan"] is not None
    assert "progress" in ctx.snapshot
    assert "today" in ctx.snapshot


async def test_build_context_no_plan_is_minimal(db, athlete):
    # The bare `athlete` fixture has no Plan.
    ctx = await build_athlete_context(db, athlete.id)
    assert ctx.snapshot["plan"] is None
    assert "no plan" in ctx.markdown.lower()
