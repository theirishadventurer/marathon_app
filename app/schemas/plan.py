from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class PlannedWorkoutOut(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: uuid.UUID
    cycle_id: uuid.UUID
    scheduled_date: date
    original_date: date
    week_number: int
    type: str
    family: str
    status: str
    duration_min: int | None
    distance_mi: Decimal | None
    target_pace: str | None
    target_hr_zone: str | None
    title: str
    description_md: str
    intent_md: str
    original_snapshot: dict | None = Field(default=None, validation_alias="original_snapshot_json")


class CycleOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    sequence: int
    race_name: str
    race_date: date
    start_date: date
    end_date: date


class CycleProgress(BaseModel):
    week: int
    total_weeks: int
    days_to_race: int


class PlanCurrentOut(BaseModel):
    plan_name: str
    plan_id: uuid.UUID
    active_cycle: CycleOut | None
    cycle_progress: CycleProgress | None


class DayWorkouts(BaseModel):
    date: date
    workouts: list[PlannedWorkoutOut]


class WeekOut(BaseModel):
    week_start: date
    days: list[DayWorkouts]


class TodayOut(BaseModel):
    date: date
    workouts: list[PlannedWorkoutOut]
    coach_brief: str | None = None
