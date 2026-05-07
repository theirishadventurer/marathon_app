from __future__ import annotations

from datetime import date
from decimal import Decimal
from unittest.mock import Mock


def _planned(
    type_value: str,
    distance_mi=None,
    duration_min=None,
    target_pace=None,
    family="running",
):
    """Tiny mock helper since we don't need a real ORM row."""
    m = Mock()
    m.type = Mock(value=type_value)
    m.title = type_value.replace("_", " ").title()
    m.distance_mi = Decimal(str(distance_mi)) if distance_mi is not None else None
    m.duration_min = duration_min
    m.target_pace = target_pace
    m.family = Mock(value=family)
    return m


def _completed(distance_mi=5.2, avg_pace_s_per_km=425):
    m = Mock()
    m.distance_m = Decimal(str(distance_mi * 1609.344))
    m.avg_pace_s_per_km = avg_pace_s_per_km
    m.duration_s = 1800
    return m


def test_compose_coach_brief_running_with_yesterday_and_adherence():
    from app.services.coach_brief import compose_coach_brief

    out = compose_coach_brief(
        today=date(2026, 5, 6),
        todays_workouts=[_planned("tempo", distance_mi=6.0, duration_min=55, target_pace="11:00")],
        yesterday_completion=_completed(distance_mi=5.2, avg_pace_s_per_km=425),
        days_to_race=173,
        last_5_days_adherence=0.8,
        race_name="MCM",
    )
    assert out is not None
    assert "tempo" in out.lower() or "Tempo" in out
    assert "yesterday" in out.lower() or "Yesterday" in out
    assert "MCM" in out
    assert "173" in out
    assert len(out) <= 280


def test_compose_coach_brief_rest_day():
    from app.services.coach_brief import compose_coach_brief

    out = compose_coach_brief(
        today=date(2026, 5, 6),
        todays_workouts=[_planned("rest", family="other")],
        yesterday_completion=None,
        days_to_race=173,
        last_5_days_adherence=None,
        race_name="MCM",
    )
    assert out is not None
    assert "rest" in out.lower()


def test_compose_coach_brief_returns_none_when_nothing_to_say():
    from app.services.coach_brief import compose_coach_brief

    out = compose_coach_brief(
        today=date(2026, 5, 6),
        todays_workouts=[],
        yesterday_completion=None,
        days_to_race=None,
        last_5_days_adherence=None,
        race_name=None,
    )
    assert out is None


def test_compose_coach_brief_capped_at_280_chars():
    from app.services.coach_brief import compose_coach_brief

    out = compose_coach_brief(
        today=date(2026, 5, 6),
        todays_workouts=[
            _planned("long", distance_mi=20.0, duration_min=180, target_pace="12:30")
        ],
        yesterday_completion=_completed(distance_mi=5.2, avg_pace_s_per_km=425),
        days_to_race=200,
        last_5_days_adherence=0.4,
        race_name="The Big Race With A Verbose Name",
    )
    assert out is not None
    assert len(out) <= 280


def test_compose_coach_brief_low_adherence_signal():
    from app.services.coach_brief import compose_coach_brief

    out = compose_coach_brief(
        today=date(2026, 5, 6),
        todays_workouts=[_planned("easy", distance_mi=5.0)],
        yesterday_completion=None,
        days_to_race=100,
        last_5_days_adherence=0.2,
        race_name="MCM",
    )
    assert out is not None
    # Low adherence triggers the reset/focus phrasing
    assert "reset" in out.lower() or "focus" in out.lower()
