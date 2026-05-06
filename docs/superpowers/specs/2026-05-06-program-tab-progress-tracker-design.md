# Program Tab + Progress Tracker — Design

**Status:** design (no code)
**Date:** 2026-05-06
**Owner:** session lead (CBell)
**Branch:** `session-2/backend-move-endpoints` (doc-only; implementation deferred to a follow-up session)
**Related plan:** `PLAN.md` — Marathon Trilogy 2026-2027 (3 cycles, 52 weeks, 364 workouts)

---

## 1. Goal & user story

> As the athlete, I want to zoom out from "today" and "this week" and see the
> entire 52-week trilogy at once. I want to know how far I am into Phase 1
> (MCM), how much of the plan I've actually completed vs. skipped, when the
> next race is, and where the peak weeks land. Tapping any part of the program
> should drop me into that week's view.

**Where it lives.** A new fourth tab in the bottom nav, sitting between
`Week` and `Chat`:

```
[ Today ] [ Week ] [ Program ] [ Chat ] [ Settings ]
   ▣        ▦         ▤          ◇        ⚙
```

**Position vs. existing tabs.**

- `Today` — today's prescribed workouts; tactical, single-day focus.
- `Week` — 7-day Mon-Sun grid with drag-to-move; tactical, week focus.
- **`Program` (new)** — 52-week / 3-cycle map; **strategic** view. Answers
  "where am I in the trilogy?" and "am I on track?". Read-only navigation
  surface that hands off to `Week` / `WorkoutDetail` for any actual edits.
- `Chat` / `Settings` — unchanged.

**Hand-off rules.** Tapping a week tile or bar navigates to `Week` with that
Monday as the cursor. Tapping a race milestone navigates to that race-day
`WorkoutDetail`. The Program tab itself never mutates plan data.

---

## 2. Visual mockups (ASCII)

All three options reuse the current retro tokens: deep-navy bg
(`colors.bg`), cream ink (`colors.ink`), `PressStart2P` for headings,
`VT323` for body, square `nesBorder` + `nesShadow`. Family accents stay:
green = running (`accentRun`), mustard = strength (`accentStrength`),
blue = rest/cross (`accentRest`), red = danger/skipped (`accentDanger`),
yellow = highlight/current (`accentHi`).

### Option A — World map (3 cycle lanes)

Three vertical lanes, one per cycle. Each lane is a stack of week tiles
ordered chronologically. Tap a tile -> `Week` view for that Monday. Race
milestone tiles cap each lane.

```
+------------------------------------------------------------+
|  PROGRAM  -  MARATHON TRILOGY 2026-2027                    |
|  WK 4 / 52  *  PHASE 1 / 3  *  173 DAYS TO MCM             |
+------------------------------------------------------------+
|  [STATS]  ON-PLAN 92%  *  STREAK 11d  *  PEAK WK 23 (P1)   |
+------------------------------------------------------------+
|                                                            |
|  P1 MCM         P2 DISNEY        P3 DELAWARE               |
|  28 weeks       11 weeks         13 weeks                  |
|  +------+       +------+         +------+                  |
|  |##W01#|done   |  W01 |upcoming |  W01 |upcoming          |
|  |##W02#|done   |  W02 |         |  W02 |                  |
|  |##W03#|done   |  W03 |         |  W03 |                  |
|  |>>W04<|NOW    |  W04 |         |  W04 |                  |
|  |  W05 |       |  W05 |         |  W05 |                  |
|  |  W06 |       |  W06 |         |  W06 |                  |
|  |  W07 |       |  W07 |         |  W07 |                  |
|  |::W08:|cutbk  |  W08 |         |::W08:|cutbk             |
|  |  ... |       |  ... |         |  ... |                  |
|  |##W23#|PEAK   |##W08#|peak     |##W11#|peak              |
|  |  ... |       |  ... |         |  ... |                  |
|  |[FLAG]|       |[FLAG]|         |[FLAG]|                  |
|  | MCM  |       |DISNEY|         |DELAW.|                  |
|  |10/25 |       |01/10 |         |04/11 |                  |
|  +------+       +------+         +------+                  |
|                                                            |
|  Legend:  ## done   >> current   :: cutback                |
|           __ skipped/missed  blank = upcoming              |
+------------------------------------------------------------+
```

