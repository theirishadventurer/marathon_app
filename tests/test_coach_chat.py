from unittest.mock import MagicMock, patch

from sqlalchemy import select

from app.models.agent import AgentKind, AgentMessage, MessageRole
from app.models.athlete import Athlete
from app.models.workout import PlannedWorkout
from app.services.agents import coach_chat


def _text_response(text: str):
    part = MagicMock()
    part.function_call = None
    part.text = text
    cand = MagicMock()
    cand.content.parts = [part]
    resp = MagicMock()
    resp.candidates = [cand]
    return resp


def _proposal_response(summary: str, workout_id: str):
    fc = MagicMock()
    fc.name = "propose_plan_change"
    fc.args = {
        "summary": summary,
        "options": [
            {
                "id": "option_a",
                "label": "Shift long run",
                "tradeoff": "more rest",
                "rationale": "durability",
                "edits": [
                    {"workout_id": workout_id, "field": "scheduled_date", "new_value": "2026-06-02"}
                ],
            }
        ],
    }
    part = MagicMock()
    part.function_call = fc
    part.text = None
    cand = MagicMock()
    cand.content.parts = [part]
    resp = MagicMock()
    resp.candidates = [cand]
    return resp


async def test_run_turn_text_persists_two_rows(seeded_db):
    athlete = (await seeded_db.execute(select(Athlete).limit(1))).scalar_one()
    fake = MagicMock()
    fake.models.generate_content.return_value = _text_response("Nice work this week.")
    with patch.object(coach_chat, "get_gemini_client", return_value=fake):
        result = await coach_chat.run_turn(seeded_db, athlete.id, "How am I doing?")

    assert result.reply_md == "Nice work this week."
    assert result.proposal is None
    rows = (
        (
            await seeded_db.execute(
                select(AgentMessage)
                .where(AgentMessage.agent == AgentKind.user_chat)
                .order_by(AgentMessage.created_at)
            )
        )
        .scalars()
        .all()
    )
    assert len(rows) == 2
    assert rows[0].role == MessageRole.user
    assert rows[0].context_snapshot_json is not None
    assert rows[1].role == MessageRole.assistant


async def test_run_turn_proposal_branch(seeded_db):
    athlete = (await seeded_db.execute(select(Athlete).limit(1))).scalar_one()
    workout = (await seeded_db.execute(select(PlannedWorkout).limit(1))).scalar_one()
    fake = MagicMock()
    fake.models.generate_content.return_value = _proposal_response(
        "Moving your long run helps recovery.", str(workout.id)
    )
    with patch.object(coach_chat, "get_gemini_client", return_value=fake):
        result = await coach_chat.run_turn(seeded_db, athlete.id, "Can I move my long run?")

    assert result.proposal is not None
    assert result.proposal["state"] == "pending"
    assert result.proposal["options"][0]["id"] == "option_a"
    msg = (
        (
            await seeded_db.execute(
                select(AgentMessage).where(AgentMessage.role == MessageRole.assistant)
            )
        )
        .scalars()
        .first()
    )
    assert msg.proposal_state_json["proposal_id"] == result.proposal["proposal_id"]
