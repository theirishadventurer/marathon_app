# Feat B — Recent Runs Strip + Coach Brief on Today — Design

**Status:** design / pending implementation
**Date:** 2026-05-07
**Owner:** session lead (CBell)
**Branch:** `session-2/backend-move-endpoints`
**Session:** 2.7 (parallel design — Feat B of A/B/C/D)
**Depends on (loose):** Feat D (visual tokens) for final polish
**Companion to:** Feat A (manual log creates new completions and must bust the same cache)

---

## 1. Goal & user story

> As the athlete on the Today screen, I want a one-glance read of (a) my
> recent runs (last ~5) and (b) a coach brief that ties today's prescription
> to recent context — e.g., "Yesterday: 5mi @ 11:30/mi · Today: tempo 6mi ·
> MCM 173 days." So I can open the app, know what I did, know what's coming,
> and know how it fits, without scrolling, tapping, or thinking.

Two placeholders on `mobile/src/screens/TodayScreen.tsx` get filled in this
feature:

- **Coach brief** card at line 78-85 (currently italic "Coach brief — wired
  in session 3").
- **Recent runs** card at line 119-126 (currently the static
  "Recent runs strip lands once `/workouts/completed/recent` ships." note).

Both surfaces become *useful and computed*, not LLM-driven. The full Daily
Coach AI ships in Session 3.

---

## 2. Two sub-features

### B1 — Recent runs strip

- **New backend endpoint** `GET /workouts/completed/recent?limit=5`.
- **New mobile hook** `useRecentCompleted(limit)` in
  `mobile/src/api/hooks/useWorkouts.ts`.
- **New mobile component** `mobile/src/components/RecentRunsStrip.tsx` —
  horizontal `ScrollView` of mini run cards.
- **Per-card content:** date glyph (`THU 5/2`), distance (`5.0mi`), pace
  (`10:45/mi`), HR (`148 bpm`) when present.
- **Tap behavior:** open a small detail bottom sheet with the raw completion
  fields (distance / duration / pace / HR / elevation / calories). We do
  *not* navigate to `WorkoutDetail` because that screen is keyed off a
  *planned* workout id; many completions are bonus/unmatched runs that have
  no planned counterpart. Routing to `WorkoutDetail` would require resolving
  the reconciliation match first, and a quick stat-sheet matches the
  glanceable intent better. (Open question — see §9.)

### B2 — Coach brief

- **No new endpoint.** Populate the existing `coach_brief: str | None` field
  on `TodayOut` (see `app/schemas/plan.py:70`), which the
  `GET /plan/today` route currently always returns as `None` (see
  `app/routes/plan.py:111`).
- **Computed, not LLM-driven.** A small heuristic combines (a) today's
  planned workouts, (b) the last completion that matched yesterday or today,
  (c) the last 5 days of plan adherence, and (d) days-to-race from the
  active cycle.
- **Output:** a 1-3 sentence string.
- **Examples:**
  - *"Tempo day — 6mi at 11:00/mi target. Yesterday's easy was solid (5.2mi,
    11:25 avg). MCM in 173 days."*
  - *"Recovery: full rest. You've been steady — 4 of last 5 days on plan.
    Use it."*
  - *"Strength A. 45min lower-body session. Last hard day was 2 days ago,
    you should feel fresh."*

The brief is rendered inside the existing `RetroBorder` card on Today —
italic placeholder text in `TodayScreen.tsx:81-83` is replaced with the
real string when present, and the whole card hides if the brief is `None`.

---

## 3. Backend endpoint shape (B1)

### Request

```
GET /workouts/completed/recent?limit=5
Authorization: Bearer <athlete jwt>
```

`limit` is a query int, default `5`, clamped server-side to `[1, 50]`.

### Response

`200 OK` — `list[CompletedWorkoutOut]`, most recent first. Reuses the
existing schema in `app/schemas/workout.py:12-27` — **no new DTO needed.**

```json
[
  {
    "id": "…",
    "garmin_activity_id": 12345,
    "activity_date": "2026-05-06",
    "started_at": "2026-05-06T06:14:00",
    "activity_type": "running",
    "family": "running",
    "duration_s": 1830,
    "distance_m": "5023.10",
    "avg_hr": 148,
    "max_hr": 162,
    "avg_pace_s_per_km": null,
    "elevation_gain_m": "12.4",
    "calories": 412
  },
  …
]
```

### Query

Lives in `app/routes/workouts.py` next to the existing `GET /workouts/{id}`
handler. No reconciliation join — the strip shows raw completions
including bonus / unmatched runs.

