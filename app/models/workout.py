import enum
import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from app.models.plan import Cycle

from sqlalchemy import (
    BigInteger,
    Date,
    Enum,
    ForeignKey,
    Integer,
    Numeric,
    SmallInteger,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin


class WorkoutType(enum.StrEnum):
    easy = "easy"
    long = "long"
    tempo = "tempo"
    intervals = "intervals"
    hills = "hills"
    mp_long = "mp_long"
    recovery = "recovery"
    strides = "strides"
    strength_a = "strength_a"
    strength_b = "strength_b"
    cross = "cross"
    rest = "rest"
    race = "race"


class WorkoutFamily(enum.StrEnum):
    running = "running"
    strength = "strength"
    other = "other"


class WorkoutStatus(enum.StrEnum):
    planned = "planned"
    moved = "moved"
    skipped = "skipped"
    done = "done"


class PlannedWorkout(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "planned_workouts"

    cycle_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cycles.id", ondelete="CASCADE"),
        nullable=False,
    )

    scheduled_date: Mapped[date] = mapped_column(Date, nullable=False)
    original_date: Mapped[date] = mapped_column(Date, nullable=False)
    week_number: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    type: Mapped[WorkoutType] = mapped_column(
        Enum(WorkoutType, name="workout_type", native_enum=True), nullable=False
    )
    family: Mapped[WorkoutFamily] = mapped_column(
        Enum(WorkoutFamily, name="workout_family", native_enum=True), nullable=False
    )
    status: Mapped[WorkoutStatus] = mapped_column(
        Enum(WorkoutStatus, name="workout_status", native_enum=True),
        nullable=False,
        server_default="planned",
    )

    duration_min: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    distance_mi: Mapped[Decimal | None] = mapped_column(Numeric(4, 1), nullable=True)
    target_pace: Mapped[str | None] = mapped_column(Text, nullable=True)
    target_hr_zone: Mapped[str | None] = mapped_column(Text, nullable=True)

    title: Mapped[str] = mapped_column(Text, nullable=False)
    description_md: Mapped[str] = mapped_column(Text, nullable=False)
    intent_md: Mapped[str] = mapped_column(Text, nullable=False, server_default="")
    original_snapshot_json: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB, nullable=True, default=None
    )

    # Relationships
    cycle: Mapped["Cycle"] = relationship(back_populates="planned_workouts")


class CompletedWorkout(UUIDMixin, Base):
    __tablename__ = "completed_workouts"

    athlete_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("athletes.id", ondelete="CASCADE"),
        nullable=False,
    )

    garmin_activity_id: Mapped[int | None] = mapped_column(BigInteger, unique=True, nullable=True)
    activity_date: Mapped[date] = mapped_column(Date, nullable=False)
    started_at: Mapped[datetime] = mapped_column(nullable=False)
    activity_type: Mapped[str] = mapped_column(Text, nullable=False)
    family: Mapped[WorkoutFamily] = mapped_column(
        Enum(WorkoutFamily, name="workout_family", native_enum=True, create_type=False),
        nullable=False,
    )

    duration_s: Mapped[int] = mapped_column(Integer, nullable=False)
    distance_m: Mapped[Decimal | None] = mapped_column(Numeric(8, 2), nullable=True)
    avg_hr: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    max_hr: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    avg_pace_s_per_km: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    elevation_gain_m: Mapped[Decimal | None] = mapped_column(Numeric(6, 1), nullable=True)
    calories: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    strava_activity_id: Mapped[int | None] = mapped_column(BigInteger, unique=True, nullable=True)
    source: Mapped[str] = mapped_column(Text, nullable=False, server_default="manual")
    avg_cadence: Mapped[Decimal | None] = mapped_column(Numeric(5, 1), nullable=True)
    avg_watts: Mapped[Decimal | None] = mapped_column(Numeric(6, 1), nullable=True)
    relative_effort: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)

    fit_file_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    raw_summary_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    synced_at: Mapped[datetime] = mapped_column(server_default=func.now(), nullable=False)
