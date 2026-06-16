from app.services.llm.gemini_client import (
    COACH_SYSTEM_PROMPT,
    PROPOSE_PLAN_CHANGE_DECLARATION,
)


def test_declaration_shape():
    d = PROPOSE_PLAN_CHANGE_DECLARATION
    assert d["name"] == "propose_plan_change"
    props = d["parameters"]["properties"]
    assert set(props) >= {"summary", "options"}
    opt = props["options"]["items"]["properties"]
    assert set(opt) >= {"id", "label", "tradeoff", "rationale", "edits"}
    edit = opt["edits"]["items"]["properties"]
    assert set(edit) == {"workout_id", "field", "new_value"}
    assert edit["field"]["enum"] == ["scheduled_date", "status"]


def test_system_prompt_mentions_guardrails():
    assert "never fabricate" in COACH_SYSTEM_PROMPT.lower()
