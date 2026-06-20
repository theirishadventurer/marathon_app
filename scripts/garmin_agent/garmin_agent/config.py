from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

import keyring
from dotenv import load_dotenv

load_dotenv()

KEYRING_SERVICE = "marathon-garmin-agent"

# The garth OAuth token blob (several KB) exceeds the Windows Credential Manager
# per-credential size limit (~2560 bytes), which fails CredWrite with
# WinError 1783. It is persisted to a gitignored local file instead — this is
# how the garth library stores it by default anyway. It holds OAuth tokens only,
# never the Garmin password. The small ingest token still uses keyring.
GARTH_TOKEN_PATH = Path(__file__).resolve().parent.parent / ".garth_token"


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
    if not GARTH_TOKEN_PATH.exists():
        return None
    token = GARTH_TOKEN_PATH.read_text(encoding="utf-8").strip()
    return token or None


def set_garth_token(value: str) -> None:
    # Write owner-only (0o600) so the OAuth token blob is not world/group-readable
    # on POSIX hosts (e.g. when this agent is moved to a Linux Pi/mini-PC, per the
    # README). On Windows the mode is effectively ignored and NTFS ACLs from the
    # user profile apply. O_CREAT only sets the mode on creation, so chmod
    # defensively in case a looser-permission file already exists.
    fd = os.open(GARTH_TOKEN_PATH, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(value)
    os.chmod(GARTH_TOKEN_PATH, 0o600)