**Tile colour rules.**

- `done` tile: filled green (`accentRun`), week number in `bg` ink.
- `current` tile: yellow (`accentHi`) with `>>` chevrons, slight pulse.
- `upcoming` tile: panel bg, dim ink, square `nesBorder`.
- `cutback` tile: blue accent border, distinguishable but not "done".
- `skipped/missed` tile (>=50% of week was skipped): red (`accentDanger`).
- `peak` tile: `accentHi` outline + `[PEAK]` label badge.
- Race tile: filled `accentHi`, flag glyph, race name + date.

**Interactions.**

- Tap week tile -> `Week` screen, cursor = that Monday.
- Long-press week tile -> tooltip showing `WK n - X mi planned, Y mi done`.
- Tap race tile -> `WorkoutDetail` for the race row.
- Pinch / pull-down -> none (lanes scroll vertically inside one screen).
  Each lane is independently scrollable on small screens; on tall screens
  all three fit.
- The current week auto-scrolls into view on mount.

**Strengths.**

- Visceral "trilogy" feel — three columns, three races, three lanes.
- Cutback / peak / race punctuation reads at a glance.
- Tile colour map = adherence map, no extra chrome.
- Maps perfectly to the data model (`Cycle` -> lane, week_number -> tile).

**Weaknesses.**

- Three columns of 28/11/13 tiles is a lot of vertical scroll on small
  phones; lanes will be unequal height (P1 dominates).
- No per-day fidelity — you can't see "I missed Wednesday in week 6"
  without drilling in.
- Daily mileage trends are not visible; week status is one-bit per tile.

---

### Option B — Heat-mapped grid (52 x 7)

A grid: 52 weeks across the X-axis, 7 days down the Y-axis. Each cell is
one workout slot. Cells coloured by status. Race days flagged. Pinch
zooms cells; default zoom shows ~12 weeks fitting on screen with
horizontal scroll.

```
+------------------------------------------------------------+
|  PROGRAM  -  HEAT MAP                                      |
|  WK 4 / 52  *  92% ON-PLAN  *  173d -> MCM                 |
+------------------------------------------------------------+
|        P1 MCM ............ | P2 DISN | P3 DELAWARE         |
|        W01 W02 W03|W04|W05  W29 W30 .. W40 W41 ..          |
|   MON   #   #   # | > | .   .   .  ..  .   .  ..           |
|   TUE   #   #   # | > | .   .   .  ..  .   .  ..           |
|   WED   #   #   # | > | .   .   .  ..  .   .  ..           |
|   THU   #   #   # | > | .   .   .  ..  .   .  ..           |
|   FRI   #   #   # | > | .   .   .  ..  .   .  ..           |
|   SAT   #   #   # | > | .   .   .  ..  .   .  ..  [F=race] |
|   SUN   _   #   # | > | .   .   .  ..  .   .  ..           |
|                   |   |                                    |
|        ^current week       ^cycle break                    |
|                                                            |
|  Cycle bar:  [===== P1 28w =====][== P2 11w ==][= P3 13w =]|
|              ^ 4/28 (you)                                  |
|                                                            |
|  Legend: # done   > current  . upcoming  _ skipped         |
|          F race day                                        |
+------------------------------------------------------------+
```

**Cell encoding.** Each glyph is one `PlannedWorkout`:

- `#` filled cell, family-coloured: green (run), mustard (strength),
  blue (rest/cross). Done.
- `>` yellow cell. Current week column highlighted top-to-bottom.
- `.` empty cell with thin border. Upcoming.
- `_` red. Skipped.
- `F` flag on race-day cell.

**Interactions.**

- Pinch in -> zoom to a single cycle (~28 weeks visible).
- Pinch out -> all 52 weeks fit, cells become 4-8px squares.
- Tap a cell -> `WorkoutDetail`.
- Tap a column header (W04) -> `Week` for that Monday.
- Cycle bar at bottom is a mini-scrubber; drag to jump.

