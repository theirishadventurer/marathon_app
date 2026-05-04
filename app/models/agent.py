from __future__ import annotations

import enum
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import Enum, ForeignKey, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, UUIDMixin


class AgentKind(enum.StrEnum):
    daily_coach = "daily_coach"
    plan_adapter = "plan_adapter"
    run_analyst = "run_analyst"
    user_chat = "user_chat"


class MessageRole(enum.StrEnum):
    system = "system"
    user = "user"
    assistant = "assistant"


class AgentMessage(UUIDMixin, Base):
    __tablename__ = "agent_messages"

    athlete_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("athletes.id", ondelete="CASCADE"),
        nullable=False,
    )
    agent: Mapped[AgentKind] = mapped_column(
        Enum(AgentKind, name="agent_kind", native_enum=True), nullable=False
    )
    role: Mapped[MessageRole] = mapped_column(
        Enum(MessageRole, name="message_role", native_enum=True), nullable=False
    )
    content_md: Mapped[str] = mapped_column(Text, nullable=False)
    context_snapshot_json: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    related_workout_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("planned_workouts.id", ondelete="SET NULL"),
        nullable=True,
    )
    related_reconciliation_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("reconciliations.id", ondelete="SET NULL"),
        nullable=True,
    )
    proposal_state_json: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now(), nullable=False)
