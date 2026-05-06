from __future__ import annotations

from datetime import date
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.models.workout import WorkoutType


class EditWorkoutRequest(BaseModel):
    """All fields optional — only those passed get updated."""

    model_config = ConfigDict(extra="forbid")

    type: WorkoutType | None = None
    distance_mi: Decimal | None = Field(default=None, ge=0, le=100)
    duration_min: int | None = Field(default=None, ge=0, le=600)
    title: str | None = Field(default=None, min_length=1, max_length=200)


class RescheduleOriginalRequest(BaseModel):
    new_date: date


class RescheduleOriginalResponse(BaseModel):
    new_workout_id: str
    proposal: dict  # ProposalOut shape; left loose to avoid circular import
