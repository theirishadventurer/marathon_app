from datetime import date
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class MoveRequest(BaseModel):
    new_date: date


class WorkoutEdit(BaseModel):
    workout_id: UUID
    field: str  # "scheduled_date" or "status"
    new_value: str


class AdapterOption(BaseModel):
    id: str  # "option_a" or "option_b"
    label: str
    tradeoff: str
    edits: list[WorkoutEdit]
    rationale: str


class ProposalOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    proposal_id: UUID
    summary: str
    options: list[AdapterOption]
    # Lifecycle state ("pending" | "applied" | "discarded"). Optional so the
    # drag-flow proposal endpoint (which omits it) is unaffected; the chat
    # history needs it to know whether to still offer "Review proposal".
    state: str | None = None


class ApplyMoveRequest(BaseModel):
    proposal_id: UUID
    choice: str  # "option_a", "option_b", "just_move", "cancel"
