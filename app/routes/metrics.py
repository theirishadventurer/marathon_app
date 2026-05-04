from __future__ import annotations

import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import get_current_athlete, get_db
from app.models.athlete import Athlete
from app.models.metrics import DailyMetric
from app.schemas.metrics import DailyMetricOut

router = APIRouter(prefix="/metrics", tags=["metrics"])


@router.get("/recent", response_model=list[DailyMetricOut])
async def metrics_recent(
    days: int = Query(default=14, ge=1, le=90),
    athlete: Athlete = Depends(get_current_athlete),
    db: AsyncSession = Depends(get_db),
):
    cutoff = datetime.date.today() - datetime.timedelta(days=days)
    result = await db.execute(
        select(DailyMetric)
        .where(
            DailyMetric.athlete_id == athlete.id,
            DailyMetric.metric_date >= cutoff,
        )
        .order_by(DailyMetric.metric_date.desc())
    )
    metrics = result.scalars().all()
    return [DailyMetricOut.model_validate(m) for m in metrics]
