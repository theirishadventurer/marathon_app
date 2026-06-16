from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.plan import Cycle, Plan
from app.models.workout import CompletedWorkout, PlannedWorkout
from app.services.plan_aggregator import build_plan_stats


@dataclass
class AthleteContext:
    snapshot: dict[str, Any]
    markdown: str


async def _active_plan(db: AsyncSession, athlete_id: uuid.UUID) -> Plan | None:
    return (
        await db.execute(
            select(Plan).where(Plan.athlete_id == athlete_id, Plan.is_active.is_(True)).limit(1)
        )
    ).scalar_one_or_none()


async def _active_cycle(db: AsyncSession, plan_id: uuid.UUID, today: date) -> Cycle | None:
    cycle = (
        await db.execute(
            select(Cycle)
            .where(Cycle.plan_id == plan_id, Cycle.start_date <= today, Cycle.end_date >= today)
            .order_by(Cycle.sequence)
            .limit(1)
        )
    ).scalar_one_or_none()
    if cycle is not None:
        return cycle
    return (
        await db.execute(
            select(Cycle)
            .where(Cycle.plan_id == plan_id, Cycle.start_date <= today)
            .order_by(Cycle.start_date.desc())
            .limit(1)
        )
    ).scalar_one_or_none()


def _wk(w: PlannedWorkout) -> dict[str, Any]:
    return {
        "id": str(w.id),
        "date": w.scheduled_date.isoformat(),
        "type": w.type.value,
        "status": w.status.value,
        "title": w.title,
        "distance_mi": float(w.distance_mi) if w.distance_mi is not None else None,
    }


async def build_athlete_context(db: AsyncSession, athlete_id: uuid.UUID) -> AthleteContext:
    """Assemble a fresh live-DB context (snapshot dict + markdown block) for the coach."""
    today = date.today()
    plan = await _active_plan(db, athlete_id)

    if plan is None:
        snapshot: dict[str, Any] = {
            "plan": None,
            "progress": None,
            "today": [],
            "week": [],
            "recent_actuals": [],
        }
        return AthleteContext(snapshot=snapshot, markdown="No plan is currently loaded.")

    cycle = await _active_cycle(db, plan.id, today)

    # Progress KPIs (reuse the aggregator; cycle scope).
    stats = await build_plan_stats(db, athlete_id, scope="cycle")

    # Today's prescribed workouts.
    today_rows = (
        (
            await db.execute(
                select(PlannedWorkout)
                .join(Cycle, PlannedWorkout.cycle_id == Cycle.id)
                .where(Cycle.plan_id == plan.id, PlannedWorkout.scheduled_date == today)
                .order_by(PlannedWorkout.scheduled_date)
            )
        )
        .scalars()
        .all()
    )

    # This week (Mon..Sun).
    week_start = today - timedelta(days=today.weekday())
    week_end = week_start + timedelta(days=6)
    week_rows = (
        (
            await db.execute(
                select(PlannedWorkout)
                .join(Cycle, PlannedWorkout.cycle_id == Cycle.id)
                .where(
                    Cycle.plan_id == plan.id,
                    PlannedWorkout.scheduled_date >= week_start,
                    PlannedWorkout.scheduled_date <= week_end,
                )
                .order_by(PlannedWorkout.scheduled_date)
            )
        )
        .scalars()
        .all()
    )

    # Recent actuals (last 14 days of Garmin-synced completions).
    recent_rows = (
        (
            await db.execute(
                select(CompletedWorkout)
                .where(
                    CompletedWorkout.athlete_id == athlete_id,
                    CompletedWorkout.activity_date >= today - timedelta(days=14),
                )
                .order_by(CompletedWorkout.activity_date.desc())
            )
        )
        .scalars()
        .all()
    )

    cycle_snap = None
    if cycle is not None:
        cycle_snap = {
            "name": cycle.name,
            "race_name": cycle.race_name,
            "race_date": cycle.race_date.isoformat(),
            "days_to_race": (cycle.race_date - today).days,
            "peak_week_target": cycle.peak_week_target,
        }

    snapshot = {
        "plan": {"name": plan.name, "philosophy_md": plan.philosophy_md, "cycle": cycle_snap},
        "progress": {
            "on_plan_pct": stats.on_plan_pct,
            "done_count": stats.done_count,
            "skipped_count": stats.skipped_count,
            "planned_mi": str(stats.planned_mi),
            "actual_mi": str(stats.actual_mi),
            "streak_days": stats.streak_days,
            "next_milestone": stats.next_milestone.label if stats.next_milestone else None,
        },
        "today": [_wk(w) for w in today_rows],
        "week": [_wk(w) for w in week_rows],
        "recent_actuals": [
            {
                "date": c.activity_date.isoformat(),
                "type": c.activity_type,
                "distance_mi": round(float(c.distance_m) / 1609.344, 2)
                if c.distance_m is not None
                else None,
                "avg_hr": c.avg_hr,
            }
            for c in recent_rows
        ],
    }

    markdown = _render_markdown(snapshot)
    return AthleteContext(snapshot=snapshot, markdown=markdown)


def _render_markdown(s: dict[str, Any]) -> str:
    lines: list[str] = []
    p = s["plan"]
    lines.append(f"## Plan: {p['name']}")
    if p["philosophy_md"]:
        lines.append(f"Philosophy: {p['philosophy_md']}")
    c = p["cycle"]
    if c:
        lines.append(
            f"Cycle **{c['name']}** — {c['race_name']} on {c['race_date']} "
            f"({c['days_to_race']}d out). Peak week target: {c['peak_week_target']}."
        )
    pr = s["progress"]
    if pr:
        lines.append(
            f"\n## Progress (cycle): {pr['on_plan_pct']:.0%} on-plan; "
            f"{pr['done_count']} done / {pr['skipped_count']} skipped; "
            f"{pr['actual_mi']} of {pr['planned_mi']} mi; streak {pr['streak_days']}d. "
            f"Next: {pr['next_milestone']}."
        )
    lines.append("\n## Today")
    lines.append(
        "\n".join(f"- {w['title']} ({w['type']}, {w['status']})" for w in s["today"]) or "- Rest"
    )
    lines.append("\n## This week")
    lines.append(
        "\n".join(
            f"- {w['date']}: {w['title']} ({w['type']}, {w['status']}) [id {w['id']}]"
            for w in s["week"]
        )
        or "- (empty)"
    )
    lines.append("\n## Recent actuals (14d)")
    rendered_actuals = []
    for a in s["recent_actuals"]:
        hr = f" @ {a['avg_hr']}bpm" if a["avg_hr"] else ""
        rendered_actuals.append(f"- {a['date']}: {a['type']} {a['distance_mi']}mi{hr}")
    lines.append("\n".join(rendered_actuals) or "- (none synced)")
    return "\n".join(lines)
