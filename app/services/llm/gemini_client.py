from typing import Any

from google import genai

from app.config import settings

COACH_SYSTEM_PROMPT = (
    "You are an experienced marathon coach working with this athlete on a 12-month, "
    "three-marathon plan. You value durability over peak fitness.\n"
    "Be specific, reference the athlete's data, and stay encouraging and concise.\n"
    "\n"
    "How to interact:\n"
    "- Default to conversation. Answer questions, give guidance, and discuss training "
    "in plain text. This is your normal mode.\n"
    "- When the athlete's intent is unclear, ask a clarifying question instead of acting.\n"
    "- ONLY call the propose_plan_change function when the athlete explicitly asks to "
    "change, move, skip, add, or reschedule a workout — or explicitly asks you to modify "
    "the plan. Do NOT propose changes in response to greetings, status checks, or general "
    "questions. Discuss first; propose only when asked.\n"
    "- From time to time, and especially when it's relevant to what the athlete is asking, "
    "remind them in plain text that you can adjust their program whenever they want — and "
    "invite them to just ask. Do this conversationally; do not call the function to make "
    "the reminder.\n"
    "- When you do propose a change, always explain the tradeoffs.\n"
    "\n"
    "Guardrails: give general training guidance only — no medical advice; defer to the "
    "athlete on injury and health. Never fabricate data: reason only from the provided "
    "athlete context. If data is missing, say so plainly."
)

# propose_plan_change mirrors the established proposal_state_json contract
# (summary + options[] each with id/label/tradeoff/rationale/edits[]).
# Each edit is {workout_id, field in {scheduled_date, status}, new_value}.
PROPOSE_PLAN_CHANGE_DECLARATION: dict[str, Any] = {
    "name": "propose_plan_change",
    "description": "Propose one or more plan-change options for the athlete to review.",
    "parameters": {
        "type": "object",
        "required": ["summary", "options"],
        "properties": {
            "summary": {"type": "string", "description": "1-2 sentence impact assessment"},
            "options": {
                "type": "array",
                "items": {
                    "type": "object",
                    "required": ["id", "label", "tradeoff", "rationale", "edits"],
                    "properties": {
                        "id": {"type": "string", "enum": ["option_a", "option_b"]},
                        "label": {"type": "string"},
                        "tradeoff": {"type": "string"},
                        "rationale": {"type": "string"},
                        "edits": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "required": ["workout_id", "field", "new_value"],
                                "properties": {
                                    "workout_id": {"type": "string"},
                                    "field": {
                                        "type": "string",
                                        "enum": ["scheduled_date", "status"],
                                    },
                                    "new_value": {"type": "string"},
                                },
                            },
                        },
                    },
                },
            },
        },
    },
}


def get_gemini_client() -> genai.Client:
    """Create a Gemini client. Separated for test mocking (mirrors get_anthropic_client)."""
    # TODO(caching): v1 sends the full prompt each turn; revisit CachedContent if cost matters.
    return genai.Client(api_key=settings.gemini_api_key)
