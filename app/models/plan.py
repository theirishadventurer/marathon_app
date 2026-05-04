import uuid
from datetime import date, datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.models.athlete import Athlete
    from app.models.workout import PlannedWorkout

from sqlalchemy import Boolean, Date, ForeignKey, SmallInteger, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, UUIDMixin


class Plan(UUIDMixin, Base):
    __tablename__ = "plans"

    athlete_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("athletes.id", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(Text, nullable=False)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    philosophy_md: Mapped[str] = mapped_column(Text, nullable=False, server_default="")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")
    created_at: Mapped[datetime] = mapped_column(server_default=func.now(), nullable=False)

    # Relationships
    athlete: Mapped["Athlete"] = relationship(back_populates="plans")
    cycles: Mapped[list["Cycle"]] = relationship(back_populates="plan")


class Cycle(UUIDMixin, Base):
    __tablename__ = "cycles"

    plan_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("plans.id", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(Text, nullable=False)
    sequence: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    race_name: Mapped[str] = mapped_column(Text, nullable=False)
    race_date: Mapped[date] = mapped_column(Date, nullable=False)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    peak_week_target: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    notes_md: Mapped[str] = mapped_column(Text, nullable=False, server_default="")

    # Relationships
    plan: Mapped["Plan"] = relationship(back_populates="cycles")
    planned_workouts: Mapped[list["PlannedWorkout"]] = relationship(back_populates="cycle")