```sql
SELECT *
FROM completed_workouts
WHERE athlete_id = :athlete_id
ORDER BY started_at DESC
LIMIT :limit;
```

SQLAlchemy:

```python
@router.get("/completed/recent", response_model=list[CompletedWorkoutOut])
async def completed_recent(
    limit: int = Query(default=5, ge=1, le=50),
    athlete: Athlete = Depends(get_current_athlete),
    db: AsyncSession = Depends(get_db),
):
    rows = (await db.execute(
        select(CompletedWorkout)
        .where(CompletedWorkout.athlete_id == athlete.id)
        .order_by(CompletedWorkout.started_at.desc())
        .limit(limit)
    )).scalars().all()
    return [CompletedWorkoutOut.model_validate(r) for r in rows]
```

### Caching

Same pattern as `_PLAN_STATS_CACHE` in
`app/services/plan_aggregator.py:32-41`: a small in-process dict keyed on
`(athlete_id, limit)` with a 60s TTL.

Cache invalidation triggers:

1. **Garmin sync** — extend `GarminSyncService.sync_all` in
   `app/services/garmin_sync.py:239-266` to call
   `invalidate_recent_completed_cache(athlete_id)` after activities are
   committed (mirrors the existing `invalidate_plan_cache` pattern).
2. **Manual log (Feat A)** — when the manual-log endpoint commits a new
   `CompletedWorkout`, it calls the same invalidator.
3. **Reconciliation does NOT need to bust this cache** — the strip shows
   raw completions, not reconciled state.

### Auth & ordering notes

- Auth required (existing `get_current_athlete`).
- Order by `started_at DESC`, *not* `activity_date`, so two runs on the same
  day come back morning → evening in reverse order (most recent first).
- No pagination — `limit` caps it. The strip is glanceable, not a feed.

---

## 4. Coach-brief computation (B2)

### Where it lives

**New helper:** `app/services/coach_brief.py`. The route handler
`plan_today` calls one function, gets a string-or-None, and stuffs it on
`TodayOut`. Putting it in `app/routes/plan.py` directly would balloon that
file past the 500-line guideline and mix data-fetch with composition logic.
Putting it on the existing `plan_aggregator` muddies that module's
single-responsibility (week rollups + stats). A standalone service file is
the cleanest fit.

```python
# app/services/coach_brief.py
async def compose_today_brief(
    db: AsyncSession,
    athlete_id: UUID,
    today: date,
) -> str | None:
    """Return a 1-3 sentence brief for the Today screen, or None
    if we don't have enough signal."""
```

Called from `plan_today` after the workouts query (around
`app/routes/plan.py:107`):

```python
brief = await compose_today_brief(db, athlete.id, today)
return TodayOut(date=today, workouts=[...], coach_brief=brief)
```

### Inputs assembled inside the helper

1. **Today's planned workouts** (already fetched by the caller — pass
   them in to avoid a second query).
2. **Active cycle** for `race_name` + `race_date` — same `_active_plan` /
   `_active_cycle` helpers already used in `plan.py`.
3. **Yesterday's matched completion**, if any: a single
   `Reconciliation` join keyed off `PlannedWorkout.scheduled_date =
   today - 1 day`. We pull the matched `CompletedWorkout` row.
4. **Adherence over last 5 days**: count of `PlannedWorkout.status` ∈
   {`done`, `moved`} vs total non-rest planned rows for
   `[today - 5 days, today - 1 day]`. Drives the "X of last 5 on plan"
   phrase.
5. **Days since last hard day**: scan back through plan rows for the most
   recent `type ∈ {tempo, intervals, hills, mp_long, long, race}` with
   `status = done` or `status = moved` whose `scheduled_date < today`.

### Heuristic (pseudo-Python)

