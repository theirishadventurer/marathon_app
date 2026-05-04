import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.agent import AgentMessage


async def generate_daily_brief(db: AsyncSession, athlete_id: uuid.UUID) -> AgentMessage:
    """Generate morning coaching brief. Wired in session 3."""
    raise NotImplementedError("Wired in session 3")
