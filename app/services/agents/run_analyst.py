import uuid

from sqlalchemy.ext.asyncio import AsyncSession


async def review_reconciliation(db: AsyncSession, reconciliation_id: uuid.UUID) -> str:
    """Review a reconciled workout pair. Wired in session 3."""
    raise NotImplementedError("Wired in session 3")
