from datetime import datetime

from pydantic import BaseModel, Field


class GarminReauthRequest(BaseModel):
    email: str
    password: str


class GarminStatusOut(BaseModel):
    needs_reauth: bool
    last_sync: datetime | None
    last_error: str | None
    last_error_at: datetime | None


class SyncReportOut(BaseModel):
    synced_activities: int
    synced_metrics: int
    errors: list[str]


class GarminIngestRequest(BaseModel):
    activities: list[dict] = Field(default_factory=list, max_length=2000)
    metrics: list[dict] = Field(default_factory=list, max_length=2000)


class GarminIngestResponse(BaseModel):
    synced_activities: int
    synced_metrics: int
    skipped: int


class GarminPollOut(BaseModel):
    sync_requested: bool
