from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any
from urllib.parse import urlencode

AUTHORIZE_URL = "https://www.strava.com/oauth/authorize"
SCOPE = "activity:read_all"
REFRESH_BUFFER = timedelta(minutes=5)


@dataclass
class StravaTokens:
    access_token: str
    refresh_token: str
    expires_at: datetime
    scope: str | None = None
    athlete_strava_id: int | None = None


def build_authorize_url(*, client_id: str, redirect_uri: str, state: str) -> str:
    params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": SCOPE,
        "approval_prompt": "auto",
        "state": state,
    }
    return f"{AUTHORIZE_URL}?{urlencode(params)}"


def tokens_from_response(resp: dict[str, Any]) -> StravaTokens:
    athlete = resp.get("athlete") or {}
    return StravaTokens(
        access_token=resp["access_token"],
        refresh_token=resp["refresh_token"],
        expires_at=datetime.fromtimestamp(int(resp["expires_at"]), tz=UTC),
        scope=resp.get("scope"),
        athlete_strava_id=athlete.get("id"),
    )


def needs_refresh(expires_at: datetime, now: datetime) -> bool:
    return expires_at - now <= REFRESH_BUFFER
