import uuid
from datetime import date
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession


async def propose_rebalance(
    db: AsyncSession, athlete_id: uuid.UUID, workout_id: uuid.UUID, new_date: date
) -> dict[str, Any]:
    """Propose rebalance options when a workout is moved. Wired in session 2."""
    raise NotImplementedError("Wired in session 2")
