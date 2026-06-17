from __future__ import annotations

import uuid
from datetime import date, datetime

from pydantic import BaseModel


class StravaConnectOut(BaseModel):
    authorize_url: str


class StravaStatusOut(BaseModel):
    connected: bool
    athlete_strava_id: int | None = None
    last_sync: datetime | None = None
    last_error: str | None = None
    last_error_at: datetime | None = None


class StravaSyncReportOut(BaseModel):
    synced_activities: int
    errors: list[str]


class CandidateOut(BaseModel):
    completed_id: uuid.UUID
    activity_date: date
    activity_type: str
    distance_mi: float | None
    duration_min: int
    avg_pace_str: str | None
    source: str


class LinkCompletedRequest(BaseModel):
    completed_id: uuid.UUID
