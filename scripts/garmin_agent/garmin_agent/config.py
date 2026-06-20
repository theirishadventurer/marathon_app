from __future__ import annotations

import os
from dataclasses import dataclass

import keyring
from dotenv import load_dotenv

load_dotenv()

KEYRING_SERVICE = "marathon-garmin-agent"


@dataclass
class AgentConfig:
    api_url: str
    garmin_email: str
    lookback_days: int
    poll_seconds: int
    periodic_hours: int
    allowed_ip_prefixes: list[str]


def load_config() -> AgentConfig:
    return AgentConfig(
        api_url=os.environ["MARATHON_API_URL"].rstrip("/"),
        garmin_email=os.environ["GARMIN_EMAIL"],
        lookback_days=int(os.environ.get("LOOKBACK_DAYS", "14")),
        poll_seconds=int(os.environ.get("POLL_SECONDS", "60")),
        periodic_hours=int(os.environ.get("PERIODIC_HOURS", "6")),
        allowed_ip_prefixes=[
            p.strip() for p in os.environ.get("ALLOWED_IP_PREFIXES", "").split(",") if p.strip()
        ],
    )


def get_ingest_token() -> str:
    tok = keyring.get_password(KEYRING_SERVICE, "ingest_token")
    if not tok:
        raise RuntimeError("ingest_token not set — run `python -m garmin_agent.agent --set-secrets`")
    return tok


def set_ingest_token(value: str) -> None:
    keyring.set_password(KEYRING_SERVICE, "ingest_token", value)


def get_garth_token() -> str | None:
    return keyring.get_password(KEYRING_SERVICE, "garth_token")


def set_garth_token(value: str) -> None:
    keyring.set_password(KEYRING_SERVICE, "garth_token", value)
