"""Parse PLAN.md into structured data for seeding the database."""

from __future__ import annotations

import re
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation
from pathlib import Path

# Hardcoded cycle anchor dates — do NOT derive from PLAN.md
CYCLES = [
    {
        "name": "Phase 1 — MCM Build",
        "sequence": 1,
        "race_name": "Marine Corps Marathon",
        "race_date": date(2026, 10, 25),
        "start_date": date(2026, 5, 25),
        "weeks": 22,
    },
    {
        "name": "Phase 2 — Disney Build",
        "sequence": 2,
        "race_name": "Walt Disney World Marathon",
        "race_date": date(2027, 1, 10),
        "start_date": date(2026, 10, 26),
        "weeks": 11,
    },
    {
        "name": "Phase 3 — Delaware Build",
        "sequence": 3,
        "race_name": "Coastal Delaware Marathon",
        "race_date": date(2027, 4, 11),
        "start_date": date(2027, 1, 11),
        "weeks": 13,
    },
]

DAY_OFFSETS = {
    "Mon": 0,
    "Tue": 1,
    "Wed": 2,
    "Thu": 3,
    "Fri": 4,
    "Sat": 5,
    "Sun": 6,
}

# Title templates per workout type
_TITLE_MAP = {
    "easy": "Easy Run",
    "long": "Long Run",
    "tempo": "Tempo Run",
    "intervals": "Intervals",
    "hills": "Hill Repeats",
    "mp_long": "MP Long Run",
    "recovery": "Recovery Run",
    "strides": "Strides",
    "race": "Race Day",
    "strength_a": "Strength A",
    "strength_b": "Strength B",
    "cross": "Cross Training",
    "rest": "Rest Day",
}


def _build_title(workout_type: str, dist: Decimal | None) -> str:
    base = _TITLE_MAP.get(workout_type, workout_type.replace("_", " ").title())
    if dist is not None:
        return f"{base} - {dist}mi"
    return base


def _parse_athlete_yaml(yaml_block: str) -> dict:
    """Parse the YAML-like athlete profile block."""
    athlete: dict = {}

    # name
    m = re.search(r'^name:\s*"(.+?)"', yaml_block, re.MULTILINE)
    name = m.group(1) if m else ""
    athlete["name"] = "Marathon Runner" if name == "[FILL IN]" else name

    # email
    m = re.search(r'^email:\s*"(.+?)"', yaml_block, re.MULTILINE)
    email = m.group(1) if m else ""
    athlete["email"] = "runner@marathon.dev" if email == "[FILL IN]" else email

    # hr_zones
    zones: dict[str, list[int]] = {}
    for zm in re.finditer(r"(z\d):\s*\[(\d+),\s*(\d+)\]", yaml_block):
        zones[zm.group(1)] = [int(zm.group(2)), int(zm.group(3))]
    athlete["hr_zones"] = zones

    # pace_targets
    paces: dict[str, str] = {}
    for pm in re.finditer(r'(\w+):\s*"([^"]+)"', yaml_block):
        key = pm.group(1)
        if key not in ("name", "email") and key != "injury_notes_md":
            paces[key] = pm.group(2)
    athlete["pace_targets"] = paces

    # injury_notes — everything after injury_notes_md: |
    inj_match = re.search(r"injury_notes_md:\s*\|\n((?:[ \t]+.+\n?)+)", yaml_block)
    athlete["injury_notes"] = inj_match.group(1).strip() if inj_match else ""

    return athlete


def _parse_philosophy(text: str) -> str:
    """Extract the Plan Philosophy markdown code block."""
    m = re.search(
        r"## Plan Philosophy.*?```markdown\s*\n(.*?)```",
        text,
        re.DOTALL,
    )
    return m.group(1).strip() if m else ""


def _parse_workout_tables(text: str) -> list[list[dict]]:
    """Extract workout tables from each phase's code block.

    Returns a list of 3 lists (one per phase), each containing raw workout dicts.
    """
    # Find the three phase code blocks — they come after Phase N headers
    # Each is a ``` ... ``` block that contains WEEK lines and workout lines
    phase_sections = re.split(r"^# Phase \d", text, flags=re.MULTILINE)
    # phase_sections[0] is everything before Phase 1; [1], [2], [3] are the phases

    all_phases: list[list[dict]] = []
    for section in phase_sections[1:]:
        # Find the code block in this section
        code_match = re.search(r"```\n(.*?)```", section, re.DOTALL)
        if not code_match:
            continue
        code_block = code_match.group(1)
        workouts = _parse_code_block(code_block)
        all_phases.append(workouts)

    return all_phases


