from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.move import ProposalOut


class ChatMessageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    role: str  # "user" | "assistant"
    content_md: str
    created_at: datetime
    proposal: ProposalOut | None = None


class ChatHistoryOut(BaseModel):
    messages: list[ChatMessageOut]


class PostChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)


class PostChatResponse(BaseModel):
    reply_md: str
    proposal: ProposalOut | None = None


class ChatProposalApplyRequest(BaseModel):
    proposal_id: UUID
    choice: str  # "option_a" | "option_b" | "just_move" | "cancel"
