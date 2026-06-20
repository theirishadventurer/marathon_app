from datetime import UTC, date, datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import get_current_athlete, get_db, get_ingest_athlete, require_ingest_token
from app.models.athlete import Athlete
from app.models.garmin import GarminAuthState
from app.models.metrics import DailyMetric
from app.models.workout import CompletedWorkout
from app.schemas.garmin import (
    GarminIngestRequest,
    GarminIngestResponse,
    GarminPollOut,
    GarminReauthRequest,
    GarminStatusOut,
)
from app.services.garmin_sync import GarminLoginFailed, GarminSyncService, map_activity, map_metric

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


@router.post("/ingest", response_model=GarminIngestResponse)
async def ingest(
    body: GarminIngestRequest,
    _: None = Depends(require_ingest_token),
    athlete: Athlete = Depends(get_ingest_athlete),
    db: AsyncSession = Depends(get_db),
):
    aid = str(athlete.id)
    skipped = 0

    # Activities: dedup vs DB + within-batch (FIX M3: guard is not None, not truthy)
    incoming_ids = [
        a.get("activityId") for a in body.activities if a.get("activityId") is not None
    ]
    existing = set()
    if incoming_ids:
        rows = await db.execute(
            select(CompletedWorkout.garmin_activity_id).where(
                CompletedWorkout.garmin_activity_id.in_(incoming_ids)
            )
        )
        existing = {r[0] for r in rows.all()}
    seen: set[int] = set()
    synced_activities = 0
    for act in body.activities:
        w = map_activity(act, aid)
        if w is None:
            skipped += 1
            continue
        if w.garmin_activity_id in existing or w.garmin_activity_id in seen:
            continue
        seen.add(w.garmin_activity_id)
        db.add(w)
        synced_activities += 1

    # Metrics: merge non-null fields into existing rows, insert new ones (FIX I2)
    _MERGE_FIELDS = (
        "sleep_score",
        "sleep_duration_s",
        "hrv_overnight_ms",
        "resting_hr",
        "body_battery_high",
        "body_battery_low",
        "training_readiness",
        "training_status",
    )
    synced_metrics = 0
    # Map all metrics once (map_metric is the single source of truth for dates)
    mapped_metrics: list[DailyMetric] = []
    for day in body.metrics:
        m = map_metric(day, aid)
        if m is None:
            skipped += 1
            continue
        mapped_metrics.append(m)

    existing_rows: dict[date, DailyMetric] = {}
    incoming_dates = {m.metric_date for m in mapped_metrics}
    if incoming_dates:
        rows = await db.execute(
            select(DailyMetric).where(
                DailyMetric.athlete_id == athlete.id,
                DailyMetric.metric_date.in_(incoming_dates),
            )
        )
        existing_rows = {r.metric_date: r for r in rows.scalars().all()}

    for m in mapped_metrics:
        target = existing_rows.get(m.metric_date)
        if target is not None and target is not m:
            # Merge non-null fields onto the existing row (DB row or earlier same-date item)
            for field in _MERGE_FIELDS:
                val = getattr(m, field)
                if val is not None:
                    setattr(target, field, val)
            target.raw_json = m.raw_json
            synced_metrics += 1
        else:
            db.add(m)
            existing_rows[m.metric_date] = m
            synced_metrics += 1

    # Upsert GarminAuthState + stamp last sync (FIX M4: create state if absent)
    state = (
        await db.execute(
            select(GarminAuthState).where(GarminAuthState.athlete_id == athlete.id)
        )
    ).scalar_one_or_none()
    if state is None:
        state = GarminAuthState(
            athlete_id=athlete.id,
            token_dir_path="",
            needs_reauth=False,
        )
        db.add(state)
    state.last_successful_sync = datetime.now(UTC).replace(tzinfo=None)
    state.sync_requested_at = None

    # FIX I1: wrap commit — concurrent ingest may race on the unique constraint
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(status_code=409, detail="Concurrent ingest conflict; retry") from exc

    return GarminIngestResponse(
        synced_activities=synced_activities,
        synced_metrics=synced_metrics,
        skipped=skipped,
    )


@router.get("/poll", response_model=GarminPollOut)
async def poll(
    _: None = Depends(require_ingest_token),
    athlete: Athlete = Depends(get_ingest_athlete),
    db: AsyncSession = Depends(get_db),
):
    state = (
        await db.execute(
            select(GarminAuthState).where(GarminAuthState.athlete_id == athlete.id)
        )
    ).scalar_one_or_none()
    requested = state is not None and state.sync_requested_at is not None
    return GarminPollOut(sync_requested=requested)


@router.post("/request-sync")
async def request_sync(
    athlete: Athlete = Depends(get_current_athlete),
    db: AsyncSession = Depends(get_db),
):
    state = (
        await db.execute(
            select(GarminAuthState).where(GarminAuthState.athlete_id == athlete.id)
        )
    ).scalar_one_or_none()
    if state is None:
        state = GarminAuthState(
            athlete_id=athlete.id,
            token_dir_path="",  # residential agent owns tokens; server stores none
            needs_reauth=False,
        )
        db.add(state)
    state.sync_requested_at = datetime.now(UTC)
    await db.commit()
    return {"ok": True}
