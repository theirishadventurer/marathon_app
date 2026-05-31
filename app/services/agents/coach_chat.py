from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.agent import AgentKind, AgentMessage, MessageRole
from app.services.agent_context import build_athlete_context
from app.services.llm.gemini_client import (
    COACH_SYSTEM_PROMPT,
    PROPOSE_PLAN_CHANGE_DECLARATION,
    get_gemini_client,
)

HISTORY_LIMIT = 20


@dataclass
class ChatTurnResult:
    reply_md: str
    proposal: dict[str, Any] | None = None


async def _recent_history(db: AsyncSession, athlete_id: uuid.UUID) -> list[AgentMessage]:
    rows = (
        (
            await db.execute(
                select(AgentMessage)
                .where(
                    AgentMessage.athlete_id == athlete_id,
                    AgentMessage.agent == AgentKind.user_chat,
                )
                .order_by(AgentMessage.created_at.desc())
                .limit(HISTORY_LIMIT)
            )
        )
        .scalars()
        .all()
    )
    return list(reversed(rows))


def _build_prompt(context_md: str, history: list[AgentMessage], message: str) -> str:
    parts = [f"Athlete context:\n{context_md}", "---"]
    if history:
        convo = "\n".join(f"{m.role.value}: {m.content_md}" for m in history if m.content_md)
        parts.append(convo)
        parts.append("---")
    parts.append(f"user: {message}")
    return "\n".join(parts)


def _extract(response: Any) -> tuple[str, dict[str, Any] | None]:
    """Return (text, function_args|None) from a Gemini response."""
    text_chunks: list[str] = []
    fc_args: dict[str, Any] | None = None
    for cand in response.candidates or []:
        for part in cand.content.parts or []:
            fc = getattr(part, "function_call", None)
            if fc is not None and getattr(fc, "name", None) == "propose_plan_change":
                fc_args = dict(fc.args)
            elif getattr(part, "text", None):
                text_chunks.append(part.text)
    return ("".join(text_chunks).strip(), fc_args)


def _lead_workout_id(options: list[dict[str, Any]]) -> uuid.UUID | None:
    """The first edit's workout_id, used only as a soft pointer. Ownership is
    re-validated at apply time (proposal_apply), never trusted here."""
    for opt in options:
        for edit in opt.get("edits", []):
            try:
                return uuid.UUID(edit["workout_id"])
            except (KeyError, ValueError):
                continue
    return None


async def run_turn(db: AsyncSession, athlete_id: uuid.UUID, message: str) -> ChatTurnResult:
    ctx = await build_athlete_context(db, athlete_id)

    # 1. Persist the user turn (kept even if Gemini later fails — see plan Q2).
    user_msg = AgentMessage(
        athlete_id=athlete_id,
        agent=AgentKind.user_chat,
        role=MessageRole.user,
        content_md=message,
        context_snapshot_json=ctx.snapshot,
    )
    db.add(user_msg)
    await db.commit()

    # 2. Load history (includes the just-persisted user turn at the tail; drop it).
    history = await _recent_history(db, athlete_id)
    history = [m for m in history if m.id != user_msg.id]

    # 3. Call Gemini. The caller (route) wraps this in try/except → 502.
    client = get_gemini_client()
    from google.genai import types  # local import keeps module import-safe in tests

    response = client.models.generate_content(
        model=settings.gemini_model,
        contents=_build_prompt(ctx.markdown, history, message),
        config=types.GenerateContentConfig(
            system_instruction=COACH_SYSTEM_PROMPT,
            tools=[types.Tool(function_declarations=[PROPOSE_PLAN_CHANGE_DECLARATION])],
        ),
    )

    text, fc_args = _extract(response)

    # 4. Branch.
    if fc_args is not None:
        summary = fc_args["summary"]
        options = fc_args["options"]
        proposal_id = str(uuid.uuid4())
        lead_workout_id = _lead_workout_id(options)
        proposal_state = {
            "proposal_id": proposal_id,
            "summary": summary,
            "options": options,
            "state": "pending",
            "created_by": "user_chat",
        }
        assistant_msg = AgentMessage(
            athlete_id=athlete_id,
            agent=AgentKind.user_chat,
            role=MessageRole.assistant,
            content_md=summary,
            related_workout_id=lead_workout_id,
            proposal_state_json=proposal_state,
        )
        db.add(assistant_msg)
        await db.commit()
        return ChatTurnResult(reply_md=summary, proposal=proposal_state)

    reply = text or "I'm not sure how to respond to that — could you rephrase?"
    assistant_msg = AgentMessage(
        athlete_id=athlete_id,
        agent=AgentKind.user_chat,
        role=MessageRole.assistant,
        content_md=reply,
    )
    db.add(assistant_msg)
    await db.commit()
    return ChatTurnResult(reply_md=reply, proposal=None)