def _parse_code_block(block: str) -> list[dict]:
    """Parse a single workout code block into a list of raw workout dicts."""
    workouts: list[dict] = []
    current_week = 0

    for line in block.strip().split("\n"):
        line = line.strip()
        if not line:
            continue

        # Check for WEEK header
        week_match = re.match(r"^WEEK\s+(\d+)", line)
        if week_match:
            current_week = int(week_match.group(1))
            continue

        # Parse workout line: Day | type | dist | dur | description | intent
        parts = [p.strip() for p in line.split("|")]
        if len(parts) < 6:
            continue

        day_str = parts[0][:3]  # e.g., "Mon"
        workout_type = parts[1]
        dist_str = parts[2]
        dur_str = parts[3]
        description = parts[4]
        intent = parts[5] if len(parts) > 5 else ""

        # Parse distance
        dist: Decimal | None = None
        if dist_str:
            try:
                dist = Decimal(dist_str)
            except InvalidOperation:
                dist = None

        # Parse duration
        dur: int | None = None
        if dur_str:
            try:
                dur = int(dur_str)
            except ValueError:
                dur = None

        workouts.append(
            {
                "week_number": current_week,
                "day": day_str,
                "type": workout_type,
                "distance_mi": dist,
                "duration_min": dur,
                "description_md": description,
                "intent_md": intent,
            }
        )

    return workouts


def parse_plan(plan_path: str, cycle_one_start_date: date | None = None) -> dict:
    """Parse PLAN.md and return structured data for seeding.

    Args:
        plan_path: Path to PLAN.md (absolute or relative).
        cycle_one_start_date: Optional override for Cycle 1's anchor.
            When supplied, Cycle 1 is shortened from its hardcoded 28-week
            template by dropping the EARLIEST weeks; the LAST
            ``(race_date - cycle_one_start_date) // 7`` weeks of the template
            are retained, with their calendar dates re-anchored so that
            template-week N's Monday equals the new start (where N is the
            first surviving template week). Cycles 2 and 3 are unaffected.

    Returns:
        Dict with athlete, philosophy, and cycles (including workouts with dates).
    """
    text = Path(plan_path).read_text(encoding="utf-8")

    # --- Athlete profile ---
    yaml_match = re.search(r"```yaml\s*\n(.*?)```", text, re.DOTALL)
    athlete = _parse_athlete_yaml(yaml_match.group(1)) if yaml_match else {}

    # --- Philosophy ---
    philosophy = _parse_philosophy(text)

    # --- Workout tables ---
    phase_workouts = _parse_workout_tables(text)

    # --- Build cycles with dated workouts ---
    cycles: list[dict] = []
    for i, cycle_meta in enumerate(CYCLES):
        raw_workouts = phase_workouts[i] if i < len(phase_workouts) else []
        start = cycle_meta["start_date"]
        end = cycle_meta["race_date"]  # race day is end of cycle

        # Reseed Cycle 1 only when an override is supplied AND it differs from default.
        is_cycle1 = cycle_meta["sequence"] == 1
        if is_cycle1 and cycle_one_start_date is not None and cycle_one_start_date != start:
            start, raw_workouts = _reanchor_cycle_one(
                raw_workouts=raw_workouts,
                template_total_weeks=cycle_meta["weeks"],
                race_date=end,
                new_start=cycle_one_start_date,
            )

        # Calendar dates are computed relative to the FIRST surviving template
        # week (week_offset=0 lands on ``start``).
        first_week_number = raw_workouts[0]["week_number"] if raw_workouts else 1

        dated_workouts: list[dict] = []
        for w in raw_workouts:
            day_offset = DAY_OFFSETS.get(w["day"], 0)
            week_offset = w["week_number"] - first_week_number
            workout_date = start + timedelta(weeks=week_offset, days=day_offset)
            title = _build_title(w["type"], w["distance_mi"])

            dated_workouts.append(
                {
                    "week_number": w["week_number"],
                    "day": w["day"],
                    "type": w["type"],
                    "date": workout_date,
                    "distance_mi": w["distance_mi"],
                    "duration_min": w["duration_min"],
                    "title": title,
                    "description_md": w["description_md"],
                    "intent_md": w["intent_md"],
                }
            )

        cycles.append(
            {
                "name": cycle_meta["name"],
                "sequence": cycle_meta["sequence"],
                "race_name": cycle_meta["race_name"],
                "race_date": cycle_meta["race_date"],
                "start_date": start,
                "end_date": end,
                "workouts": dated_workouts,
            }
        )

    return {
        "athlete": athlete,
        "philosophy": philosophy,
        "cycles": cycles,
    }


def _reanchor_cycle_one(
    *,
    raw_workouts: list[dict],
    template_total_weeks: int,
    race_date: date,
    new_start: date,
) -> tuple[date, list[dict]]:
    """Drop earliest weeks of a Cycle 1 template to fit a later start date.

    Returns the (possibly clamped) anchor date and the surviving raw workouts.
    Surviving workouts are the LAST ``weeks_in_cycle`` template weeks; their
    ``week_number`` values are preserved (the FIRST surviving week's number is
    therefore ``template_total_weeks - weeks_in_cycle + 1``).
    """
    days_to_race = (race_date - new_start).days
    # Race day is the Sunday at the end of the final week, so we use ceiling
    # division to count the partial last week (matches the template, where
    # 195 days from default start spans 28 calendar weeks Mon→Sun).
    weeks_in_cycle = max(1, min(template_total_weeks, (days_to_race + 6) // 7))
    first_surviving_week = template_total_weeks - weeks_in_cycle + 1

    surviving = [w for w in raw_workouts if w["week_number"] >= first_surviving_week]
    return new_start, surviving
