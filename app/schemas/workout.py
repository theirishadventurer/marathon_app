from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict

from app.schemas.plan import PlannedWorkoutOut


class CompletedWorkoutOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    garmin_activity_id: int
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
