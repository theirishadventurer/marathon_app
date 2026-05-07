from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.plan import PlannedWorkoutOut


class CompletedWorkoutOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    garmin_activity_id: int | None
    activity_date: date
    started_at: datetime
    activity_type: str
    family: str
    duration_s: int
    distance_m: Decimal | None
    avg_hr: int | None
    max_hr: int | None
    avg_pace_s_per_km: int | None
    elevation_gain_m: Decimal | None
    calories: int | None


class ReconciliationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    planned_id: uuid.UUID | None
    completed_id: uuid.UUID | None
    match_confidence: Decimal | None
    deviation_notes_md: str
    agent_review_md: str | None
    agent_reviewed_at: datetime | None


class WorkoutDetailOut(BaseModel):
    planned: PlannedWorkoutOut | None
    completed: CompletedWorkoutOut | None
    reconciliation: ReconciliationOut | None


class LogCompletedRequest(BaseModel):
    """Manual completion log: duration is required; pace/distance optional."""

    model_config = ConfigDict(extra="forbid")

    duration_min: int = Field(..., ge=1, le=600)
    distance_mi: float | None = Field(default=None, ge=0, le=100)
    avg_pace_str: str | None = Field(default=None, max_length=10)
    avg_hr: int | None = Field(default=None, ge=20, le=250)
    notes: str | None = Field(default=None, max_length=2000)


class LogCompletedResponse(BaseModel):
    planned: PlannedWorkoutOut
    completed: CompletedWorkoutOut
    reconciliation: ReconciliationOut
