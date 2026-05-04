from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import CheckConstraint, ForeignKey, Numeric, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, UUIDMixin


class Reconciliation(UUIDMixin, Base):
    __tablename__ = "reconciliations"
    __table_args__ = (
        CheckConstraint(
            "planned_id IS NOT NULL OR completed_id IS NOT NULL",
            name="recon_at_least_one",
        ),
    )

    athlete_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("athletes.id", ondelete="CASCADE"),
        nullable=False,
    )
    planned_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("planned_workouts.id", ondelete="SET NULL"),
        nullable=True,
    )
    completed_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("completed_workouts.id", ondelete="SET NULL"),
        nullable=True,
    )
    match_confidence: Mapped[Decimal | None] = mapped_column(
        Numeric(3, 2), nullable=True
    )
    deviation_notes_md: Mapped[str] = mapped_column(
        Text, nullable=False, server_default=""
    )
    agent_review_md: Mapped[str | None] = mapped_column(Text, nullable=True)
    agent_reviewed_at: Mapped[datetime | None] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), nullable=False
    )
