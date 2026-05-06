from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Literal

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


class WeekRollup(BaseModel):
    week_number: int
    week_start: date
    week_end: date
    planned_count: int
    done_count: int
    skipped_count: int
    moved_count: int
    planned_mi: Decimal
    actual_mi: Decimal
    is_cutback: bool
    is_peak: bool
    has_race: bool
    status: Literal["done", "partial", "current", "upcoming", "skipped"]


class CycleFull(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    sequence: int
    race_name: str
    race_date: date
    start_date: date
    end_date: date
    peak_week_target: int | None = None
    race_planned_id: uuid.UUID | None = None
    weeks: list[WeekRollup] = []


class PlanFullOut(BaseModel):
    plan_name: str
    plan_id: uuid.UUID
    start_date: date
    end_date: date
    cycles: list[CycleFull]


class NextMilestone(BaseModel):
    kind: Literal["peak", "race", "decision"]
    label: str
    date: date


class PeakWeekSummary(BaseModel):
    week_number: int
    planned_mi: Decimal
    long_run_mi: Decimal | None = None


class PlanStatsOut(BaseModel):
    scope: Literal["cycle", "plan"]
    cycle_id: uuid.UUID | None = None
    on_plan_pct: float
    done_count: int
    skipped_count: int
    planned_to_date_count: int
    planned_mi: Decimal
    actual_mi: Decimal
    streak_days: int
    next_milestone: NextMilestone | None = None
    peak_week: PeakWeekSummary | None = None
    computed_at: datetime
