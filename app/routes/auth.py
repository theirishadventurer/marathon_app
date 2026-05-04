from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import create_access_token, verify_password
from app.deps import get_db
from app.models.athlete import Athlete
from app.schemas.auth import LoginRequest, TokenResponse

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Athlete).where(Athlete.email == body.email))
    athlete = result.scalar_one_or_none()
    if athlete is None or not verify_password(body.password, athlete.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )
    token, expires_at = create_access_token(str(athlete.id))
    return TokenResponse(token=token, expires_at=expires_at)
