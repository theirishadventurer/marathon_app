from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.deps import get_current_athlete, get_db
from app.models.agent import AgentKind, AgentMessage
from app.models.athlete import Athlete
from app.schemas.chat import (
    ChatHistoryOut,
    ChatMessageOut,
    ChatProposalApplyRequest,
    PostChatRequest,
    PostChatResponse,
)
from app.services.agents import coach_chat
from app.services.cache_invalidation import invalidate_for_athlete
from app.services.proposal_apply import (
    ProposalApplyError,
    ProposalNotFound,
    apply_proposal,
)

router = APIRouter(prefix="/chat", tags=["chat"])


@router.get("", response_model=ChatHistoryOut)
async def get_chat(
    limit: int = Query(default=50, ge=1, le=200),
    before: uuid.UUID | None = Query(default=None),
    athlete: Athlete = Depends(get_current_athlete),
    db: AsyncSession = Depends(get_db),
):
    q = (
        select(AgentMessage)
        .where(
            AgentMessage.athlete_id == athlete.id,
            AgentMessage.agent == AgentKind.user_chat,
        )
        .order_by(AgentMessage.created_at.desc())
        .limit(limit)
    )
    if before is not None:
        anchor = (
            await db.execute(select(AgentMessage).where(AgentMessage.id == before))
        ).scalar_one_or_none()
        if anchor is not None:
            q = q.where(AgentMessage.created_at < anchor.created_at)
    rows = list(reversed((await db.execute(q)).scalars().all()))

    return ChatHistoryOut(
        messages=[
            ChatMessageOut(
                id=m.id,
                role=m.role.value,
                content_md=m.content_md,
                created_at=m.created_at,
                proposal=m.proposal_state_json if m.proposal_state_json else None,
            )
            for m in rows
        ]
    )


@router.post("", response_model=PostChatResponse)
async def post_chat(
    body: PostChatRequest,
    athlete: Athlete = Depends(get_current_athlete),
    db: AsyncSession = Depends(get_db),
):
    if not settings.gemini_api_key:
        raise HTTPException(status_code=503, detail="Coach unavailable — GEMINI_API_KEY not set")
    try:
        result = await coach_chat.run_turn(db, athlete.id, body.message)
    except HTTPException:
        raise
    except Exception as e:  # noqa: BLE001 — convert to CORS-safe 502
        raise HTTPException(status_code=502, detail="Coach failed to respond") from e

    if result.proposal is not None:
        invalidate_for_athlete(athlete.id)  # a proposal row was written
    return PostChatResponse(reply_md=result.reply_md, proposal=result.proposal)


@router.post("/proposal/apply")
async def apply_chat_proposal(
    body: ChatProposalApplyRequest,
    athlete: Athlete = Depends(get_current_athlete),
    db: AsyncSession = Depends(get_db),
):
    try:
        await apply_proposal(db, athlete.id, body.proposal_id, body.choice)
    except ProposalNotFound:
        raise HTTPException(status_code=404, detail="Proposal not found") from None
    except ProposalApplyError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    invalidate_for_athlete(athlete.id)
    return {"ok": True}
