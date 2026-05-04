from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class GarminAuthState(Base):
    __tablename__ = "garmin_auth_state"

    athlete_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("athletes.id", ondelete="CASCADE"),
        primary_key=True,
    )
    token_dir_path: Mapped[str] = mapped_column(Text, nullable=False)
    last_successful_sync: Mapped[datetime | None] = mapped_column(nullable=True)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_error_at: Mapped[datetime | None] = mapped_column(nullable=True)
    needs_reauth: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
