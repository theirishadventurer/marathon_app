from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import get_current_athlete, get_db
from app.models.athlete import Athlete
from app.schemas.garmin import SyncReportOut
from app.services.garmin_sync import GarminSyncService

router = APIRouter(prefix="/admin", tags=["admin"])


@router.post("/sync", response_model=SyncReportOut)
async def sync(
    athlete: Athlete = Depends(get_current_athlete),
    db: AsyncSession = Depends(get_db),
):
    svc = GarminSyncService(db=db, athlete_id=str(athlete.id))
    report = await svc.sync_all()
    return SyncReportOut(**report.to_dict())
