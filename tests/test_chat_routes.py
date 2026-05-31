from unittest.mock import MagicMock, patch

from app.config import settings
from app.services.agents import coach_chat


def _text_response(text):
    part = MagicMock()
    part.function_call = None
    part.text = text
    cand = MagicMock()
    cand.content.parts = [part]
    resp = MagicMock()
    resp.candidates = [cand]
    return resp


async def test_post_chat_returns_reply(client, auth_headers, monkeypatch):
    monkeypatch.setattr(settings, "gemini_api_key", "test-key")
    fake = MagicMock()
    fake.models.generate_content.return_value = _text_response("Keep it up.")
    with patch.object(coach_chat, "get_gemini_client", return_value=fake):
        r = await client.post("/chat", json={"message": "hi"}, headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["reply_md"] == "Keep it up."


async def test_post_chat_gemini_failure_is_502(client, auth_headers, monkeypatch):
    monkeypatch.setattr(settings, "gemini_api_key", "test-key")
    fake = MagicMock()
    fake.models.generate_content.side_effect = RuntimeError("gemini down")
    with patch.object(coach_chat, "get_gemini_client", return_value=fake):
        r = await client.post("/chat", json={"message": "hi"}, headers=auth_headers)
    assert r.status_code == 502


async def test_post_chat_missing_key_is_503(client, auth_headers, monkeypatch):
    monkeypatch.setattr(settings, "gemini_api_key", "")
    r = await client.post("/chat", json={"message": "hi"}, headers=auth_headers)
    assert r.status_code == 503


async def test_get_chat_returns_thread_chronological(client, auth_headers, monkeypatch):
    monkeypatch.setattr(settings, "gemini_api_key", "test-key")
    fake = MagicMock()
    fake.models.generate_content.return_value = _text_response("Reply one.")
    with patch.object(coach_chat, "get_gemini_client", return_value=fake):
        await client.post("/chat", json={"message": "first"}, headers=auth_headers)
    r = await client.get("/chat", headers=auth_headers)
    assert r.status_code == 200
    msgs = r.json()["messages"]
    assert [m["role"] for m in msgs] == ["user", "assistant"]
    assert msgs[0]["content_md"] == "first"
