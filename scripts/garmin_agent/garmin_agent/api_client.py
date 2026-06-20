from __future__ import annotations

import httpx

from garmin_agent.config import AgentConfig


def build_payload(activities, metrics) -> dict:
    return {"activities": activities or [], "metrics": metrics or []}


def post_ingest(cfg: AgentConfig, token: str, payload: dict) -> dict:
    resp = httpx.post(
        f"{cfg.api_url}/garmin/ingest",
        json=payload,
        headers={"X-Ingest-Token": token},
        timeout=60,
    )
    resp.raise_for_status()
    return resp.json()


def poll_requested(cfg: AgentConfig, token: str) -> bool:
    resp = httpx.get(
        f"{cfg.api_url}/garmin/poll",
        headers={"X-Ingest-Token": token},
        timeout=15,
    )
    resp.raise_for_status()
    return bool(resp.json().get("sync_requested"))