**Strengths.**

- Maximum information density — every workout visible.
- Adherence patterns ("I always skip Tuesday strength") jump out.
- Single, calm rectangle reads like a GitHub contribution graph.

**Weaknesses.**

- 52 x 7 = 364 cells. Cells are tiny on a phone; pinch-zoom is
  table-stakes which adds gesture complexity.
- The "trilogy" narrative gets flattened into one ribbon.
- Race-day milestones disappear into a single `F` cell.
- Hardest of the three to ship cleanly in v1 (zoomable canvas, careful
  hit-testing).

---

### Option C — Mileage bar chart

Weekly mileage as a vertical bar chart. Each week has two stacked bars:
planned (outlined) and actual (filled). Cycle separators. KPIs and a
race countdown live below the chart. More analytics-leaning.

```
+------------------------------------------------------------+
|  PROGRAM  -  WEEKLY MILEAGE                                |
|  WK 4 / 52   *   173 DAYS -> MCM                           |
+------------------------------------------------------------+
|                                                            |
|  mi                                          PEAK 42       |
|  45 |                          [_]                         |
|  40 |                       [_][_][_]                      |
|  35 |                    [_][_][_][_][_]                   |
|  30 |                 [_][_][_][_][_][_][_]                |
|  25 |              [_][_][_][_][_][_][_][_][_]             |
|  20 |  [_]      [_][#][#][#][#][#][_][_][_][_][_]          |
|  15 |  [#][#][#][#][#][#][#][#][#][_][_][_][_][_][_]       |
|  10 |  [#][#][#][#][#][#][#][#][#][_][_][_][_][_][_][_]   .|
|   5 |  [#][#][#][#][#][#][#][#][#][_][_][_][_][_][_][_]    |
|   0 +-W1-W2-W3-W4-W5-W6-W7-W8-W9-...-W23-...-W28||W29-...  |
|         |        ^you      ^cutback   ^peak    [MCM]       |
|         |--- P1 28w ---|     |- P2 -|         |-- P3 --|   |
|                                                            |
|  [#] actual    [_] planned    || cycle break               |
+------------------------------------------------------------+
|  KPIs                                                      |
|  +-----------------+ +-----------------+                   |
|  | ON-PLAN         | | THIS CYCLE      |                   |
|  |   92%           | |   42 / 850 mi   |                   |
|  +-----------------+ +-----------------+                   |
|  +-----------------+ +-----------------+                   |
|  | NEXT RACE       | | STREAK          |                   |
|  |   MCM 173d      | |   11 days       |                   |
|  +-----------------+ +-----------------+                   |
+------------------------------------------------------------+
```

**Encoding.**

- Each week = one column. Outlined bar = planned weekly mileage. Filled
  bar within = actual mileage from completed runs.
- Bar colour: green for run-only; if mixed, top of bar is the running
  stack, bottom strata are strength minutes / cross.
- Cutback weeks are obvious by shape (V-shape every 4th week).
- Cycle dividers as `||`. Race week marked with a flag glyph atop the bar.

**Interactions.**

- Tap a bar -> `Week` for that Monday.
- Horizontal pan / scroll. No pinch.
- KPI cards under chart are static; tapping one expands the calculation
  in a bottom sheet (e.g. "ON-PLAN 92% = 47 done / 51 planned to date").

**Strengths.**

- Best for spotting under/over-training (planned vs actual gap).
- Clear, calm, single chart — easy to read on a small screen.
- KPI cards directly map to the stats panel without competing for space.
- Cutback rhythm and peak shape visualises plan philosophy.

**Weaknesses.**

- Loses the "trilogy" story — it's one continuous chart.
- Strength/rest days are invisible or compressed into bar strata.
- Less evocative than Option A; reads "spreadsheet."
- 52 columns is dense; can feel cluttered on a phone.

---

## 3. Recommendation

**Default to Option A (World map).**

