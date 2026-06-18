import hmac
from collections.abc import AsyncGenerator

from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import decode_access_token
from app.config import settings
from app.db import async_session_factory
from app.models.athlete import Athlete

bearer_scheme = HTTPBearer()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_factory() as session:
        yield session


async def get_current_athlete(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> Athlete:
    athlete_id = decode_access_token(credentials.credentials)
    if athlete_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )
    result = await db.execute(select(Athlete).where(Athlete.id == athlete_id))
    athlete = result.scalar_one_or_none()
    if athlete is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Athlete not found",
        )
    return athlete


async def require_ingest_token(
    x_ingest_token: str | None = Header(default=None),
) -> None:
    if not settings.garmin_ingest_token:
        raise HTTPException(status_code=503, detail="Garmin ingest is not configured")
    if x_ingest_token is None or not hmac.compare_digest(
        x_ingest_token, settings.garmin_ingest_token
    ):
        raise HTTPException(status_code=401, detail="Invalid ingest token")


async def get_ingest_athlete(db: AsyncSession = Depends(get_db)) -> Athlete:
    email = settings.garmin_ingest_athlete_email
    if not email:
        raise HTTPException(status_code=503, detail="Garmin ingest athlete not configured")
    athlete = (
        await db.execute(select(Athlete).where(Athlete.email == email))
    ).scalar_one_or_none()
    if athlete is None:
        raise HTTPException(status_code=400, detail="Configured ingest athlete not found")
    return athlete
