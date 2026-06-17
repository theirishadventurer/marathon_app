from __future__ import annotations

from typing import Any

import httpx

TOKEN_URL = "https://www.strava.com/oauth/token"
DEAUTH_URL = "https://www.strava.com/oauth/deauthorize"
API_BASE = "https://www.strava.com/api/v3"


class StravaClient:
    """Thin async wrapper around Strava's REST API. The single network seam;
    tests patch get_strava_client() to return a fake (mirrors get_gemini_client)."""

    async def exchange_code(
        self, *, client_id: str, client_secret: str, code: str
    ) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=15) as http:
            r = await http.post(
                TOKEN_URL,
                data={
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "code": code,
                    "grant_type": "authorization_code",
                },
            )
            r.raise_for_status()
            return r.json()

    async def refresh_token(
        self, *, client_id: str, client_secret: str, refresh_token: str
    ) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=15) as http:
            r = await http.post(
                TOKEN_URL,
                data={
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "refresh_token": refresh_token,
                    "grant_type": "refresh_token",
                },
            )
            r.raise_for_status()
            return r.json()

    async def get_activities(
        self, *, access_token: str, after_epoch: int, page: int = 1, per_page: int = 100
    ) -> list[dict[str, Any]]:
        async with httpx.AsyncClient(timeout=30) as http:
            r = await http.get(
                f"{API_BASE}/athlete/activities",
                headers={"Authorization": f"Bearer {access_token}"},
                params={"after": after_epoch, "page": page, "per_page": per_page},
            )
            r.raise_for_status()
            return r.json()

    async def deauthorize(self, *, access_token: str) -> None:
        async with httpx.AsyncClient(timeout=15) as http:
            r = await http.post(
                DEAUTH_URL, headers={"Authorization": f"Bearer {access_token}"}
            )
            r.raise_for_status()


def get_strava_client() -> StravaClient:
    """Separated for test mocking (mirrors get_gemini_client / get_anthropic_client)."""
    return StravaClient()
