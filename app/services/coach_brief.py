"""Coach-brief composer (heuristic).

Pure-function helper that turns the data already assembled by the
``/plan/today`` route into a 1-3 sentence string for the Today screen's
``coach_brief`` field. No LLM, no I/O — pass the data in, get a string
or ``None`` out.

See spec §B2 / §4 of
``docs/superpowers/specs/2026-05-07-feat-b-recent-runs-and-coach-brief-design.md``.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any

# Hard cap per spec: clients render verbatim; treat as the safety net.
MAX_LEN = 280

# "Headline" priority for picking the lead workout when multiple are
# scheduled the same day. Lower index == more headline.
_HEADLINE_ORDER = (
    "race",
    "long",
    "mp_long",
    "tempo",
    "intervals",
    "hills",
    "easy",
    "recovery",
    "strides",
    "strength_a",
    "strength_b",
    "cross",
    "rest",
)


def _enum_value(obj: Any) -> str | None:
    """Pull ``.value`` off a StrEnum-style attr, falling back to ``str()``."""
    if obj is None:
        return None
    val = getattr(obj, "value", None)
    if val is not None:
        return str(val)
    return str(obj)


def _headline_index(workout: Any) -> int:
    t = _enum_value(getattr(workout, "type", None)) or ""
    try:
        return _HEADLINE_ORDER.index(t)
    except ValueError:
        return len(_HEADLINE_ORDER)


def _format_distance_mi(distance_mi: Decimal | float | int | None) -> str | None:
    if distance_mi is None:
        return None
    try:
        d = float(distance_mi)
    except (TypeError, ValueError):
        return None
    # Drop trailing .0 for whole numbers; otherwise one decimal.
    if d == int(d):
        return f"{int(d)}mi"
    return f"{d:.1f}mi"


def _today_sentence(workout: Any) -> str:
    """Lead sentence describing what's prescribed today."""
    wtype = _enum_value(getattr(workout, "type", None)) or "workout"
    family = _enum_value(getattr(workout, "family", None))
    distance = _format_distance_mi(getattr(workout, "distance_mi", None))
    duration = getattr(workout, "duration_min", None)
    pace = getattr(workout, "target_pace", None)

    # Friendly label for the type
    label_map = {
        "easy": "Easy run",
        "long": "Long run",
        "tempo": "Tempo",
        "intervals": "Intervals",
        "hills": "Hills",
        "mp_long": "MP long",
        "recovery": "Recovery",
        "strides": "Strides",
        "strength_a": "Strength A",
        "strength_b": "Strength B",
        "cross": "Cross-training",
        "rest": "Rest day",
        "race": "Race",
    }
    label = label_map.get(wtype, wtype.replace("_", " ").title())

    if wtype == "rest":
        return "Rest day — recovery."

    if family == "running" or wtype in {
        "easy",
        "long",
        "tempo",
        "intervals",
        "hills",
        "mp_long",
        "recovery",
        "strides",
        "race",
    }:
        # Prefer distance + pace; fall back to distance alone or duration.
        if distance and pace:
            return f"{label} — {distance} at {pace} target."
        if distance:
            return f"{label} — {distance}."
        if duration:
            return f"{label} — {duration}min."
        return f"{label} on tap."

    if family == "strength" or wtype in {"strength_a", "strength_b"}:
        if duration:
            # Strength A/B are lower-vs-upper biased; default to lower for A
            bias = "lower-body" if wtype == "strength_a" else "upper-body"
            return f"{label} — {duration}min {bias} session."
        return f"{label} session."

    # Other / cross
    if duration:
        return f"{label} — {duration}min."
    return f"{label} on tap."


def _yesterday_sentence(completion: Any) -> str | None:
    """Recap sentence describing yesterday's actual effort."""
    distance_m = getattr(completion, "distance_m", None)
    pace_s_per_km = getattr(completion, "avg_pace_s_per_km", None)

    distance_mi: float | None = None
    if distance_m is not None:
        try:
            distance_mi = float(distance_m) / 1609.344
        except (TypeError, ValueError):
            distance_mi = None

    if distance_mi is not None and distance_mi > 0:
        d_str = f"{distance_mi:.1f}mi"
        if pace_s_per_km:
            # Convert s/km to mm:ss per mile
            s_per_mi = round(pace_s_per_km * 1.609344)
            mm, ss = divmod(s_per_mi, 60)
            return f"Yesterday: {d_str} @ {mm}:{ss:02d} avg."
        return f"Yesterday: {d_str} run."
    # No distance — at least acknowledge it
    duration_s = getattr(completion, "duration_s", None)
    if duration_s:
        mins = round(duration_s / 60)
        return f"Yesterday: {mins}min session."
    return None


def _adherence_sentence(adherence: float) -> str | None:
    if adherence >= 0.8:
        # Approximate the "X of last 5" framing from spec
        return "You've been steady — 4 of last 5 on plan."
    if adherence >= 0.5:
        return "Some catch-up due — last 5 days a mixed bag."
    return "Reset week — focus on the plan."


def _race_tail(days_to_race: int | None, race_name: str | None) -> str | None:
    if days_to_race is None or race_name is None:
        return None
    if days_to_race < 0:
        return None
    return f"{race_name} {days_to_race} days."


def _enforce_cap(sentences: list[str]) -> str:
    """Join sentences with single spaces; drop tail-first if over MAX_LEN."""
    parts = list(sentences)
    while parts:
        out = " ".join(parts).strip()
        if len(out) <= MAX_LEN:
            return out
        parts.pop()  # drop the last sentence and retry
    return ""


def compose_coach_brief(
    today: date,
    todays_workouts: list[Any],
    yesterday_completion: Any | None,
    days_to_race: int | None,
    last_5_days_adherence: float | None,
    race_name: str | None,
) -> str | None:
    """Compose the 1-3 sentence coach brief.

    Returns ``None`` only when there's nothing useful to say (no plan AND
    no recent completions). Otherwise returns a string capped at 280 chars.
    """
    # Nothing to say
    if not todays_workouts and yesterday_completion is None:
        return None

    sentences: list[str] = []

    # 1. Today
    if todays_workouts:
        headline = min(todays_workouts, key=_headline_index)
        sentences.append(_today_sentence(headline))

    # 2. Yesterday recap
    if yesterday_completion is not None:
        s = _yesterday_sentence(yesterday_completion)
        if s:
            sentences.append(s)

    # 3. Adherence signal
    if last_5_days_adherence is not None:
        s = _adherence_sentence(last_5_days_adherence)
        if s:
            sentences.append(s)

    # 4. Days-to-race tail
    tail = _race_tail(days_to_race, race_name)
    if tail:
        sentences.append(tail)

    if not sentences:
        return None

    return _enforce_cap(sentences)