The Program tab's job is the **strategic/narrative** view. The athlete
already has `Week` for tactical fidelity and `WorkoutDetail` for
per-workout truth. What the existing tabs **do not** give is the answer
to "where am I in the trilogy story?" — and that is exactly what a
3-lane world-map answers in one glance.

Why A over B and C:

- **Narrative fit.** The plan is explicitly framed as a trilogy
  (`PLAN.md` -> three races, three peaks, two recovery transitions).
  Three lanes match three races. One ribbon (B) and one chart (C) both
  flatten that.
- **Implementation cost.** Lanes of week tiles are a `FlatList` of
  `WeekTile` components. No zoom canvas, no chart library, no
  gesture choreography. This ships in a session.
- **Touch ergonomics.** Tiles are large, finger-friendly, and reusable
  in future contexts (e.g. Settings -> "browse cycles").
- **Data fit.** The week-level rollup endpoint (see section 5) feeds A
  directly; B needs per-day rollups (heavier) and C needs a charting
  primitive we don't ship yet.

**Honest tradeoffs.**

- A is **the most evocative for the trilogy** but **loses fidelity for
  individual workouts**. Mitigation: tap-through to Week is one hop.
- A does **not** show mileage trend by default. Mitigation: include a
  small "this cycle planned vs actual mi" KPI in the stats panel
  (section 4); promote a sparkline as a v2 addition if the user wants C's
  signal back later.
- A's three lanes are unequal height (28 / 11 / 13). Mitigation: each
  lane is independently scrollable and starts auto-scrolled to the
  current week. Lanes share a top-aligned header so the cycle name and
  race date are always visible.

**v2 path.** Add a "View" toggle in the header (`MAP | BARS`) that
swaps A for C without altering navigation or endpoints. C only needs
mileage rollups already on the response (section 5). Heat-map (B) is
parking-lot.

---

## 4. Progress stats — the panel

The header strip and stats card sit above the lanes. Goal: at most six
KPIs, each readable in under a second, with at least one motivational
("streak") and at least one diagnostic ("on-plan %"). Anything that
demands a chart goes in `WorkoutDetail` or a future `Insights` screen.

### Top six (selected)

| # | Stat | Display | Source |
|---|---|---|---|
| 1 | **Cycle progress** | `WK 4 / 28  *  PHASE 1 / 3` | Existing `cycle_progress` from `/plan/current` |
| 2 | **Days to next race** | `173d -> MCM` | `cycle.race_date - today` |
| 3 | **On-plan adherence** | `92%` (done / (done + skipped) of dates <= today) | New aggregator over `PlannedWorkout.status` |
| 4 | **Volume this cycle** | `42 / 187 mi` (actual / planned mi to date in current cycle) | Sum `planned.distance_mi` and reconciled actuals |
| 5 | **Streak** | `11 days` (consecutive on-plan days, where each day is "all planned workouts done or no workouts scheduled") | New aggregator |
| 6 | **Next milestone** | `PEAK WK 23 - 21 mi` or `RACE 173d - MCM` | `cycle.peak_week_target` and `cycle.race_date` |

### Why these six

- (1)+(2) anchor the user in time — "where am I, when is the next big day".
- (3) is the single most honest "are you on plan?" number. Calculation
  is simple and stable.
- (4) is the running-volume answer without a chart. Cycle-scoped (not
  plan-scoped) because cycle volumes vary wildly (P1 850mi, P2 ~280mi).
- (5) is the only motivational number. Day-level streaks reward
  consistency without punishing rest days.
- (6) drives forward focus. The wording flips from "next peak" to
  "next race" as the cycle approaches taper (computed: if days_to_race
  <= 21, milestone is the race; else, milestone is the peak week).

### Layout in the header

