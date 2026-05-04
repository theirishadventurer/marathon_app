from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class DailyMetricOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    metric_date: date
    sleep_score: int | None
    sleep_duration_s: int | None
    hrv_overnight_ms: Decimal | None
    resting_hr: int | None
    body_battery_high: int | None
    body_battery_low: int | None
    training_readiness: int | None
    training_status: str | None
