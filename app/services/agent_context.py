import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession


async def build_athlete_context(db: AsyncSession, athlete_id: uuid.UUID) -> dict[str, Any]:
    """Build the shared context dict used by all agents. Wired in session 3."""
    raise NotImplementedError("Wired in session 3")