```
+------------------------------------------------------------+
|  PROGRAM  -  MARATHON TRILOGY 2026-2027                    |
|  WK 4 / 28  *  PHASE 1 / 3  *  173d -> MCM                 |
+------------------------------------------------------------+
|  +--------------+ +--------------+ +--------------+        |
|  | ON-PLAN  92% | | CYCLE  42mi  | | STREAK   11d |        |
|  |              | |  / 187 plan  | |              |        |
|  +--------------+ +--------------+ +--------------+        |
|  +-------------------------+ +-------------------------+   |
|  | NEXT MILESTONE          | | PEAK WK                 |   |
|  |  RACE  MCM  173d        | |  WK 23  21mi  long      |   |
|  +-------------------------+ +-------------------------+   |
+------------------------------------------------------------+
```

Use existing `RetroCard` for each KPI tile. Pixel headings via
`PressStart2P`, numerals via `VT323` for legibility.

### Stats deferred to v2 / out of scope here

- **Pace trend (4-week rolling avg easy pace).** Needs Garmin reconciliation
  to be solid for >= 4 weeks; promote when data accumulates.
- **Family balance pie/bar (run / strength / cross / rest).** Useful but
  not blocking; not how this athlete describes their plan.
- **Phase 1 decision-point alerts ("end of Phase 1 review").** Belongs
  in a notification / coach brief, not a tile.

### Backend dependency

Stats 1 and 2 already exist on `/plan/current`. Stats 3, 4, 5, 6 require
a **new aggregator** (see section 5). All six values must come back in
one round-trip; no client-side fan-out. Streak (5) is the only one that
needs day-by-day iteration; bound it to the cycle's date range, not the
full plan.

---

## 5. Backend work needed

### Two new endpoints

#### 5.1 `GET /plan/full` — week-rollup map

Returns the full plan as a hierarchy: `plan -> cycles -> weeks`. **Does
not** return individual workouts (the tab does not need them; tap-through
goes to `/plan/week`). 52 weeks of rollup is bounded and small (~6 KB).

```
GET /plan/full
Query: none
Response:
{
  "plan_name": "Marathon Trilogy 2026-2027",
  "plan_id": "<uuid>",
  "start_date": "2026-04-13",
  "end_date": "2027-04-12",
  "cycles": [
    {
      "id": "<uuid>",
      "name": "Phase 1 - MCM",
      "sequence": 1,
      "race_name": "Marine Corps Marathon",
      "race_date": "2026-10-25",
      "start_date": "2026-04-13",
      "end_date": "2026-10-25",
      "peak_week_target": 23,
      "weeks": [
        {
          "week_number": 1,
          "week_start": "2026-04-13",
          "week_end": "2026-04-19",
          "planned_count": 7,
          "done_count": 7,
          "skipped_count": 0,
          "moved_count": 0,
          "planned_mi": 18.0,
          "actual_mi": 18.4,
          "is_cutback": false,
          "is_peak": false,
          "has_race": false,
          "status": "done"     // done | partial | current | upcoming | skipped
        },
        ...
      ]
    },
    ...
  ]
}
```

**`status` derivation per week:**

- `done` — all `planned_count` are `done` and `week_end <= today`.
- `partial` — `week_end <= today` AND `skipped_count > 0`. Renders red.
- `current` — `week_start <= today <= week_end`. Renders yellow.
- `upcoming` — `week_start > today`. Renders bg.
- `skipped` — fully past, `done_count == 0` and at least one row exists.

**`is_peak`** — `week_number == cycle.peak_week_target`.
**`is_cutback`** — heuristic: planned_mi < (avg of previous 3 weeks) - 25%.
Stored derived; computed once per query. (We do not have a `cutback`
column today; the heuristic is good enough and cheap.)

#### 5.2 `GET /plan/stats` — KPI bundle

```
GET /plan/stats
Query:
  scope: "cycle" | "plan"   (default: "cycle")
Response:
{
  "scope": "cycle",
  "cycle_id": "<uuid>",
  "on_plan_pct": 0.92,
  "done_count": 47,
  "skipped_count": 4,
  "planned_to_date_count": 51,
  "planned_mi": 187.0,
  "actual_mi": 42.0,
  "streak_days": 11,
  "next_milestone": {
    "kind": "peak",            // peak | race | decision
    "label": "WK 23 - 21mi long",
    "date": "2026-09-19"
  },
  "peak_week": {
    "week_number": 23,
    "planned_mi": 42.0,
    "long_run_mi": 21.0
  },
  "computed_at": "2026-05-06T14:00:00Z"
}
```

