from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import get_current_athlete, get_db
from app.models.athlete import Athlete
from app.models.garmin import GarminAuthState
from app.schemas.garmin import GarminReauthRequest, GarminStatusOut
from app.services.garmin_sync import GarminLoginFailed, GarminSyncService

router = APIRouter(prefix="/garmin", tags=["garmin"])


@router.post("/reauth")
async def reauth(
    body: GarminReauthRequest,
    athlete: Athlete = Depends(get_current_athlete),
    db: AsyncSession = Depends(get_db),
):
    svc = GarminSyncService(db=db, athlete_id=str(athlete.id))
    try:
        await svc.reauth(email=body.email, password=body.password)
    except GarminLoginFailed as e:
        # 502 (Bad Gateway): upstream Garmin rejected/throttled us. Surfaces
        # as a clear client-side error (with CORS headers intact) instead of
        # an opaque 500 that the browser misreads as a CORS failure.
        raise HTTPException(status_code=502, detail=str(e)) from e
    return {"ok": True}


@router.get("/status", response_model=GarminStatusOut)
async def status(
    athlete: Athlete = Depends(get_current_athlete),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(GarminAuthState).where(GarminAuthState.athlete_id == athlete.id)
    )
    state = result.scalar_one_or_none()
    if state is None:
        return GarminStatusOut(
            needs_reauth=True,
            last_sync=None,
            last_error=None,
            last_error_at=None,
        )
    return GarminStatusOut(
        needs_reauth=state.needs_reauth,
        last_sync=state.last_successful_sync,
        last_error=state.last_error,
        last_error_at=state.last_error_at,
    )
