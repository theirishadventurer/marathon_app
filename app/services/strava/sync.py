from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

from app.lib.workout_family import family_for_strava_sport_type
from app.models.workout import CompletedWorkout


def _parse_started_at(raw: str) -> datetime:
    # Strava ISO8601, may end in 'Z'
    return datetime.fromisoformat(raw.replace("Z", "+00:00"))


def map_activity(athlete_id: uuid.UUID, act: dict[str, Any]) -> CompletedWorkout:
    started_at = _parse_started_at(act["start_date_local"])
    sport = act.get("sport_type") or act.get("type") or "Run"

    avg_speed = act.get("average_speed") or 0
    avg_pace = round(1000 / avg_speed) if avg_speed and avg_speed > 0 else None

    has_hr = act.get("has_heartrate")
    avg_hr = round(act["average_heartrate"]) if has_hr and act.get("average_heartrate") else None
    max_hr = round(act["max_heartrate"]) if has_hr and act.get("max_heartrate") else None

    def _num(key: str) -> Decimal | None:
        v = act.get(key)
        return Decimal(str(v)) if v is not None else None

    return CompletedWorkout(
        athlete_id=athlete_id,
        strava_activity_id=int(act["id"]),
        source="strava",
        activity_date=started_at.date(),
        started_at=started_at,
        activity_type=str(sport),
        family=family_for_strava_sport_type(str(sport)),
        duration_s=int(act.get("moving_time", 0)),
        distance_m=_num("distance"),
        avg_hr=avg_hr,
        max_hr=max_hr,
        avg_pace_s_per_km=avg_pace,
        elevation_gain_m=_num("total_elevation_gain"),
        calories=int(act["calories"]) if act.get("calories") is not None else None,
        avg_cadence=_num("average_cadence"),
        avg_watts=_num("average_watts"),
        relative_effort=int(act["suffer_score"]) if act.get("suffer_score") is not None else None,
        raw_summary_json=act,
    )