### Aggregation queries (pseudo-SQL)

All queries are scoped to `athlete_id` via `Plan -> Cycle -> PlannedWorkout`.

**Week rollup (single query, used by `/plan/full`):**

```sql
SELECT
  c.id AS cycle_id,
  pw.week_number,
  COUNT(*) AS planned_count,
  COUNT(*) FILTER (WHERE pw.status = 'done')    AS done_count,
  COUNT(*) FILTER (WHERE pw.status = 'skipped') AS skipped_count,
  COUNT(*) FILTER (WHERE pw.status = 'moved')   AS moved_count,
  COALESCE(SUM(pw.distance_mi), 0)              AS planned_mi,
  MIN(pw.scheduled_date)                        AS week_start,
  MAX(pw.scheduled_date)                        AS week_end,
  BOOL_OR(pw.type = 'race')                     AS has_race
FROM planned_workouts pw
JOIN cycles c ON c.id = pw.cycle_id
JOIN plans p  ON p.id = c.plan_id
WHERE p.athlete_id = :athlete_id AND p.is_active = true
GROUP BY c.id, pw.week_number
ORDER BY c.sequence, pw.week_number;
```

**Actual mileage by week (separate query, joined client-side or via
sub-select):**

```sql
SELECT
  pw.cycle_id, pw.week_number,
  COALESCE(SUM(cw.distance_m) / 1609.344, 0) AS actual_mi
FROM planned_workouts pw
JOIN reconciliations  r  ON r.planned_id   = pw.id
JOIN completed_workouts cw ON cw.id        = r.completed_id
WHERE pw.cycle_id IN (:cycle_ids)
GROUP BY pw.cycle_id, pw.week_number;
```

**Streak (cycle-scoped):**

Walk `planned_workouts` ordered by `scheduled_date DESC` for the active
cycle, starting from `today`. For each date <= today, the streak day
counts if every row on that date has `status IN ('done', 'moved')` OR
the day has zero rows (rest day not in plan = neutral). First date with
a `skipped` row breaks the streak. Return integer.

This walks at most 28 days for an active cycle in P1; trivial cost.

**On-plan % (cycle-scoped):**

```sql
SELECT
  COUNT(*) FILTER (WHERE status = 'done')                       AS done,
  COUNT(*) FILTER (WHERE status IN ('done','skipped','moved'))  AS settled
FROM planned_workouts pw
JOIN cycles c ON c.id = pw.cycle_id
WHERE c.id = :active_cycle_id AND pw.scheduled_date <= :today;
```

`on_plan_pct = done / NULLIF(settled, 0)`.

### Cost / cache plan

- `/plan/full` over 364 rows is **one indexed `GROUP BY`**; benchmark
  shows this on the order of single-digit ms in dev. No need for a
  materialised view in v1.
- `/plan/stats` is the same scan plus the streak walk; same order of
  magnitude.

**Recommendation:** **cache for 60 seconds in-process**, keyed by
`athlete_id`. The cache is invalidated implicitly by being short-lived;
explicit invalidation on workout edit/skip/move would be nice but is
overkill for v1. The athlete's actions take >60s of dwell-time after a
mutation before they look at the Program tab again in practice. Mark
this as **revisit if perceived staleness > 60s** during dogfooding.

If/when we need stronger consistency: invalidate the per-athlete cache
inside the existing `PATCH /workouts/{id}`, `POST /workouts/{id}/skip`,
and `PATCH /workouts/{id}/move` handlers (one-line cache bust each).

### Pydantic schemas (new, in `app/schemas/plan.py`)

