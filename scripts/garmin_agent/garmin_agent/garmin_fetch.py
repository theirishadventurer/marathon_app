from __future__ import annotations

import logging
from datetime import date, timedelta
from getpass import getpass

from garminconnect import Garmin

logger = logging.getLogger(__name__)


def login_interactive(email: str) -> str:
    """One-time interactive login (handles MFA). Returns the garth token blob.

    The password is read at the prompt and never persisted."""
    password = getpass(f"Garmin password for {email}: ")
    client = Garmin(email=email, password=password)
    client.login()  # prompts for MFA on the console if the account requires it
    if getattr(client, "garth", None) is None:
        raise RuntimeError("Login did not establish a session (check creds / rate limit).")
    return client.garth.dumps()


def client_from_token(token: str) -> Garmin:
    client = Garmin()
    client.garth.loads(token)
    client.login()  # refreshes via cached token; no password
    if getattr(client, "garth", None) is None:
        raise RuntimeError("Cached token rejected — re-run with --login.")
    return client


def fetch(client: Garmin, lookback_days: int) -> tuple[list[dict], list[dict]]:
    start = (date.today() - timedelta(days=lookback_days)).isoformat()
    end = date.today().isoformat()
    activities = client.get_activities_by_date(start, end) or []
    metrics: list[dict] = []
    cursor = date.today() - timedelta(days=lookback_days)
    while cursor <= date.today():
        try:
            stats = client.get_daily_stats(cursor.isoformat())
            if stats:
                metrics.append(stats if isinstance(stats, dict) else stats[0])
        except Exception as exc:  # noqa: BLE001
            logger.warning("daily stats failed for %s: %s", cursor, exc)
        cursor += timedelta(days=1)
    return activities, metrics
