from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import RedirectResponse
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.deps import get_current_athlete, get_db
from app.models.athlete import Athlete
from app.models.strava import StravaAuthState
from app.schemas.strava import StravaConnectOut, StravaStatusOut, StravaSyncReportOut
from app.services.strava import oauth
from app.services.strava.client import get_strava_client
from app.services.strava.sync import StravaSyncService

router = APIRouter(prefix="/strava", tags=["strava"])


def _require_config() -> None:
    if not (
        settings.strava_client_id
        and settings.strava_client_secret
        and settings.strava_redirect_uri
    ):
        raise HTTPException(status_code=503, detail="Strava is not configured")


@router.get("/connect", response_model=StravaConnectOut)
async def connect(athlete: Athlete = Depends(get_current_athlete)):
    _require_config()
    url = oauth.build_authorize_url(
        client_id=settings.strava_client_id, redirect_uri=settings.strava_redirect_uri
    )
    return StravaConnectOut(authorize_url=url)


@router.get("/callback")
async def callback(
    code: str,
    athlete: Athlete = Depends(get_current_athlete),
    db: AsyncSession = Depends(get_db),
):
    _require_config()
    client = get_strava_client()
    try:
        resp = await client.exchange_code(
            client_id=settings.strava_client_id,
            client_secret=settings.strava_client_secret,
            code=code,
        )
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=f"Strava token exchange failed: {e}") from e

    tokens = oauth.tokens_from_response(resp)
    state = (
        await db.execute(select(StravaAuthState).where(StravaAuthState.athlete_id == athlete.id))
    ).scalar_one_or_none()
    if state is None:
        state = StravaAuthState(athlete_id=athlete.id)
        db.add(state)
    state.access_token = tokens.access_token
    state.refresh_token = tokens.refresh_token
    state.expires_at = tokens.expires_at
    state.scope = tokens.scope
    state.athlete_strava_id = tokens.athlete_strava_id
    state.last_error = None
    state.last_error_at = None
    await db.commit()

    return RedirectResponse(url=settings.web_origin or "/")


@router.get("/status", response_model=StravaStatusOut)
async def status(
    athlete: Athlete = Depends(get_current_athlete),
    db: AsyncSession = Depends(get_db),
):
    state = (
        await db.execute(select(StravaAuthState).where(StravaAuthState.athlete_id == athlete.id))
    ).scalar_one_or_none()
    if state is None:
        return StravaStatusOut(connected=False)
    return StravaStatusOut(
        connected=True,
        athlete_strava_id=state.athlete_strava_id,
        last_sync=state.last_successful_sync,
        last_error=state.last_error,
        last_error_at=state.last_error_at,
    )


@router.post("/sync", response_model=StravaSyncReportOut)
async def sync(
    athlete: Athlete = Depends(get_current_athlete),
    db: AsyncSession = Depends(get_db),
):
    _require_config()
    try:
        report = await StravaSyncService(db, athlete.id).sync()
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=f"Strava sync failed: {e}") from e
    return StravaSyncReportOut(**report.to_dict())


@router.delete("/disconnect")
async def disconnect(
    athlete: Athlete = Depends(get_current_athlete),
    db: AsyncSession = Depends(get_db),
):
    state = (
        await db.execute(select(StravaAuthState).where(StravaAuthState.athlete_id == athlete.id))
    ).scalar_one_or_none()
    if state is not None:
        client = get_strava_client()
        try:  # noqa: SIM105
            await client.deauthorize(access_token=state.access_token)
        except Exception:  # noqa: BLE001
            pass
        await db.execute(delete(StravaAuthState).where(StravaAuthState.athlete_id == athlete.id))
        await db.commit()
    return {"ok": True}