```python
async def compose_today_brief(db, athlete_id, today) -> str | None:
    # Active cycle (for days-to-race + race name)
    cycle = await _active_cycle_for(db, athlete_id, today)

    # Today's prescriptions (ordered)
    todays = await _todays_planned(db, athlete_id, today)

    # Yesterday's actual (single completion that matched yesterday's plan)
    yest_actual = await _yesterday_completion(db, athlete_id, today)

    # 5-day adherence
    adh_done, adh_total = await _last_n_days_adherence(db, athlete_id, today, n=5)

    # Days since last hard
    hard_gap = await _days_since_last_hard(db, athlete_id, today)

    # ── Compose ───────────────────────────────────────────────────────
    # If no plan and no recent completions, skip the brief entirely.
    if not todays and yest_actual is None:
        return None

    # Sentence 1: today.
    if todays:
        s1 = _today_sentence(todays[0])  # "Tempo day — 6mi at 11:00/mi target."
    else:
        s1 = "Rest day — nothing scheduled."

    # Sentence 2: context (pick the strongest signal we have).
    s2_candidates = []
    if yest_actual is not None:
        s2_candidates.append(_yesterday_sentence(yest_actual))
        # e.g. "Yesterday's easy was solid (5.2mi, 11:25 avg)."
    elif adh_total >= 3:
        s2_candidates.append(_adherence_sentence(adh_done, adh_total))
        # e.g. "You've been steady — 4 of last 5 days on plan."
    if hard_gap is not None and hard_gap >= 2 and _is_easy_today(todays):
        s2_candidates.append(
            f"Last hard day was {hard_gap} days ago, you should feel fresh."
        )
    s2 = s2_candidates[0] if s2_candidates else None

    # Sentence 3: race countdown (only if cycle exists & inside 365d).
    s3 = None
    if cycle is not None:
        days = (cycle.race_date - today).days
        if 0 < days <= 365:
            s3 = f"{cycle.race_name} in {days} days."

    return " ".join(p for p in (s1, s2, s3) if p)
```

### Return semantics

- Returns `None` when the athlete has no active plan **and** no recent
  completions — the Today card hides entirely.
- Returns a single string otherwise. Sentences are concatenated with a
  single space; clients render verbatim. No HTML/Markdown.
- Length envelope: target ≤ 200 chars, hard cap 280 chars (truncate with
  `…` server-side as a safety net).

### Caching

- The brief is cheap to compute (one extra `Reconciliation` join + one
  `PlannedWorkout` group query) and changes the moment a sync lands.
- Add a tiny `(athlete_id, today_iso)` LRU dict with a 60s TTL inside
  `coach_brief.py`, busted by `invalidate_plan_cache` (we already call this
  from every plan-mutating endpoint, plus we'll call it from the Garmin
  sync when activities land — same hook point as the recent-runs cache).
- Brief cache + plan_full cache + plan_stats cache + recent-completed cache
  are all owned by separate modules, so we wire one **central**
  `invalidate_for_athlete(athlete_id)` helper that fans out — better than
  threading three imports through every handler.

---

## 5. Mockup (ASCII)

Today screen with both surfaces populated. Tokens match `colors`
from `mobile/src/theme/tokens.ts`; copy follows the staycation-style
mixed-case `▸` headers introduced by `SectionHeader`
(`mobile/src/components/SectionHeader.tsx`).

```
+------------------------------------------------------------+
|  ▸ TODAY  5/7                                              |
|                                                            |
|  WHAT'S ON TAP                                             |
|  Week 4 of 28 · 173 days to MCM                            |
|                                                            |
|  ▸ Coach brief                                             |
|  +------------------------------------------------------+  |
|  |  Tempo day — 6mi at 11:00/mi target.                 |  |
|  |  Yesterday's easy was solid (5.2mi, 11:25 avg).      |  |
|  |  MCM in 173 days.                                    |  |
|  +------------------------------------------------------+  |
|                                                            |
|  +------------------------------------------------------+  |
|  | ■ TEMPO                                    [PLANNED] |  |
|  |  Tempo 6mi · 11:00/mi · 11-13                        |  |
|  |  6.0mi   54min   11:00/mi   Z3                       |  |
|  |  [WHY?] [EDIT]                                       |  |
|  +------------------------------------------------------+  |
|                                                            |
|  ▸ Recent runs                                             |
|  +------+ +------+ +------+ +------+ +------+              |
|  |TUE   | |MON   | |SUN   | |SAT   | |FRI   |  >>         |
|  | 5/6  | | 5/5  | | 5/4  | | 5/3  | | 5/2  |             |
|  |■ 5.2 | |■ 4.0 | |■12.0 | |■ — — | |■ 5.0 |             |
|  |11:25 | |11:50 | |11:10 | |REST  | |10:45 |             |
|  |148bpm| |142bpm| |155bpm| |      | |146bpm|             |
|  +------+ +------+ +------+ +------+ +------+              |
|                                                            |
+------------------------------------------------------------+
```

Mini-card spec (in `RecentRunsStrip.tsx`):

- Width ~96-104px, height ~108px, square `RetroBorder`.
- Top line: `PressStart2P 8` `THU` (day-of-week glyph) in `colors.inkDim`.
- Second line: `VT323 14` `5/2` (m/d) in `colors.inkDim`.
- Family swatch (10×10 square, `familyColor[family]`) inline with distance:
  `■ 5.2mi` rendered in `VT323 18`, `colors.ink`.
- Third line: pace `VT323 14`, `colors.inkDim`.
- Fourth line: HR `VT323 12`, `colors.inkDim`. Falls back to a single `—`
  when the activity has no HR (e.g., manual log without HR).