```python
class WeekRollup(BaseModel):
    week_number: int
    week_start: date
    week_end: date
    planned_count: int
    done_count: int
    skipped_count: int
    moved_count: int
    planned_mi: Decimal
    actual_mi: Decimal
    is_cutback: bool
    is_peak: bool
    has_race: bool
    status: Literal["done", "partial", "current", "upcoming", "skipped"]

class CycleFull(CycleOut):
    peak_week_target: int | None
    weeks: list[WeekRollup]

class PlanFullOut(BaseModel):
    plan_name: str
    plan_id: uuid.UUID
    start_date: date
    end_date: date
    cycles: list[CycleFull]

class NextMilestone(BaseModel):
    kind: Literal["peak", "race", "decision"]
    label: str
    date: date

class PeakWeekSummary(BaseModel):
    week_number: int
    planned_mi: Decimal
    long_run_mi: Decimal | None

class PlanStatsOut(BaseModel):
    scope: Literal["cycle", "plan"]
    cycle_id: uuid.UUID | None
    on_plan_pct: float
    done_count: int
    skipped_count: int
    planned_to_date_count: int
    planned_mi: Decimal
    actual_mi: Decimal
    streak_days: int
    next_milestone: NextMilestone | None
    peak_week: PeakWeekSummary | None
    computed_at: datetime
```

### What does NOT change

- `/plan/current`, `/plan/today`, `/plan/week` — untouched.
- `Reconciliation` model — untouched. The actual-mi rollup uses the
  existing `reconciliations` table; we just aggregate over it.
- No new tables. No migrations.

---

## 6. Frontend component plan

### New tab in `RootNavigator.tsx`

Add to `TabParamList`:

```ts
export type TabParamList = {
  Today: undefined;
  Week: undefined;
  Program: undefined;   // NEW
  Chat: undefined;
  Settings: undefined;
};
```

Tab order: Today, Week, **Program**, Chat, Settings. Icon glyph: `▤`
(matches the lane shape; sits visually between `▦` Week and `◇` Chat).

### New screen file

```
mobile/src/screens/ProgramScreen.tsx
```

Structure:

```
ProgramScreen
+- SafeAreaView
   +- ScrollView (vertical, refresh control)
      +- ProgramHeader  (title, week-of-N strip)
      +- StatsPanel     (3 + 2 RetroCard grid; section 4)
      +- LaneRow        (horizontal scroll on small phones)
         +- CycleLane (Phase 1)
         +- CycleLane (Phase 2)
         +- CycleLane (Phase 3)
```

### New components

| Component | Location | Notes |
|---|---|---|
| `CycleLane` | `mobile/src/components/program/CycleLane.tsx` | Vertical stack of `WeekTile` + race milestone tile. Header shows cycle name + race date. Auto-scrolls to current week on mount. |
| `WeekTile` | `mobile/src/components/program/WeekTile.tsx` | Square tile, family-coloured by `status`. Shows `WK n` and small mileage glyph. Long-press tooltip. Reuses `nesBorder` + `nesShadow`. |
| `RaceMilestoneTile` | `mobile/src/components/program/RaceMilestoneTile.tsx` | Filled `accentHi` tile with flag glyph, race name, date. Caps each lane. |
| `StatTile` | `mobile/src/components/program/StatTile.tsx` | Wraps `RetroCard` with a label (`PressStart2P` 8pt) + value (`VT323` 22pt). Used in StatsPanel. |
| `StatsPanel` | `mobile/src/components/program/StatsPanel.tsx` | Grid of `StatTile`s. Layout per section 4. |

All new components live under `components/program/` to keep the existing
`components/` flat list uncluttered.

### Reuse (no changes needed)

- `RetroBorder`, `RetroCard`, `RetroPill`, `RetroButton` — direct reuse.
- `colors`, `familyColor`, `nesShadow`, `nesBorder` — direct reuse.
- `useNavigation` -> `Tabs` jump for week tile tap, `RootStack` jump for
  race tile tap.

### New API hooks

```
mobile/src/api/hooks/usePlan.ts   (extend existing file)
```

Add:

