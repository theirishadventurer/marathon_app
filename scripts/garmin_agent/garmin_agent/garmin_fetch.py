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
    # garminconnect resumes a saved session when the token string (>512 chars) is
    # passed to login() — it calls garth.loads internally and skips SSO. Calling
    # login() with no argument instead attempts a fresh SSO login with empty
    # credentials (401). The garth token carries OAuth creds only; no password.
    client.login(tokenstore=token)
    if getattr(client, "garth", None) is None:
        raise RuntimeError("Cached token rejected — re-run with --login.")
    return client


def enrich_metric(client: Garmin, cdate: str, day: dict) -> None:
    """Merge recovery fields from the separate Garmin endpoints into the daily
    get_stats() dict, under the exact keys map_metric reads. get_stats() carries
    only the daily summary (restingHeartRate, bodyBattery*); sleep score/duration,
    overnight HRV, training readiness and training status each live on their own
    endpoint. Each endpoint is isolated in its own try/except so one failure does
    not drop the others, and only present values are written (so a missing day
    leaves map_metric's null-tolerant fields untouched). Mutates `day` in place.
    """
    try:
        sleep = client.get_sleep_data(cdate) or {}
        dto = sleep.get("dailySleepDTO") or {}
        overall = (dto.get("sleepScores") or {}).get("overall") or {}
        if overall.get("value") is not None:
            day["sleepScore"] = overall["value"]
        if dto.get("sleepTimeSeconds") is not None:
            day["sleepDurationSeconds"] = dto["sleepTimeSeconds"]
        if sleep.get("avgOvernightHrv") is not None:
            day["hrvOvernight"] = sleep["avgOvernightHrv"]
    except Exception as exc:  # noqa: BLE001
        logger.warning("sleep/hrv enrich failed for %s: %s", cdate, exc)
    try:
        tr = client.get_training_readiness(cdate) or []
        if isinstance(tr, list) and tr and tr[0].get("score") is not None:
            day["trainingReadiness"] = tr[0]["score"]
    except Exception as exc:  # noqa: BLE001
        logger.warning("training-readiness enrich failed for %s: %s", cdate, exc)
    try:
        ts = client.get_training_status(cdate) or {}
        latest = (ts.get("mostRecentTrainingStatus") or {}).get("latestTrainingStatusData") or {}
        for dev in latest.values():
            phrase = (dev or {}).get("trainingStatusFeedbackPhrase")
            if phrase:
                day["trainingStatus"] = phrase
                break
    except Exception as exc:  # noqa: BLE001
        logger.warning("training-status enrich failed for %s: %s", cdate, exc)


def fetch(client: Garmin, lookback_days: int) -> tuple[list[dict], list[dict]]:
    today = date.today()
    start = today - timedelta(days=lookback_days)
    activities = client.get_activities_by_date(start.isoformat(), today.isoformat()) or []
    metrics: list[dict] = []
    cursor = start
    while cursor <= today:
        cdate = cursor.isoformat()
        try:
            stats = client.get_stats(cdate)
            if stats:
                day = stats if isinstance(stats, dict) else stats[0]
                enrich_metric(client, cdate, day)
                metrics.append(day)
        except Exception as exc:  # noqa: BLE001
            logger.warning("daily stats failed for %s: %s", cursor, exc)
        cursor += timedelta(days=1)
    return activities, metrics
