from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin


class Athlete(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "athletes"

    name: Mapped[str] = mapped_column(Text, nullable=False)
    email: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(Text, nullable=False)
    hr_zones_json: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    pace_targets_json: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB, nullable=True
    )
    injury_notes_md: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    plans: Mapped[list["Plan"]] = relationship(back_populates="athlete")
