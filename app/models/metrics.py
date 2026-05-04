from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import Date, ForeignKey, Integer, Numeric, SmallInteger, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, UUIDMixin


class DailyMetric(UUIDMixin, Base):
    __tablename__ = "daily_metrics"
    __table_args__ = (
        UniqueConstraint("athlete_id", "metric_date"),
    )

    athlete_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("athletes.id", ondelete="CASCADE"),
        nullable=False,
    )
    metric_date: Mapped[date] = mapped_column(Date, nullable=False)
    sleep_score: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    sleep_duration_s: Mapped[int | None] = mapped_column(Integer, nullable=True)
    hrv_overnight_ms: Mapped[Decimal | None] = mapped_column(
        Numeric(5, 1), nullable=True
    )
    resting_hr: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    body_battery_high: Mapped[int | None] = mapped_column(
        SmallInteger, nullable=True
    )
    body_battery_low: Mapped[int | None] = mapped_column(
        SmallInteger, nullable=True
    )
    training_readiness: Mapped[int | None] = mapped_column(
        SmallInteger, nullable=True
    )
    training_status: Mapped[str | None] = mapped_column(Text, nullable=True)
    raw_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    synced_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), nullable=False
    )
