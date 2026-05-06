from datetime import date, datetime
from decimal import Decimal
from uuid import uuid4


def test_week_rollup_schema_round_trip():
    from app.schemas.plan import WeekRollup

    rollup = WeekRollup(
        week_number=1,
        week_start=date(2026, 4, 13),
        week_end=date(2026, 4, 19),
        planned_count=7,
        done_count=7,
        skipped_count=0,
        moved_count=0,
        planned_mi=Decimal("18.0"),
        actual_mi=Decimal("18.4"),
        is_cutback=False,
        is_peak=False,
        has_race=False,
        status="done",
    )
    dumped = rollup.model_dump()
    assert dumped["status"] == "done"
    assert dumped["planned_mi"] == Decimal("18.0")


def test_plan_full_out_schema_round_trip():
    from app.schemas.plan import CycleFull, PlanFullOut

    cycle_id = uuid4()
    plan_id = uuid4()
    cycle = CycleFull(
        id=cycle_id,
        name="Phase 1 - MCM",
        sequence=1,
        race_name="Marine Corps Marathon",
        race_date=date(2026, 10, 25),
        start_date=date(2026, 4, 13),
        end_date=date(2026, 10, 25),
        peak_week_target=23,
        race_planned_id=uuid4(),
        weeks=[],
    )
    plan = PlanFullOut(
        plan_name="Marathon Trilogy 2026-2027",
        plan_id=plan_id,
        start_date=date(2026, 4, 13),
        end_date=date(2027, 4, 12),
        cycles=[cycle],
    )
    dumped = plan.model_dump()
    assert dumped["plan_name"] == "Marathon Trilogy 2026-2027"
    assert dumped["cycles"][0]["peak_week_target"] == 23


def test_plan_stats_out_schema_round_trip():
    from app.schemas.plan import (
        NextMilestone,
        PeakWeekSummary,
        PlanStatsOut,
    )

    stats = PlanStatsOut(
        scope="cycle",
        cycle_id=uuid4(),
        on_plan_pct=0.92,
        done_count=47,
        skipped_count=4,
        planned_to_date_count=51,
        planned_mi=Decimal("187.0"),
        actual_mi=Decimal("42.0"),
        streak_days=11,
        next_milestone=NextMilestone(
            kind="peak",
            label="WK 23 - 21mi long",
            date=date(2026, 9, 19),
        ),
        peak_week=PeakWeekSummary(
            week_number=23,
            planned_mi=Decimal("42.0"),
            long_run_mi=Decimal("21.0"),
        ),
        computed_at=datetime(2026, 5, 6, 14, 0, 0),
    )
    dumped = stats.model_dump()
    assert dumped["streak_days"] == 11
    assert dumped["next_milestone"]["kind"] == "peak"