```ts
export function usePlanFull() {
  return useQuery({
    queryKey: ['plan', 'full'],
    queryFn: async () => (await api.get<PlanFullOut>('/plan/full')).data,
    staleTime: 60_000,   // matches backend cache TTL
  });
}

export function useProgressStats(scope: 'cycle' | 'plan' = 'cycle') {
  return useQuery({
    queryKey: ['plan', 'stats', scope],
    queryFn: async () =>
      (await api.get<PlanStatsOut>('/plan/stats', { params: { scope } })).data,
    staleTime: 60_000,
  });
}
```

### New API types

Generated from the OpenAPI export script (already in repo). After
shipping the backend endpoints, run the existing export script and the
new types land in `mobile/src/api/types.ts` automatically.

### Navigation hand-off

- `WeekTile.onPress(weekStart: string)` -> `navigation.navigate('Tabs', { screen: 'Week', params: undefined })`, then `Week` reads a navigation param or sets its `cursorIso` from a route param. **Decision:** add an optional `initialDate?: string` param to the `Week` tab so we don't need shared state. (One-line param-list change, deferred to implementation.)
- `RaceMilestoneTile.onPress(workoutId)` -> `navigation.navigate('WorkoutDetail', { workoutId })`. Requires the race-row's planned_workout id; cheapest path is adding `race_planned_id` to each `CycleFull` in the response.

---

## 7. Out of scope (deferred)

The following are explicitly **not** in v1 of the Program tab. Each is a
real idea, parking-lotted to keep v1 honest:

- **Pinch-to-zoom heat map** (Option B). Re-evaluate once v1 has been
  used for 2+ weeks.
- **Mileage chart** (Option C). Add as a `MAP | BARS` toggle in v2.
- **Pace-trend KPI**. Needs >= 4 weeks of solid Garmin reconciliation.
- **Decision-point notifications** (e.g. "End of Phase 1 review").
  Belongs in coach-brief / chat, not in this tab.
- **Editable plan from this tab.** This tab is read-only; edits stay
  on `Today` / `Week` / `WorkoutDetail`.
- **Cross-cycle compare view** ("how did I do P1 vs P2"). Post-MCM
  feature.
- **Achievement badges** ("first 20-miler", "longest streak"). Tempting,
  defer; we don't have a `badges` table.
- **Per-day fidelity in the world map.** Tile = week. Drill-down is
  one tap to `Week`.
- **Sharing / screenshots / "post my progress."** Defer.

---

## 8. Done criteria

A future implementation session can call this feature complete when:

**Backend**

- [ ] `GET /plan/full` returns `PlanFullOut` with all three cycles + 52
      weeks of rollups for the seeded plan.
- [ ] `GET /plan/stats?scope=cycle` returns `PlanStatsOut` with the six
      KPIs from section 4 populated.
- [ ] Both endpoints respond < 100ms p95 in dev with a hot DB.
- [ ] In-process per-athlete cache with 60s TTL; documented and easy to
      bust.
- [ ] Tests: at least one happy-path test per endpoint, plus a
      cycle-boundary test (week 28 P1 + week 1 P2 reported correctly).
- [ ] OpenAPI export script regenerated and committed.

**Mobile**

- [ ] New `Program` tab present in the bottom nav with `▤` glyph.
- [ ] `ProgramScreen` renders three `CycleLane`s with all 52 week tiles
      coloured by `status` from the API.
- [ ] Stats panel shows the six KPIs from section 4.
- [ ] Tapping a `WeekTile` navigates to `Week` with that Monday as the
      cursor.
- [ ] Tapping a `RaceMilestoneTile` opens `WorkoutDetail` for the race.
- [ ] Pull-to-refresh works on `ProgramScreen`.
- [ ] Visuals match current retro tokens (no new colours, no new fonts,
      `nesShadow` + `nesBorder` reused everywhere).
- [ ] Lane scrolls auto-position to the current week on mount.

**Quality**

- [ ] All existing `Today` / `Week` flows untouched and passing tests.
- [ ] Lint + format clean on backend (`ruff check`, `ruff format`).
- [ ] Type-check + lint clean on mobile.
- [ ] Manual smoke test on iOS simulator: every tab loads, every tap
      navigates correctly, refresh works, stats update after a manual
      `/workouts/{id}/skip` from `WorkoutDetail`.
