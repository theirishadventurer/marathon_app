"""Unit tests for app.seed.plan_parser.parse_plan with cycle_one_start_date override."""

from __future__ import annotations

from datetime import date


def test_parse_plan_default_cycle_one_start_unchanged():
    """Calling parse_plan() without override produces the historical Cycle 1 anchor."""
    from app.seed.plan_parser import parse_plan

    data = parse_plan("PLAN.md")
    cycle1 = data["cycles"][0]
    assert cycle1["start_date"] == date(2026, 4, 13)
    # Total workouts unchanged from baseline
    total = sum(len(c["workouts"]) for c in data["cycles"])
    assert total == 364


def test_parse_plan_with_cycle_one_start_drops_earliest_weeks():
    """cycle_one_start_date=2026-05-06 (3 weeks late) drops the earliest weeks.

    The LAST 25 weeks of the 28-week template are retained.
    """
    from app.seed.plan_parser import parse_plan

    data = parse_plan("PLAN.md", cycle_one_start_date=date(2026, 5, 6))
    cycle1 = data["cycles"][0]
    assert cycle1["start_date"] == date(2026, 5, 6)
    assert cycle1["race_date"] == date(2026, 10, 25)

    # 28 - 3 = 25 weeks of build-up retained
    week_numbers = sorted({w["week_number"] for w in cycle1["workouts"]})
    assert len(week_numbers) == 25
    # The DROPPED weeks were the EARLIEST (lowest week numbers)
    # The first emitted template-week should be week 4 (template's W4)
    assert week_numbers[0] == 4
    assert week_numbers[-1] == 28

    # First emitted workout calendar date >= cycle 1 start
    first_workouts = [w for w in cycle1["workouts"] if w["week_number"] == 4]
    assert all(w["date"] >= date(2026, 5, 6) for w in first_workouts)
    # The Monday of week 4 should be the new start_date (2026-05-06 is a Wednesday,
    # but the new anchor is treated as the Monday of the first emitted week — verify
    # by checking that the earliest workout date in week 4 equals start_date).
    monday_of_first = min(w["date"] for w in first_workouts)
    assert monday_of_first == date(2026, 5, 6)


def test_parse_plan_cycles_two_three_unaffected_by_cycle_one_override():
    """The override only affects Cycle 1; Cycles 2 and 3 are unchanged."""
    from app.seed.plan_parser import parse_plan

    base = parse_plan("PLAN.md")
    overridden = parse_plan("PLAN.md", cycle_one_start_date=date(2026, 5, 6))
    assert base["cycles"][1] == overridden["cycles"][1]
    assert base["cycles"][2] == overridden["cycles"][2]


def test_parse_plan_cycle_one_start_equal_to_default_is_noop():
    """Passing the same start as the default produces the same cycle 1."""
    from app.seed.plan_parser import parse_plan

    base = parse_plan("PLAN.md")
    same = parse_plan("PLAN.md", cycle_one_start_date=date(2026, 4, 13))
    assert base["cycles"][0] == same["cycles"][0]