- Strength / cross / rest activities show duration only (`45min`) and skip
  pace/HR; family swatch uses the right accent so the user can scan.
- 8px gap between cards; the strip is `horizontal` with
  `showsHorizontalScrollIndicator={false}`.

Empty state: when the endpoint returns `[]`, render the existing single
`RetroBorder` card with `VT323 14` text "No runs yet — sync Garmin or log
one." and link the **LOG** affordance (Feat A).

---

## 6. Component plan

### Backend

| File | Change |
|------|--------|
| `app/routes/workouts.py` | Add `GET /workouts/completed/recent` handler. Reuses `CompletedWorkoutOut`. |
| `app/services/coach_brief.py` | **New** — `compose_today_brief(db, athlete_id, today)` plus private helpers. Keeps under 300 lines. |
| `app/routes/plan.py` | In `plan_today` (line 91-112): call `compose_today_brief` and pass result into `TodayOut.coach_brief`. |
| `app/services/garmin_sync.py` | After `sync_activities` commits, call the central invalidator (recent-completed cache + coach-brief cache). |
| `app/services/plan_aggregator.py` | Re-export an `invalidate_for_athlete` umbrella, or add a sibling helper in a new `app/services/cache.py`. |
| `tests/test_recent_completed.py` | **New** — happy path, limit clamp, empty list, scoping (other athlete's completions excluded). |
| `tests/test_coach_brief.py` | **New** — fixtures for each branch: today only, today + yesterday, rest day, no plan / no completions → None, race-day countdown phrase, 280-char cap. |

### Mobile

| File | Change |
|------|--------|
| `mobile/src/api/hooks/useWorkouts.ts` | Add `useRecentCompleted(limit = 5)`. Same react-query shape as `useWorkoutDetail`. `staleTime: 30_000`. Invalidation key: `['workouts', 'recent']` — busted by the Garmin sync hook and by Feat A's manual-log mutation. |
| `mobile/src/components/RecentRunsStrip.tsx` | **New.** Props: `{ items: CompletedWorkoutOut[]; onSelect?: (id: string) => void }`. Renders horizontal `ScrollView`, mini cards. |
| `mobile/src/components/RecentRunSheet.tsx` | **New** small bottom sheet showing one completion's full stat block. Reused for Tap-into-detail. |
| `mobile/src/screens/TodayScreen.tsx` | Replace lines 78-85 (coach-brief placeholder) and 119-126 (recent-runs placeholder). Wire `useRecentCompleted` and conditional render of the brief card. |
| `mobile/src/lib/format.ts` | Add `formatDayGlyph(iso) -> "THU 5/2"` and `formatPaceFromMetersAndSeconds(distance_m, duration_s) -> "10:45/mi"` helpers. The latter is needed because Garmin sync sets `avg_pace_s_per_km = null` (`app/services/garmin_sync.py:154`); we have to derive pace client-side from `distance_m / duration_s`. |

### Types

No new generated types required. `CompletedWorkoutOut` already exists in
`mobile/src/api/types.ts` (mirrors `app/schemas/workout.py:12-27`). The
existing OpenAPI export script will regenerate it on the next run; the
shape is unchanged.

---

## 7. Out of scope (deferred)

- **LLM-generated coach brief.** Session 3 swaps the heuristic for a
  Daily-Coach AI call but keeps the same `coach_brief: str | None`
  contract — the mobile side will not change.
- **Filtering recent strip by family** (run-only vs all). The strip mixes
  run + strength + other, distinguished by the family swatch color. A
  filter pill is a future polish, not v1.
- **Tap-into-`WorkoutDetail`.** Bonus / unmatched completions don't have a
  planned id, so we'd need a new "completed-only" detail screen or a
  reverse-reconciliation lookup. Both are out of scope; the small stat
  sheet covers the immediate need.
- **Cache invalidation on reconciliation.** Reconciliation only changes
  match metadata, not the raw completions list. The strip remains correct.
- **Live updating of the brief mid-day after a Garmin sync.**
  React-query's `staleTime: 30_000` plus the existing pull-to-refresh on
  `TodayScreen.tsx:38-40` are sufficient for v1.
- **Pagination / "see all".** Hard `limit` of 5 (configurable up to 50 if
  another surface ever wants it).

---

## 8. Done criteria

### Backend

- [ ] `GET /workouts/completed/recent` returns the athlete's most recent
      completed workouts, ordered by `started_at DESC`, capped by `limit`.
- [ ] Endpoint requires auth and scopes results to the requesting athlete
      (a second test athlete sees only their own rows).
- [ ] `limit` query param validates to `[1, 50]`, default `5`.
- [ ] 60s in-process cache, busted on Garmin sync and on Feat A manual-log.
- [ ] `GET /plan/today` returns a populated `coach_brief` when there is a
      plan **or** at least one recent completion; `None` only when neither.
- [ ] Coach brief never exceeds 280 characters (server-side truncation).
- [ ] All existing tests still pass; `tests/test_plan_routes.py:20`
      (currently asserts `coach_brief is None`) is updated to fixtures
      that exercise both branches.
- [ ] New tests: `test_recent_completed.py`, `test_coach_brief.py`, both
      passing under the existing `pytest` runner.
- [ ] Lint clean (`ruff check`, `ruff format`).

### Mobile

- [ ] `RecentRunsStrip` component renders 0-5 cards from
      `useRecentCompleted`. Empty state copy in place.
- [ ] Mini-card visual matches §5 mockup (dimensions, fonts, swatch
      color by family, HR fallback).
- [ ] Tap on a card opens the `RecentRunSheet` bottom sheet.
- [ ] Coach brief card renders the string when present and hides entirely
      when `coach_brief === null`.
- [ ] Pull-to-refresh on Today refreshes both the strip and the brief.
- [ ] `useRecentCompleted` cache key invalidated by the Feat A manual-log
      mutation `onSuccess`.
- [ ] `TodayScreen.tsx` no longer references the placeholder copy.

### Cross-cutting

- [ ] OpenAPI export script regenerated; mobile `openapi.json` and
      `openapi-generated.ts` updated; `mobile/src/api/types.ts` unchanged
      (no new shapes).
- [ ] Manual end-to-end against a seeded athlete: today's brief reads
      sensibly across at least 4 fixture cases (rest day, easy day, hard
      day, no-plan day).

---

## 9. Open questions

1. **Tap target on a recent-run card.** Spec above lands on a small stat
   sheet. If user feedback says "I want the planned/completed reconciled
   view," we'd add a server-side helper that returns
   `{planned_id, completed_id}` pairs and route to `WorkoutDetail` when
   matched, sheet otherwise. Worth a follow-up after first dogfooding.
2. **Pace source.** `avg_pace_s_per_km` is currently always `null` from
   Garmin sync (`app/services/garmin_sync.py:154`). Should we
   (a) derive client-side from `duration_s / distance_m`, or
   (b) backfill the column in the sync. (a) is faster to ship and
   doesn't require a backfill migration; (b) is cleaner long-term.
   Recommend (a) for v1, file a tracker issue for (b).
3. **Coach-brief tone.** The example sentences read declarative /
   informative. If the athlete prefers something more directive
   ("Hold tempo at 11:00, don't drift"), a `style` toggle in Settings is
   trivial to add later.
4. **Strength activities in the strip.** Showing them keeps total
   activity context but visually competes with run cards. If the user
   reads the strip as run-only, we add a family-pill filter. Hold the
   decision until first dogfooding.
5. **What if multiple workouts are scheduled for "today"?**
   `compose_today_brief` currently uses `todays[0]`. For days with both a
   run and a strength session this drops half the context. Easy follow-up:
   join titles in s1 ("Easy 5mi + Strength A").

---

## 10. References

- `mobile/src/screens/TodayScreen.tsx:78-85` — coach-brief placeholder
- `mobile/src/screens/TodayScreen.tsx:119-126` — recent-runs placeholder
- `app/schemas/plan.py:67-70` — `TodayOut.coach_brief` field already exists
- `app/routes/plan.py:91-112` — `plan_today` handler, currently always
  emits `coach_brief=None`
- `app/schemas/workout.py:12-27` — `CompletedWorkoutOut` (reused as-is)
- `app/services/plan_aggregator.py:31-41` — cache + invalidation pattern
  to mirror
- `app/services/garmin_sync.py:107-167` — sync-activities path (cache bust
  hook here)
- `app/services/reconciler.py` — used to look up "yesterday's matched
  completion" inside the brief helper
- `mobile/src/components/SectionHeader.tsx` — section header convention
- `mobile/src/components/WorkoutCard.tsx` — visual reference for mini-card
  styling
- `mobile/src/components/program/StatTile.tsx` — compact stat-tile
  reference for the mini-card layout
- `mobile/src/lib/format.ts` — existing format helpers (we extend with
  `formatDayGlyph` and `formatPaceFromMetersAndSeconds`)
- `mobile/src/api/hooks/usePlan.ts` — react-query hook pattern to mirror
  for `useRecentCompleted`
- `mobile/src/theme/tokens.ts` — color tokens used in the mockup
