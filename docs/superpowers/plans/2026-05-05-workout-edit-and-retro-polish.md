# Workout Edit + NES Retro Polish — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship in-place workout editing (with displaced-original prompt + AI rebalance) on top of a full NES-classic retro restyle of the mobile app.

**Architecture:**
- Backend: one additive JSONB column (`original_snapshot_json`), one PATCH endpoint, one POST `reschedule-original` endpoint that wraps the existing Plan Adapter agent. Existing apply-move endpoint extended to delete reschedule-created rows on cancel via a `proposal_state_json.created_by` sentinel.
- Mobile: `theme/retro.ts` + four primitive components (`RetroButton/Pill/Card/Border`) drive a system-wide NES restyle (Press Start 2P + VT323 fonts, 2px hard borders, mechanical-press buttons). New `EditQuestSheet` and chained `DisplacedSheet` wire onto every WorkoutCard. Existing drag-to-move and ProposalSheet are kept and restyled.

**Tech Stack:**
- Backend: FastAPI, SQLAlchemy async, Alembic, Pydantic, Anthropic SDK, pytest.
- Mobile: Expo SDK 54, React Native 0.81, TypeScript strict, NativeWind v4, `@gorhom/bottom-sheet`, React Query, react-native-reanimated v4, `expo-font`.

**Validation conventions:**
- **Backend tasks** are TDD: write failing pytest, verify red, implement, verify green, commit.
- **Mobile tasks** use `npx tsc --noEmit` as the validation gate (no jest infra in this codebase yet — adding it is out of scope). Visual restyle tasks add a manual smoke step you can do once Expo is running on `:19006`.

**Spec:** `docs/superpowers/specs/2026-05-05-workout-edit-and-retro-polish-design.md`

---

## File map

### Backend (created)
- `alembic/versions/<auto>_add_original_snapshot_json.py`
- `app/schemas/edit.py`
- `tests/test_edit_workout.py`
- `tests/test_reschedule_original.py`

### Backend (modified)
- `app/models/workout.py` — add `original_snapshot_json` column to `PlannedWorkout`
- `app/schemas/plan.py` — extend `PlannedWorkoutOut` with `original_snapshot`
- `app/routes/workouts.py` — add PATCH + reschedule-original; extend apply-move cancel
- `app/services/agents/plan_adapter.py` — write `created_by` sentinel into `proposal_state_json`
- `mobile/openapi.json` — regenerated

### Mobile (created)
- `mobile/assets/fonts/PressStart2P-Regular.ttf`
- `mobile/assets/fonts/VT323-Regular.ttf`
- `mobile/src/theme/retro.ts`
- `mobile/src/components/retro/RetroButton.tsx`
- `mobile/src/components/retro/RetroPill.tsx`
- `mobile/src/components/retro/RetroCard.tsx`
- `mobile/src/components/retro/RetroBorder.tsx`
- `mobile/src/components/EditQuestSheet.tsx`
- `mobile/src/components/DisplacedSheet.tsx`
- `mobile/src/api/hooks/useEditWorkout.ts`
- `mobile/src/api/hooks/useRescheduleOriginal.ts`

### Mobile (modified)
- `mobile/package.json`, `mobile/app.json` — `expo-font` config
- `mobile/src/theme/tokens.ts` — NES palette
- `mobile/tailwind.config.js` — match palette
- `mobile/src/api/types.ts` — add `original_snapshot` field
- `mobile/App.tsx` — load fonts via `useFonts`
- `mobile/src/components/{WorkoutCard,WhySheet,ProposalSheet,DayCard,DraggableWeekList}.tsx`
- `mobile/src/screens/{LoginScreen,TodayScreen,WeekScreen,WorkoutDetailScreen,SettingsScreen,WorkoutDetailScreen}.tsx`

---

## Phase A — Backend foundation

### Task A1: Add `original_snapshot_json` column to `PlannedWorkout`

**Files:**
- Modify: `app/models/workout.py`
- Create: `alembic/versions/<auto>_add_original_snapshot_json.py`
- Test: `tests/test_edit_workout.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_edit_workout.py`:

```python
import uuid

import pytest
from sqlalchemy import select

from app.models.workout import PlannedWorkout


@pytest.mark.asyncio
async def test_planned_workout_has_original_snapshot_column(seeded_db):
    """The planned_workouts table must have an original_snapshot_json column,
    nullable, defaulting to None on insert."""
    result = await seeded_db.execute(select(PlannedWorkout).limit(1))
    workout = result.scalar_one()
    assert hasattr(workout, "original_snapshot_json")
    assert workout.original_snapshot_json is None
```

Reuse the `seeded_db` fixture from `tests/conftest.py` (it already seeds the plan).

- [ ] **Step 2: Run test, verify fail**

Run: `docker compose exec -T api pytest tests/test_edit_workout.py::test_planned_workout_has_original_snapshot_column -v`
Expected: FAIL with `AttributeError: 'PlannedWorkout' object has no attribute 'original_snapshot_json'`.

- [ ] **Step 3: Add the column to the SQLAlchemy model**

In `app/models/workout.py`, find the `PlannedWorkout` class. Add after the existing `intent_md` field:

```python
    original_snapshot_json: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB, nullable=True, default=None
    )
```

(`JSONB`, `dict`, `Any` are already imported at the top of the file.)

- [ ] **Step 4: Generate the Alembic migration**

Run: `docker compose exec -T api alembic revision --autogenerate -m "add original_snapshot_json"`

Inspect the generated file in `alembic/versions/` — it should contain a single `op.add_column('planned_workouts', sa.Column('original_snapshot_json', postgresql.JSONB(astext_type=sa.Text()), nullable=True))` and matching `op.drop_column` in the downgrade.

- [ ] **Step 5: Apply the migration**

Run: `docker compose exec -T api alembic upgrade head`

Confirm: `docker compose exec -T db psql -U marathon -d marathon -c "\d planned_workouts" | grep original_snapshot_json` — should show the column.

- [ ] **Step 6: Run test, verify pass**

Run: `docker compose exec -T api pytest tests/test_edit_workout.py::test_planned_workout_has_original_snapshot_column -v`
Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add app/models/workout.py alembic/versions/ tests/test_edit_workout.py
git commit -m "feat(backend): add original_snapshot_json column to planned_workouts"
```

---

### Task A2: Extend `PlannedWorkoutOut` with `original_snapshot`

**Files:**
- Modify: `app/schemas/plan.py:10-27` (the `PlannedWorkoutOut` class)
- Test: `tests/test_edit_workout.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/test_edit_workout.py`:

```python
from app.schemas.plan import PlannedWorkoutOut


def test_planned_workout_out_has_original_snapshot_field():
    fields = PlannedWorkoutOut.model_fields
    assert "original_snapshot" in fields
    # nullable
    annot = fields["original_snapshot"].annotation
    assert "None" in str(annot) or annot is type(None) or "Optional" in str(annot)
```

- [ ] **Step 2: Run test, verify fail**

Run: `docker compose exec -T api pytest tests/test_edit_workout.py::test_planned_workout_out_has_original_snapshot_field -v`
Expected: FAIL with `assert "original_snapshot" in {...}`.

- [ ] **Step 3: Extend the schema**

In `app/schemas/plan.py`, modify `PlannedWorkoutOut` — add a field that aliases the JSONB column:

```python
from pydantic import BaseModel, ConfigDict, Field


class PlannedWorkoutOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    # ... existing fields ...
    intent_md: str
    original_snapshot: dict | None = Field(default=None, alias="original_snapshot_json")
```

Make sure `populate_by_name=True` is added to `model_config` so Pydantic accepts both names:

```python
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)
```

- [ ] **Step 4: Run test, verify pass**

Run: `docker compose exec -T api pytest tests/test_edit_workout.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add app/schemas/plan.py tests/test_edit_workout.py
git commit -m "feat(backend): expose original_snapshot on PlannedWorkoutOut"
```

---

### Task A3: Add edit + reschedule request schemas

**Files:**
- Create: `app/schemas/edit.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/test_edit_workout.py`:

```python
from datetime import date

from app.schemas.edit import EditWorkoutRequest, RescheduleOriginalRequest
from app.models.workout import WorkoutType


def test_edit_request_accepts_partial_fields():
    req = EditWorkoutRequest(type=WorkoutType.easy)
    assert req.type == WorkoutType.easy
    assert req.distance_mi is None
    assert req.duration_min is None
    assert req.title is None


def test_edit_request_rejects_negative_distance():
    import pytest as _p
    with _p.raises(ValueError):
        EditWorkoutRequest(distance_mi=-1)


def test_reschedule_request_round_trips_date():
    req = RescheduleOriginalRequest(new_date=date(2026, 5, 8))
    assert req.new_date == date(2026, 5, 8)
```

- [ ] **Step 2: Run test, verify fail**

Run: `docker compose exec -T api pytest tests/test_edit_workout.py -v -k "edit_request or reschedule_request"`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.schemas.edit'`.

- [ ] **Step 3: Create the schema module**

Create `app/schemas/edit.py`:

```python
from __future__ import annotations

from datetime import date
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.models.workout import WorkoutType


class EditWorkoutRequest(BaseModel):
    """All fields optional — only those passed get updated."""

    model_config = ConfigDict(extra="forbid")

    type: WorkoutType | None = None
    distance_mi: Decimal | None = Field(default=None, ge=0, le=100)
    duration_min: int | None = Field(default=None, ge=0, le=600)
    title: str | None = Field(default=None, min_length=1, max_length=200)


class RescheduleOriginalRequest(BaseModel):
    new_date: date


class RescheduleOriginalResponse(BaseModel):
    new_workout_id: str
    proposal: dict  # ProposalOut shape; left loose to avoid circular import
```

- [ ] **Step 4: Run test, verify pass**

Run: `docker compose exec -T api pytest tests/test_edit_workout.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add app/schemas/edit.py tests/test_edit_workout.py
git commit -m "feat(backend): add EditWorkoutRequest + RescheduleOriginalRequest schemas"
```

---

## Phase B — Backend endpoints

### Task B1: `PATCH /workouts/{id}` happy path

**Files:**
- Modify: `app/routes/workouts.py` (add new route)
- Test: `tests/test_edit_workout.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/test_edit_workout.py`:

```python
@pytest.mark.asyncio
async def test_patch_workout_changes_type_and_snapshots(client, athlete_token, seeded_db):
    # Pick the first planned strength workout
    result = await seeded_db.execute(
        select(PlannedWorkout).where(PlannedWorkout.type == "strength_a").limit(1)
    )
    workout = result.scalar_one()
    wid = str(workout.id)

    response = await client.patch(
        f"/workouts/{wid}",
        json={"type": "easy", "distance_mi": 5.0, "duration_min": 50, "title": "Easy run"},
        headers={"Authorization": f"Bearer {athlete_token}"},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["type"] == "easy"
    assert body["family"] == "running"
    assert body["distance_mi"] == "5.0"
    assert body["duration_min"] == 50
    assert body["title"] == "Easy run"
    snap = body["original_snapshot"]
    assert snap is not None
    assert snap["type"] == "strength_a"
    assert snap["family"] == "strength"
```

The `client` and `athlete_token` fixtures already exist in `tests/conftest.py` (used by `test_move_endpoints.py`).

- [ ] **Step 2: Run test, verify fail**

Run: `docker compose exec -T api pytest tests/test_edit_workout.py::test_patch_workout_changes_type_and_snapshots -v`
Expected: FAIL — 405 Method Not Allowed.

- [ ] **Step 3: Add the PATCH route**

In `app/routes/workouts.py`, add after the existing `skip_workout` route:

```python
from app.lib.workout_family import family_for_planned
from app.schemas.edit import EditWorkoutRequest


SNAPSHOT_FIELDS = ("type", "family", "distance_mi", "duration_min",
                   "title", "target_pace", "target_hr_zone")


def _snapshot_of(w: PlannedWorkout) -> dict:
    return {
        "type": w.type.value if w.type else None,
        "family": w.family.value if w.family else None,
        "distance_mi": str(w.distance_mi) if w.distance_mi is not None else None,
        "duration_min": w.duration_min,
        "title": w.title,
        "target_pace": w.target_pace,
        "target_hr_zone": w.target_hr_zone,
    }


@router.patch("/{workout_id}", response_model=PlannedWorkoutOut)
async def edit_workout(
    workout_id: uuid.UUID,
    body: EditWorkoutRequest,
    athlete: Athlete = Depends(get_current_athlete),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(PlannedWorkout)
        .join(Cycle, PlannedWorkout.cycle_id == Cycle.id)
        .join(Plan, Cycle.plan_id == Plan.id)
        .where(PlannedWorkout.id == workout_id, Plan.athlete_id == athlete.id)
    )
    planned = result.scalar_one_or_none()
    if planned is None:
        raise HTTPException(status_code=404, detail="Workout not found")
    if planned.status in (WorkoutStatus.done, WorkoutStatus.skipped):
        raise HTTPException(status_code=409, detail=f"Cannot edit a {planned.status.value} workout")

    updates = body.model_dump(exclude_unset=True)
    if not updates:
        return planned  # nothing to do

    # Snapshot pre-edit state on the FIRST edit only
    if planned.original_snapshot_json is None:
        planned.original_snapshot_json = _snapshot_of(planned)

    if "type" in updates:
        planned.type = updates["type"]
        planned.family = family_for_planned(updates["type"])
    if "distance_mi" in updates:
        planned.distance_mi = updates["distance_mi"]
    if "duration_min" in updates:
        planned.duration_min = updates["duration_min"]
    if "title" in updates:
        planned.title = updates["title"]

    await db.commit()
    await db.refresh(planned)
    return planned
```

- [ ] **Step 4: Run test, verify pass**

Run: `docker compose exec -T api pytest tests/test_edit_workout.py::test_patch_workout_changes_type_and_snapshots -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add app/routes/workouts.py tests/test_edit_workout.py
git commit -m "feat(backend): PATCH /workouts/{id} edits planned workout + snapshots first edit"
```

---

### Task B2: PATCH error and idempotency cases

**Files:**
- Test: `tests/test_edit_workout.py`

- [ ] **Step 1: Write the failing tests**

Append:

```python
@pytest.mark.asyncio
async def test_patch_workout_404_for_nonexistent(client, athlete_token):
    response = await client.patch(
        "/workouts/00000000-0000-0000-0000-000000000000",
        json={"type": "easy"},
        headers={"Authorization": f"Bearer {athlete_token}"},
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_patch_workout_409_for_done(client, athlete_token, seeded_db):
    result = await seeded_db.execute(select(PlannedWorkout).limit(1))
    workout = result.scalar_one()
    workout.status = "done"
    await seeded_db.commit()
    response = await client.patch(
        f"/workouts/{workout.id}",
        json={"type": "easy"},
        headers={"Authorization": f"Bearer {athlete_token}"},
    )
    assert response.status_code == 409


@pytest.mark.asyncio
async def test_patch_workout_snapshot_preserved_on_second_edit(
    client, athlete_token, seeded_db
):
    result = await seeded_db.execute(
        select(PlannedWorkout).where(PlannedWorkout.type == "strength_a").limit(1)
    )
    workout = result.scalar_one()
    wid = str(workout.id)

    # First edit: strength_a -> easy
    r1 = await client.patch(
        f"/workouts/{wid}",
        json={"type": "easy", "distance_mi": 5},
        headers={"Authorization": f"Bearer {athlete_token}"},
    )
    snap1 = r1.json()["original_snapshot"]

    # Second edit: easy -> tempo
    r2 = await client.patch(
        f"/workouts/{wid}",
        json={"type": "tempo"},
        headers={"Authorization": f"Bearer {athlete_token}"},
    )
    snap2 = r2.json()["original_snapshot"]

    # Snapshot must NOT have been overwritten — still strength_a
    assert snap1 == snap2
    assert snap2["type"] == "strength_a"
```

- [ ] **Step 2: Run tests, verify pass**

These should all pass with the Task B1 implementation already in place (the snapshot-only-on-first-edit logic is already there). If any fail, fix and re-run.

Run: `docker compose exec -T api pytest tests/test_edit_workout.py -v`
Expected: ALL PASS.

- [ ] **Step 3: Commit**

```bash
git add tests/test_edit_workout.py
git commit -m "test(backend): PATCH workout 404/409/snapshot-idempotency cases"
```

---

### Task B3: `created_by` sentinel on Plan Adapter proposal

**Files:**
- Modify: `app/services/agents/plan_adapter.py:179-...` (the `propose_rebalance` function — find where it persists to `agent_messages`)
- Test: `tests/test_plan_adapter.py` (add new test)

- [ ] **Step 1: Inspect the existing persist logic**

In `app/services/agents/plan_adapter.py`, find where `proposal_state_json` is built before being saved into `AgentMessage`. The current shape stores `{proposal_id, options, summary, new_date, ...}`. We need to add an optional `created_by` field that the caller can pass.

- [ ] **Step 2: Write the failing test**

Append to `tests/test_plan_adapter.py`:

```python
@pytest.mark.asyncio
async def test_propose_rebalance_accepts_created_by_tag(monkeypatch, seeded_db):
    """When propose_rebalance is called with created_by='reschedule_original',
    the persisted AgentMessage.proposal_state_json carries that tag."""
    # ... mock anthropic, call propose_rebalance with created_by, assert tag
```

(Look at the existing `test_propose_rebalance_*` test for the monkeypatch pattern; copy it.)

- [ ] **Step 3: Run test, verify fail**

Run: `docker compose exec -T api pytest tests/test_plan_adapter.py -v -k "created_by"`
Expected: FAIL — `propose_rebalance() got an unexpected keyword argument 'created_by'`.

- [ ] **Step 4: Update `propose_rebalance` signature**

Change the function signature:

```python
async def propose_rebalance(
    db: AsyncSession,
    athlete_id: uuid.UUID,
    workout_id: uuid.UUID,
    new_date: date,
    *,
    created_by: str | None = None,
) -> dict[str, Any]:
```

In the body, find where the `proposal_state_json` dict is built before the AgentMessage insert. Add:

```python
    if created_by is not None:
        proposal_state["created_by"] = created_by
```

(Adjust to match the actual variable name used.)

- [ ] **Step 5: Run test, verify pass**

Run: `docker compose exec -T api pytest tests/test_plan_adapter.py -v`
Expected: PASS — both old and new tests.

- [ ] **Step 6: Commit**

```bash
git add app/services/agents/plan_adapter.py tests/test_plan_adapter.py
git commit -m "feat(backend): tag proposals with created_by sentinel"
```

---

### Task B4: `POST /workouts/{id}/reschedule-original` endpoint

**Files:**
- Modify: `app/routes/workouts.py`
- Test: `tests/test_reschedule_original.py` (new)

- [ ] **Step 1: Write the failing test**

Create `tests/test_reschedule_original.py`:

```python
import datetime
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy import select

from app.models.agent import AgentMessage
from app.models.workout import PlannedWorkout, WorkoutStatus, WorkoutType


@pytest.mark.asyncio
async def test_reschedule_original_creates_row_and_returns_proposal(
    client, athlete_token, seeded_db
):
    # First, edit a strength workout into a run so a snapshot exists.
    result = await seeded_db.execute(
        select(PlannedWorkout).where(PlannedWorkout.type == "strength_a").limit(1)
    )
    edited = result.scalar_one()
    wid = str(edited.id)

    await client.patch(
        f"/workouts/{wid}",
        json={"type": "easy", "distance_mi": 5},
        headers={"Authorization": f"Bearer {athlete_token}"},
    )

    fake_proposal = {
        "proposal_id": "11111111-1111-1111-1111-111111111111",
        "summary": "fake",
        "options": [],
        "created_by": "reschedule_original",
    }

    with patch(
        "app.routes.workouts.propose_rebalance",
        AsyncMock(return_value=fake_proposal),
    ):
        response = await client.post(
            f"/workouts/{wid}/reschedule-original",
            json={"new_date": (edited.scheduled_date + datetime.timedelta(days=2)).isoformat()},
            headers={"Authorization": f"Bearer {athlete_token}"},
        )

    assert response.status_code == 200, response.text
    body = response.json()
    new_id = body["new_workout_id"]
    assert body["proposal"]["summary"] == "fake"

    # New row exists with snapshot type
    new_row = (await seeded_db.execute(
        select(PlannedWorkout).where(PlannedWorkout.id == new_id)
    )).scalar_one()
    assert new_row.type == WorkoutType.strength_a
    assert new_row.status == WorkoutStatus.planned
```

- [ ] **Step 2: Run test, verify fail**

Run: `docker compose exec -T api pytest tests/test_reschedule_original.py -v`
Expected: FAIL — 404 (route doesn't exist).

- [ ] **Step 3: Add the endpoint**

In `app/routes/workouts.py`, add after the apply-move route:

```python
from app.schemas.edit import (
    EditWorkoutRequest,
    RescheduleOriginalRequest,
    RescheduleOriginalResponse,
)


@router.post("/{workout_id}/reschedule-original", response_model=RescheduleOriginalResponse)
async def reschedule_original(
    workout_id: uuid.UUID,
    body: RescheduleOriginalRequest,
    athlete: Athlete = Depends(get_current_athlete),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(PlannedWorkout)
        .join(Cycle, PlannedWorkout.cycle_id == Cycle.id)
        .join(Plan, Cycle.plan_id == Plan.id)
        .where(PlannedWorkout.id == workout_id, Plan.athlete_id == athlete.id)
    )
    parent = result.scalar_one_or_none()
    if parent is None:
        raise HTTPException(status_code=404, detail="Workout not found")
    snap = parent.original_snapshot_json
    if snap is None:
        raise HTTPException(status_code=400, detail="Workout has not been edited; nothing to reschedule")

    # Verify new_date sits inside the parent's cycle
    cycle = (await db.execute(select(Cycle).where(Cycle.id == parent.cycle_id))).scalar_one()
    if not (cycle.start_date <= body.new_date <= cycle.end_date):
        raise HTTPException(status_code=400, detail="new_date outside parent cycle")

    decimal_distance = (
        Decimal(snap["distance_mi"]) if snap.get("distance_mi") is not None else None
    )
    new_workout = PlannedWorkout(
        cycle_id=parent.cycle_id,
        scheduled_date=body.new_date,
        original_date=body.new_date,
        week_number=parent.week_number,
        type=WorkoutType(snap["type"]),
        family=WorkoutFamily(snap["family"]),
        status=WorkoutStatus.planned,
        duration_min=snap.get("duration_min"),
        distance_mi=decimal_distance,
        target_pace=snap.get("target_pace"),
        target_hr_zone=snap.get("target_hr_zone"),
        title=snap["title"],
        description_md=parent.description_md,
        intent_md=parent.intent_md,
    )
    db.add(new_workout)
    await db.flush()

    proposal = await propose_rebalance(
        db, athlete.id, new_workout.id, body.new_date,
        created_by="reschedule_original",
    )
    await db.commit()
    return RescheduleOriginalResponse(
        new_workout_id=str(new_workout.id), proposal=proposal
    )
```

Add the necessary imports at top of file:

```python
from decimal import Decimal
from app.models.workout import WorkoutFamily
```

- [ ] **Step 4: Run test, verify pass**

Run: `docker compose exec -T api pytest tests/test_reschedule_original.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add app/routes/workouts.py tests/test_reschedule_original.py
git commit -m "feat(backend): POST /workouts/{id}/reschedule-original clones snapshot + rebalances"
```

---

### Task B5: reschedule-original error cases

**Files:**
- Test: `tests/test_reschedule_original.py`

- [ ] **Step 1: Write the failing tests**

Append:

```python
@pytest.mark.asyncio
async def test_reschedule_original_400_when_no_snapshot(
    client, athlete_token, seeded_db
):
    result = await seeded_db.execute(select(PlannedWorkout).limit(1))
    workout = result.scalar_one()
    response = await client.post(
        f"/workouts/{workout.id}/reschedule-original",
        json={"new_date": workout.scheduled_date.isoformat()},
        headers={"Authorization": f"Bearer {athlete_token}"},
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_reschedule_original_400_when_outside_cycle(
    client, athlete_token, seeded_db
):
    result = await seeded_db.execute(
        select(PlannedWorkout).where(PlannedWorkout.type == "strength_a").limit(1)
    )
    workout = result.scalar_one()
    wid = str(workout.id)

    await client.patch(
        f"/workouts/{wid}",
        json={"type": "easy"},
        headers={"Authorization": f"Bearer {athlete_token}"},
    )

    response = await client.post(
        f"/workouts/{wid}/reschedule-original",
        json={"new_date": "2099-01-01"},
        headers={"Authorization": f"Bearer {athlete_token}"},
    )
    assert response.status_code == 400
```

- [ ] **Step 2: Run, verify pass**

Run: `docker compose exec -T api pytest tests/test_reschedule_original.py -v`
Expected: ALL PASS.

- [ ] **Step 3: Commit**

```bash
git add tests/test_reschedule_original.py
git commit -m "test(backend): reschedule-original 400 cases"
```

---

### Task B6: apply-move cancel deletes reschedule-created rows

**Files:**
- Modify: `app/routes/workouts.py` (find the `apply_move` endpoint, the `if choice == "cancel"` branch)
- Test: `tests/test_reschedule_original.py`

- [ ] **Step 1: Write the failing test**

Append:

```python
@pytest.mark.asyncio
async def test_cancel_apply_move_deletes_reschedule_created_row(
    client, athlete_token, seeded_db
):
    # Edit a strength workout to seed a snapshot
    result = await seeded_db.execute(
        select(PlannedWorkout).where(PlannedWorkout.type == "strength_a").limit(1)
    )
    edited = result.scalar_one()
    wid = str(edited.id)

    await client.patch(
        f"/workouts/{wid}",
        json={"type": "easy"},
        headers={"Authorization": f"Bearer {athlete_token}"},
    )

    fake_proposal = {
        "proposal_id": "22222222-2222-2222-2222-222222222222",
        "summary": "x",
        "options": [],
        "created_by": "reschedule_original",
    }
    with patch(
        "app.routes.workouts.propose_rebalance",
        AsyncMock(return_value=fake_proposal),
    ):
        r = await client.post(
            f"/workouts/{wid}/reschedule-original",
            json={"new_date": (edited.scheduled_date + datetime.timedelta(days=2)).isoformat()},
            headers={"Authorization": f"Bearer {athlete_token}"},
        )
    new_id = r.json()["new_workout_id"]

    # Now cancel apply-move on the new row
    cancel = await client.post(
        f"/workouts/{new_id}/apply-move",
        json={"proposal_id": "22222222-2222-2222-2222-222222222222", "choice": "cancel"},
        headers={"Authorization": f"Bearer {athlete_token}"},
    )
    assert cancel.status_code == 200

    # Row must be gone
    gone = (await seeded_db.execute(
        select(PlannedWorkout).where(PlannedWorkout.id == new_id)
    )).scalar_one_or_none()
    assert gone is None
```

- [ ] **Step 2: Run test, verify fail**

Run: `docker compose exec -T api pytest tests/test_reschedule_original.py::test_cancel_apply_move_deletes_reschedule_created_row -v`
Expected: FAIL — row still exists.

- [ ] **Step 3: Extend the cancel branch**

In `app/routes/workouts.py`, find this block in `apply_move`:

```python
    if choice == "cancel":
        proposal["state"] = "discarded"
        flag_modified(msg, "proposal_state_json")
        await db.commit()
        return {"ok": True}
```

Replace with:

```python
    if choice == "cancel":
        proposal["state"] = "discarded"
        flag_modified(msg, "proposal_state_json")
        if proposal.get("created_by") == "reschedule_original":
            await db.delete(planned)
        await db.commit()
        return {"ok": True}
```

- [ ] **Step 4: Run test, verify pass**

Run: `docker compose exec -T api pytest tests/test_reschedule_original.py -v`
Expected: ALL PASS.

- [ ] **Step 5: Verify no regression in existing move tests**

Run: `docker compose exec -T api pytest tests/test_move_endpoints.py -v`
Expected: ALL PASS.

- [ ] **Step 6: Commit**

```bash
git add app/routes/workouts.py tests/test_reschedule_original.py
git commit -m "feat(backend): cancel apply-move deletes reschedule-created rows"
```

---

### Task B7: Regenerate `mobile/openapi.json`

**Files:**
- Modify: `mobile/openapi.json`

- [ ] **Step 1: Run the export**

Run: `bash scripts/export_openapi.sh`

(Requires Docker compose up. Spec is written to `mobile/openapi.json`.)

- [ ] **Step 2: Verify new endpoints present**

Run: `node -e "const s=require('./mobile/openapi.json'); console.log(Object.keys(s.paths).sort().join('\n'))"`
Expected: includes `/workouts/{workout_id}` (PATCH) and `/workouts/{workout_id}/reschedule-original` (POST).

- [ ] **Step 3: Commit**

```bash
git add mobile/openapi.json
git commit -m "chore: regenerate openapi.json with edit + reschedule-original"
```

---

## Phase C — Mobile foundation (NES tokens + retro primitives)

### Task C1: Add fonts and `expo-font` setup

**Files:**
- Modify: `mobile/package.json`
- Modify: `mobile/App.tsx`
- Modify: `mobile/app.json`
- Create: `mobile/assets/fonts/PressStart2P-Regular.ttf`
- Create: `mobile/assets/fonts/VT323-Regular.ttf`

- [ ] **Step 1: Install `expo-font`**

Run: `cd mobile && npx expo install expo-font`

- [ ] **Step 2: Download fonts**

Download:
- `https://fonts.gstatic.com/s/pressstart2p/v15/e3t4euO8T-267oIAQAu6jDQyK3nVivM.ttf` → `mobile/assets/fonts/PressStart2P-Regular.ttf`
- `https://fonts.gstatic.com/s/vt323/v17/pxiKyp0ihIEF2isfFJU.ttf` → `mobile/assets/fonts/VT323-Regular.ttf`

PowerShell:

```powershell
mkdir -p mobile/assets/fonts
Invoke-WebRequest -Uri "https://fonts.gstatic.com/s/pressstart2p/v15/e3t4euO8T-267oIAQAu6jDQyK3nVivM.ttf" -OutFile "mobile/assets/fonts/PressStart2P-Regular.ttf"
Invoke-WebRequest -Uri "https://fonts.gstatic.com/s/vt323/v17/pxiKyp0ihIEF2isfFJU.ttf" -OutFile "mobile/assets/fonts/VT323-Regular.ttf"
```

- [ ] **Step 3: Wire `useFonts` in `App.tsx`**

At the top of `mobile/App.tsx`, add:

```tsx
import { useFonts } from 'expo-font';
import * as SplashScreen from 'expo-splash-screen';
```

Replace the existing `export default function App` with:

```tsx
SplashScreen.preventAutoHideAsync().catch(() => {});

export default function App() {
  const [loaded] = useFonts({
    'PressStart2P': require('./assets/fonts/PressStart2P-Regular.ttf'),
    'VT323': require('./assets/fonts/VT323-Regular.ttf'),
  });

  useEffect(() => {
    if (loaded) {
      void SplashScreen.hideAsync();
    }
  }, [loaded]);

  if (!loaded) return null;

  return (
    <GestureHandlerRootView style={{ flex: 1 }}>
      <SafeAreaProvider>
        <QueryClientProvider client={queryClient}>
          <AuthProvider>
            <Gate />
            <StatusBar style="light" />
          </AuthProvider>
        </QueryClientProvider>
      </SafeAreaProvider>
    </GestureHandlerRootView>
  );
}
```

Add `useEffect` to the existing `react` imports.

If `expo-splash-screen` isn't installed, add it: `npx expo install expo-splash-screen`.

- [ ] **Step 4: Typecheck**

Run: `cd mobile && npx tsc --noEmit`
Expected: 0 errors.

- [ ] **Step 5: Smoke test**

Reload http://localhost:19006. App should render normally (login screen). No "fontFamily PressStart2P is not a system font" warnings in console.

- [ ] **Step 6: Commit**

```bash
git add mobile/
git commit -m "feat(mobile): load Press Start 2P + VT323 fonts via expo-font"
```

---

### Task C2: NES palette in `tokens.ts` + `tailwind.config.js`

**Files:**
- Modify: `mobile/src/theme/tokens.ts`
- Modify: `mobile/tailwind.config.js`

- [ ] **Step 1: Replace `tokens.ts`**

Overwrite `mobile/src/theme/tokens.ts` with:

```ts
export const colors = {
  bg: '#0d0d12',
  bgPanel: '#11142a',
  bgPanelAlt: '#1a1d3d',
  bgCard: '#11142a',  // alias kept for backward compat with existing consumers
  bgElev: '#11142a',  // alias
  ink: '#f4f4ec',
  inkDim: '#9a9aab',
  inkMute: '#5a5a6b',
  line: '#000000',
  accentRun: '#5cd86c',
  accentStrength: '#e8a23a',
  accentRest: '#5b8cff',
  accentDanger: '#e84a4a',
  accentHi: '#f7d51d',
} as const;

export const spacing = {
  xs: 4, sm: 8, md: 12, lg: 16, xl: 24, xxl: 32,
} as const;

export const radius = { sm: 0, md: 0, lg: 0, xl: 0 } as const;  // NES = no rounding

export type WorkoutFamily = 'running' | 'strength' | 'other';

export const familyColor: Record<WorkoutFamily, string> = {
  running: colors.accentRun,
  strength: colors.accentStrength,
  other: colors.accentRest,
};

export const fonts = {
  pixel: 'PressStart2P',
  body: 'VT323',
} as const;
```

- [ ] **Step 2: Match palette in `tailwind.config.js`**

Replace the `colors` block in `mobile/tailwind.config.js` with:

```js
      colors: {
        bg: {
          DEFAULT: '#0d0d12',
          panel: '#11142a',
          panelAlt: '#1a1d3d',
          elev: '#11142a',
          card: '#11142a',
        },
        ink: {
          DEFAULT: '#f4f4ec',
          dim: '#9a9aab',
          mute: '#5a5a6b',
        },
        accent: {
          run: '#5cd86c',
          strength: '#e8a23a',
          rest: '#5b8cff',
          danger: '#e84a4a',
          hi: '#f7d51d',
        },
        line: '#000000',
      },
      fontFamily: {
        pixel: ['PressStart2P'],
        body: ['VT323'],
      },
```

- [ ] **Step 3: Typecheck**

Run: `cd mobile && npx tsc --noEmit`
Expected: 0 errors.

- [ ] **Step 4: Smoke test**

Reload :19006. Existing screens should still render — they'll now use the navy/cream NES palette where they were using the old dark-modern colors. Visually different but not broken.

- [ ] **Step 5: Commit**

```bash
git add mobile/src/theme/tokens.ts mobile/tailwind.config.js
git commit -m "feat(mobile): NES classic palette in tokens + tailwind"
```

---

### Task C3: `theme/retro.ts` helpers

**Files:**
- Create: `mobile/src/theme/retro.ts`

- [ ] **Step 1: Create the helpers**

```ts
import { Easing, type ViewStyle } from 'react-native';

import { colors } from './tokens';

export const stepEasing = Easing.steps(4);

export function nesShadow(offset = 2): ViewStyle {
  return {
    shadowColor: '#000',
    shadowOffset: { width: offset, height: offset },
    shadowOpacity: 1,
    shadowRadius: 0,
    elevation: offset,
  };
}

export function nesBorder(width = 2): ViewStyle {
  return {
    borderWidth: width,
    borderColor: colors.line,
    borderRadius: 0,
  };
}
```

- [ ] **Step 2: Typecheck**

Run: `cd mobile && npx tsc --noEmit`
Expected: 0 errors.

- [ ] **Step 3: Commit**

```bash
git add mobile/src/theme/retro.ts
git commit -m "feat(mobile): retro.ts helpers (nesShadow, nesBorder, stepEasing)"
```

---

### Task C4: `RetroBorder` primitive

**Files:**
- Create: `mobile/src/components/retro/RetroBorder.tsx`

- [ ] **Step 1: Create the component**

```tsx
import type { PropsWithChildren } from 'react';
import { View, type ViewStyle } from 'react-native';

import { colors } from '@/theme/tokens';
import { nesBorder, nesShadow } from '@/theme/retro';

interface Props {
  background?: string;
  noShadow?: boolean;
  style?: ViewStyle;
}

export function RetroBorder({
  children,
  background = colors.bgPanel,
  noShadow = false,
  style,
}: PropsWithChildren<Props>) {
  return (
    <View
      style={[
        nesBorder(),
        noShadow ? null : nesShadow(),
        { backgroundColor: background },
        style,
      ]}
    >
      {children}
    </View>
  );
}
```

- [ ] **Step 2: Typecheck**

Run: `cd mobile && npx tsc --noEmit`
Expected: 0 errors.

- [ ] **Step 3: Commit**

```bash
git add mobile/src/components/retro/RetroBorder.tsx
git commit -m "feat(mobile): RetroBorder primitive (2px border + hard shadow)"
```

---

### Task C5: `RetroButton` primitive

**Files:**
- Create: `mobile/src/components/retro/RetroButton.tsx`

- [ ] **Step 1: Create the component**

```tsx
import { useState } from 'react';
import { Pressable, Text, View, type ViewStyle } from 'react-native';

import { colors } from '@/theme/tokens';
import { nesBorder, nesShadow } from '@/theme/retro';

type Tone = 'default' | 'primary' | 'danger' | 'ghost';

interface Props {
  label: string;
  onPress?: () => void;
  disabled?: boolean;
  tone?: Tone;
  style?: ViewStyle;
}

const TONE_BG: Record<Tone, string> = {
  default: colors.bgPanelAlt,
  primary: colors.accentRun,
  danger: colors.accentDanger,
  ghost: 'transparent',
};

const TONE_INK: Record<Tone, string> = {
  default: colors.ink,
  primary: colors.bg,
  danger: colors.ink,
  ghost: colors.ink,
};

export function RetroButton({
  label, onPress, disabled = false, tone = 'default', style,
}: Props) {
  const [pressed, setPressed] = useState(false);
  return (
    <Pressable
      onPress={onPress}
      onPressIn={() => { setPressed(true); }}
      onPressOut={() => { setPressed(false); }}
      disabled={disabled}
      style={[
        nesBorder(),
        pressed ? null : nesShadow(),
        {
          backgroundColor: TONE_BG[tone],
          paddingHorizontal: 14,
          paddingVertical: 10,
          opacity: disabled ? 0.4 : 1,
          transform: pressed ? [{ translateX: 2 }, { translateY: 2 }] : [],
        },
        style,
      ]}
    >
      <View>
        <Text
          style={{
            color: TONE_INK[tone],
            fontFamily: 'PressStart2P',
            fontSize: 10,
            letterSpacing: 1,
            textAlign: 'center',
          }}
        >
          {label.toUpperCase()}
        </Text>
      </View>
    </Pressable>
  );
}
```

- [ ] **Step 2: Typecheck**

Run: `cd mobile && npx tsc --noEmit`
Expected: 0 errors.

- [ ] **Step 3: Commit**

```bash
git add mobile/src/components/retro/RetroButton.tsx
git commit -m "feat(mobile): RetroButton primitive with mechanical-press effect"
```

---

### Task C6: `RetroPill` + `RetroCard` primitives

**Files:**
- Create: `mobile/src/components/retro/RetroPill.tsx`
- Create: `mobile/src/components/retro/RetroCard.tsx`

- [ ] **Step 1: `RetroPill`**

```tsx
import { Text, View } from 'react-native';

import { colors } from '@/theme/tokens';

interface Props {
  label: string;
  color?: string;
}

export function RetroPill({ label, color = colors.inkDim }: Props) {
  return (
    <View>
      <Text
        style={{
          color,
          fontFamily: 'PressStart2P',
          fontSize: 8,
          letterSpacing: 1,
        }}
      >
        [ {label.toUpperCase()} ]
      </Text>
    </View>
  );
}
```

- [ ] **Step 2: `RetroCard`**

```tsx
import type { PropsWithChildren } from 'react';
import { View, type ViewStyle } from 'react-native';

import { RetroBorder } from './RetroBorder';

interface Props {
  style?: ViewStyle;
  padding?: number;
}

export function RetroCard({
  children, style, padding = 14,
}: PropsWithChildren<Props>) {
  return (
    <RetroBorder style={style}>
      <View style={{ padding }}>{children}</View>
    </RetroBorder>
  );
}
```

- [ ] **Step 3: Typecheck**

Run: `cd mobile && npx tsc --noEmit`
Expected: 0 errors.

- [ ] **Step 4: Commit**

```bash
git add mobile/src/components/retro/
git commit -m "feat(mobile): RetroPill + RetroCard primitives"
```

---

## Phase D — Mobile types + hooks

### Task D1: Extend `types.ts` with `original_snapshot`

**Files:**
- Modify: `mobile/src/api/types.ts`

- [ ] **Step 1: Add the field to `PlannedWorkoutOut`**

Find the `PlannedWorkoutOut` interface and add at the end of its members:

```ts
export interface PlannedWorkoutSnapshot {
  type: string;
  family: string;
  distance_mi: string | null;
  duration_min: number | null;
  title: string;
  target_pace: string | null;
  target_hr_zone: string | null;
}

export interface PlannedWorkoutOut {
  // ... existing fields ...
  original_snapshot: PlannedWorkoutSnapshot | null;
}
```

Also append:

```ts
export interface EditWorkoutRequest {
  type?: string;
  distance_mi?: number | null;
  duration_min?: number | null;
  title?: string;
}

export interface RescheduleOriginalRequest {
  new_date: IsoDate;
}

export interface RescheduleOriginalResponse {
  new_workout_id: UUID;
  proposal: ProposalOut;
}
```

- [ ] **Step 2: Typecheck**

Run: `cd mobile && npx tsc --noEmit`
Expected: 0 errors. (Existing consumers don't yet read `original_snapshot`, so no breakage.)

- [ ] **Step 3: Commit**

```bash
git add mobile/src/api/types.ts
git commit -m "feat(mobile): add EditWorkoutRequest + original_snapshot to types"
```

---

### Task D2: `useEditWorkout` hook

**Files:**
- Create: `mobile/src/api/hooks/useEditWorkout.ts`

- [ ] **Step 1: Create the hook**

```ts
import { useMutation, useQueryClient } from '@tanstack/react-query';

import { api } from '@/api/client';
import type { EditWorkoutRequest, PlannedWorkoutOut } from '@/api/types';

interface Vars {
  workoutId: string;
  body: EditWorkoutRequest;
  /** the workout's original_snapshot BEFORE this edit, so the caller can
   *  detect a null→non-null transition (the "first edit" signal) */
  preEditSnapshot: PlannedWorkoutOut['original_snapshot'];
}

interface Result {
  workout: PlannedWorkoutOut;
  /** true iff this PATCH transitioned original_snapshot from null to non-null */
  firstEdit: boolean;
}

export function useEditWorkout() {
  const qc = useQueryClient();
  return useMutation<Result, Error, Vars>({
    mutationFn: async ({ workoutId, body, preEditSnapshot }) => {
      const res = await api.patch<PlannedWorkoutOut>(`/workouts/${workoutId}`, body);
      const firstEdit = preEditSnapshot === null && res.data.original_snapshot !== null;
      return { workout: res.data, firstEdit };
    },
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ['plan'] });
      void qc.invalidateQueries({ queryKey: ['workout'] });
    },
  });
}
```

- [ ] **Step 2: Typecheck**

Run: `cd mobile && npx tsc --noEmit`
Expected: 0 errors.

- [ ] **Step 3: Commit**

```bash
git add mobile/src/api/hooks/useEditWorkout.ts
git commit -m "feat(mobile): useEditWorkout hook (returns firstEdit flag)"
```

---

### Task D3: `useRescheduleOriginal` hook

**Files:**
- Create: `mobile/src/api/hooks/useRescheduleOriginal.ts`

- [ ] **Step 1: Create the hook**

```ts
import { useMutation, useQueryClient } from '@tanstack/react-query';

import { api } from '@/api/client';
import type { RescheduleOriginalRequest, RescheduleOriginalResponse } from '@/api/types';

interface Vars {
  workoutId: string;
  body: RescheduleOriginalRequest;
}

export function useRescheduleOriginal() {
  const qc = useQueryClient();
  return useMutation<RescheduleOriginalResponse, Error, Vars>({
    mutationFn: async ({ workoutId, body }) => {
      const res = await api.post<RescheduleOriginalResponse>(
        `/workouts/${workoutId}/reschedule-original`, body,
      );
      return res.data;
    },
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ['plan'] });
    },
  });
}
```

- [ ] **Step 2: Typecheck**

Run: `cd mobile && npx tsc --noEmit`
Expected: 0 errors.

- [ ] **Step 3: Commit**

```bash
git add mobile/src/api/hooks/useRescheduleOriginal.ts
git commit -m "feat(mobile): useRescheduleOriginal hook"
```

---

## Phase E — Mobile retro restyle (component-by-component)

> Restyling is the largest chunk by file count. Each task below restyles one
> component or screen. Commit after each so we can revert any regression.

### Task E1: Restyle `WorkoutCard`

**Files:**
- Modify: `mobile/src/components/WorkoutCard.tsx`

- [ ] **Step 1: Rewrite using retro primitives**

Replace the entire file:

```tsx
import { Pressable, Text, View } from 'react-native';

import type { PlannedWorkoutOut } from '@/api/types';
import { RetroBorder } from '@/components/retro/RetroBorder';
import { RetroPill } from '@/components/retro/RetroPill';
import { formatDistance } from '@/lib/format';
import { colors, familyColor, type WorkoutFamily } from '@/theme/tokens';

const FAMILIES: ReadonlySet<WorkoutFamily> = new Set(['running', 'strength', 'other']);

function asFamily(raw: string): WorkoutFamily {
  return FAMILIES.has(raw as WorkoutFamily) ? (raw as WorkoutFamily) : 'other';
}

const STATUS_COLOR: Record<string, string> = {
  planned: colors.inkDim,
  moved: colors.accentRest,
  skipped: colors.accentDanger,
  done: colors.accentRun,
};

interface Props {
  workout: PlannedWorkoutOut;
  onPress?: () => void;
  onWhy?: () => void;
  onEdit?: () => void;
  compact?: boolean;
}

export function WorkoutCard({ workout, onPress, onWhy, onEdit, compact = false }: Props) {
  const family = asFamily(workout.family);
  const tint = familyColor[family];
  const distance = workout.distance_mi !== null
    ? formatDistance(parseFloat(workout.distance_mi))
    : null;
  const statusColor = STATUS_COLOR[workout.status] ?? colors.inkDim;
  const wasOriginal = workout.original_snapshot;

  return (
    <Pressable onPress={onPress} style={{ marginBottom: 14 }}>
      <RetroBorder>
        <View style={{ padding: 12 }}>
          <View style={{ flexDirection: 'row', alignItems: 'center', marginBottom: 6 }}>
            <View style={{
              backgroundColor: tint, width: 10, height: 10, marginRight: 8,
            }} />
            <Text style={{
              fontFamily: 'PressStart2P', fontSize: 8, color: colors.inkDim, letterSpacing: 1,
            }}>
              {workout.type.toUpperCase()}
            </Text>
            <View style={{ flex: 1 }} />
            <RetroPill label={workout.status} color={statusColor} />
          </View>

          <Text style={{
            fontFamily: 'VT323', fontSize: 22, color: colors.ink, lineHeight: 24,
          }} numberOfLines={2}>
            {workout.title}
          </Text>

          {wasOriginal !== null && (
            <View style={{ flexDirection: 'row', alignItems: 'center', marginTop: 4 }}>
              <Text style={{
                fontFamily: 'VT323', fontSize: 14, color: colors.inkDim,
              }}>
                ↻ was: {wasOriginal.title}
              </Text>
            </View>
          )}

          {!compact && (
            <View style={{ flexDirection: 'row', flexWrap: 'wrap', marginTop: 8 }}>
              {distance !== null && (
                <Text style={{ fontFamily: 'VT323', fontSize: 16, color: colors.inkDim, marginRight: 12 }}>
                  {distance}
                </Text>
              )}
              {workout.duration_min !== null && (
                <Text style={{ fontFamily: 'VT323', fontSize: 16, color: colors.inkDim, marginRight: 12 }}>
                  {workout.duration_min}min
                </Text>
              )}
              {workout.target_pace !== null && (
                <Text style={{ fontFamily: 'VT323', fontSize: 16, color: colors.inkDim, marginRight: 12 }}>
                  {workout.target_pace}
                </Text>
              )}
              {workout.target_hr_zone !== null && (
                <Text style={{ fontFamily: 'VT323', fontSize: 16, color: colors.inkDim }}>
                  {workout.target_hr_zone}
                </Text>
              )}
            </View>
          )}

          {(onWhy !== undefined || onEdit !== undefined) && (
            <View style={{ flexDirection: 'row', marginTop: 10, gap: 8 }}>
              {onWhy !== undefined && (
                <Pressable
                  onPress={onWhy}
                  hitSlop={8}
                  style={{ borderColor: colors.line, borderWidth: 2, paddingHorizontal: 8, paddingVertical: 4 }}
                >
                  <Text style={{ fontFamily: 'PressStart2P', fontSize: 8, color: colors.ink }}>WHY?</Text>
                </Pressable>
              )}
              {onEdit !== undefined && (
                <Pressable
                  onPress={onEdit}
                  hitSlop={8}
                  style={{ borderColor: colors.line, borderWidth: 2, paddingHorizontal: 8, paddingVertical: 4 }}
                >
                  <Text style={{ fontFamily: 'PressStart2P', fontSize: 8, color: colors.ink }}>EDIT</Text>
                </Pressable>
              )}
            </View>
          )}
        </View>
      </RetroBorder>
    </Pressable>
  );
}
```

- [ ] **Step 2: Typecheck**

Run: `cd mobile && npx tsc --noEmit`
Expected: 0 errors.

- [ ] **Step 3: Smoke test**

Reload :19006 → log in → Today screen should show workout cards with the new NES look (square corners, hard shadows, pixel font, status in `[ PLANNED ]` brackets, EDIT and WHY? buttons).

- [ ] **Step 4: Commit**

```bash
git add mobile/src/components/WorkoutCard.tsx
git commit -m "feat(mobile): retro WorkoutCard with EDIT button + was-X tag"
```

---

### Task E2: Restyle `LoginScreen`

**Files:**
- Modify: `mobile/src/screens/LoginScreen.tsx`

- [ ] **Step 1: Rewrite to use retro primitives**

Replace `mobile/src/screens/LoginScreen.tsx` with:

```tsx
import { useState } from 'react';
import { ActivityIndicator, KeyboardAvoidingView, Platform, Text, TextInput, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { isAxiosError } from 'axios';

import { useAuth } from '@/auth/AuthContext';
import { RetroBorder } from '@/components/retro/RetroBorder';
import { RetroButton } from '@/components/retro/RetroButton';
import { colors } from '@/theme/tokens';

export function LoginScreen() {
  const { login } = useAuth();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const onSubmit = async () => {
    if (submitting) return;
    setSubmitting(true);
    setError(null);
    try {
      await login({ email: email.trim(), password });
    } catch (e) {
      if (isAxiosError(e) && e.response?.status === 401) setError('INVALID LOGIN');
      else if (isAxiosError(e) && e.code === 'ECONNABORTED') setError('SERVER UNREACHABLE');
      else setError('LOGIN FAILED');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: colors.bg }}>
      <KeyboardAvoidingView
        style={{ flex: 1 }}
        behavior={Platform.OS === 'ios' ? 'padding' : undefined}
      >
        <View style={{ flex: 1, paddingHorizontal: 24, justifyContent: 'center' }}>
          <Text style={{
            fontFamily: 'PressStart2P', fontSize: 24, color: colors.accentHi,
            marginBottom: 6, textAlign: 'center',
          }}>
            MARATHON
          </Text>
          <Text style={{
            fontFamily: 'VT323', fontSize: 18, color: colors.inkDim,
            marginBottom: 36, textAlign: 'center',
          }}>
            ▸ PRESS START
          </Text>

          <Text style={{ fontFamily: 'PressStart2P', fontSize: 8, color: colors.inkDim, marginBottom: 6 }}>
            EMAIL
          </Text>
          <RetroBorder background={colors.bgPanelAlt} style={{ marginBottom: 14 }}>
            <TextInput
              value={email}
              onChangeText={setEmail}
              autoCapitalize="none"
              autoCorrect={false}
              keyboardType="email-address"
              textContentType="emailAddress"
              placeholder="you@example.com"
              placeholderTextColor={colors.inkMute}
              style={{ fontFamily: 'VT323', fontSize: 18, color: colors.ink, padding: 10 }}
            />
          </RetroBorder>

          <Text style={{ fontFamily: 'PressStart2P', fontSize: 8, color: colors.inkDim, marginBottom: 6 }}>
            PASSWORD
          </Text>
          <RetroBorder background={colors.bgPanelAlt} style={{ marginBottom: 14 }}>
            <TextInput
              value={password}
              onChangeText={setPassword}
              secureTextEntry
              textContentType="password"
              placeholder="••••••••"
              placeholderTextColor={colors.inkMute}
              style={{ fontFamily: 'VT323', fontSize: 18, color: colors.ink, padding: 10 }}
            />
          </RetroBorder>

          {error !== null && (
            <Text style={{ fontFamily: 'PressStart2P', fontSize: 8, color: colors.accentDanger, marginBottom: 12 }}>
              ! {error}
            </Text>
          )}

          {submitting ? (
            <View style={{ alignItems: 'center', paddingVertical: 12 }}>
              <ActivityIndicator color={colors.accentRun} />
            </View>
          ) : (
            <RetroButton
              label="Sign in"
              onPress={() => { void onSubmit(); }}
              disabled={email.length === 0 || password.length === 0}
              tone="primary"
            />
          )}
        </View>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}
```

- [ ] **Step 2: Typecheck**

Run: `cd mobile && npx tsc --noEmit`
Expected: 0 errors.

- [ ] **Step 3: Smoke test**

Sign out → login screen should show pixel "MARATHON" title, "▸ PRESS START" subtitle, retro-bordered inputs, NES button.

- [ ] **Step 4: Commit**

```bash
git add mobile/src/screens/LoginScreen.tsx
git commit -m "feat(mobile): retro LoginScreen"
```

---

### Task E3: Restyle `WhySheet`

**Files:**
- Modify: `mobile/src/components/WhySheet.tsx`

- [ ] **Step 1: Update sheet styling**

Find the `markdownStyle` constant and overwrite the body fontSize/lineHeight + paragraph styles to use VT323. Update the workout title rendering to use Press Start 2P. Background should be `colors.bgPanel`. Add a 2px hard border at top of sheet (use the inset shadow approach — RN bottom sheets don't have native border; render a `<View>` 2px tall at top of content with `colors.line` background).

Replacement file:

```tsx
import BottomSheet, { BottomSheetScrollView } from '@gorhom/bottom-sheet';
import { forwardRef, useMemo } from 'react';
import { Text, View } from 'react-native';
import Markdown from 'react-native-markdown-display';

import type { PlannedWorkoutOut } from '@/api/types';
import { colors } from '@/theme/tokens';

interface Props {
  workout: PlannedWorkoutOut | null;
  onClose: () => void;
}

const markdownStyle = {
  body: { color: colors.ink, fontFamily: 'VT323', fontSize: 18, lineHeight: 22 },
  heading1: { color: colors.ink, fontFamily: 'PressStart2P', fontSize: 14, marginTop: 12, marginBottom: 8 },
  heading2: { color: colors.ink, fontFamily: 'PressStart2P', fontSize: 12, marginTop: 12, marginBottom: 6 },
  heading3: { color: colors.ink, fontFamily: 'PressStart2P', fontSize: 10, marginTop: 10, marginBottom: 4 },
  paragraph: { color: colors.ink, marginBottom: 8 },
  code_inline: { color: colors.accentHi, backgroundColor: colors.bgPanelAlt, paddingHorizontal: 4 },
  bullet_list: { marginBottom: 8 },
  list_item: { color: colors.ink },
  strong: { color: colors.ink, fontFamily: 'VT323', fontWeight: '700' as const },
  em: { color: colors.ink, fontStyle: 'italic' as const },
  hr: { backgroundColor: colors.line, height: 2, marginVertical: 12 },
};

export const WhySheet = forwardRef<BottomSheet, Props>(function WhySheet(
  { workout, onClose }, ref,
) {
  const snapPoints = useMemo(() => ['60%', '90%'], []);
  return (
    <BottomSheet
      ref={ref}
      index={-1}
      snapPoints={snapPoints}
      enablePanDownToClose
      onClose={onClose}
      backgroundStyle={{ backgroundColor: colors.bgPanel, borderTopWidth: 2, borderColor: colors.line, borderRadius: 0 }}
      handleIndicatorStyle={{ backgroundColor: colors.inkDim }}
    >
      <BottomSheetScrollView contentContainerStyle={{ padding: 20, paddingBottom: 40 }}>
        {workout === null ? (
          <Text style={{ fontFamily: 'VT323', fontSize: 18, color: colors.inkDim }}>
            No workout selected.
          </Text>
        ) : (
          <View>
            <Text style={{ fontFamily: 'PressStart2P', fontSize: 8, color: colors.inkDim, letterSpacing: 1 }}>
              WK {workout.week_number} · {workout.type.toUpperCase()}
            </Text>
            <Text style={{ fontFamily: 'PressStart2P', fontSize: 14, color: colors.ink, marginTop: 6, marginBottom: 14 }}>
              {workout.title.toUpperCase()}
            </Text>
            {workout.description_md.trim().length > 0 && (
              <View>
                <Text style={{ fontFamily: 'PressStart2P', fontSize: 8, color: colors.inkDim, letterSpacing: 1, marginBottom: 4 }}>
                  PRESCRIPTION
                </Text>
                <Markdown style={markdownStyle}>{workout.description_md}</Markdown>
              </View>
            )}
            {workout.intent_md.trim().length > 0 && (
              <View style={{ marginTop: 16 }}>
                <Text style={{ fontFamily: 'PressStart2P', fontSize: 8, color: colors.inkDim, letterSpacing: 1, marginBottom: 4 }}>
                  INTENT
                </Text>
                <Markdown style={markdownStyle}>{workout.intent_md}</Markdown>
              </View>
            )}
          </View>
        )}
      </BottomSheetScrollView>
    </BottomSheet>
  );
});
```

- [ ] **Step 2: Typecheck**

Run: `cd mobile && npx tsc --noEmit`
Expected: 0 errors.

- [ ] **Step 3: Smoke test**

Today → tap WHY? → bottom sheet opens with NES styling (navy bg, pixel headers, VT323 body).

- [ ] **Step 4: Commit**

```bash
git add mobile/src/components/WhySheet.tsx
git commit -m "feat(mobile): retro WhySheet"
```

---

### Task E4: Restyle `ProposalSheet`

**Files:**
- Modify: `mobile/src/components/ProposalSheet.tsx`

- [ ] **Step 1: Rewrite using retro primitives**

Replace the file. Key changes:
- All headers use `PressStart2P`, body uses `VT323`.
- OptionCard becomes a `RetroBorder` panel.
- Apply / Just-move / Cancel buttons become `RetroButton` with appropriate tones (primary / default / danger).
- `backgroundStyle` on the BottomSheet uses `colors.bgPanel` + 2px top border + radius 0.

```tsx
import BottomSheet, { BottomSheetScrollView } from '@gorhom/bottom-sheet';
import { forwardRef, useMemo, useState } from 'react';
import { ActivityIndicator, Pressable, Text, View } from 'react-native';

import type { AdapterOption, ApplyChoice, ProposalOut } from '@/api/types';
import { RetroBorder } from '@/components/retro/RetroBorder';
import { RetroButton } from '@/components/retro/RetroButton';
import { colors } from '@/theme/tokens';

interface Props {
  proposal: ProposalOut | null;
  submitting: boolean;
  onApply: (choice: ApplyChoice) => Promise<void> | void;
  onCancel: () => Promise<void> | void;
}

function OptionCard({
  option, expanded, onToggle, onApply, disabled,
}: {
  option: AdapterOption;
  expanded: boolean;
  onToggle: () => void;
  onApply: () => void;
  disabled: boolean;
}) {
  return (
    <RetroBorder style={{ marginBottom: 12 }}>
      <View style={{ padding: 14 }}>
        <Text style={{ fontFamily: 'PressStart2P', fontSize: 10, color: colors.ink }}>
          {option.label.toUpperCase()}
        </Text>
        <Text style={{ fontFamily: 'VT323', fontSize: 16, color: colors.inkDim, marginTop: 4 }}>
          {option.tradeoff}
        </Text>
        <Pressable onPress={onToggle} hitSlop={6}>
          <Text style={{ fontFamily: 'PressStart2P', fontSize: 8, color: colors.accentRun, marginTop: 8 }}>
            {expanded ? '▾ HIDE' : '▸ WHY THIS'}
          </Text>
        </Pressable>
        {expanded && (
          <Text style={{ fontFamily: 'VT323', fontSize: 16, color: colors.ink, marginTop: 8, lineHeight: 20 }}>
            {option.rationale}
          </Text>
        )}
        <View style={{ marginTop: 12 }}>
          <RetroButton label="Apply" tone="primary" onPress={onApply} disabled={disabled} />
        </View>
      </View>
    </RetroBorder>
  );
}

export const ProposalSheet = forwardRef<BottomSheet, Props>(function ProposalSheet(
  { proposal, submitting, onApply, onCancel }, ref,
) {
  const snapPoints = useMemo(() => ['60%', '92%'], []);
  const [expanded, setExpanded] = useState<string | null>(null);

  return (
    <BottomSheet
      ref={ref}
      index={-1}
      snapPoints={snapPoints}
      enablePanDownToClose
      onClose={() => { if (proposal !== null) void onCancel(); }}
      backgroundStyle={{ backgroundColor: colors.bgPanel, borderTopWidth: 2, borderColor: colors.line, borderRadius: 0 }}
      handleIndicatorStyle={{ backgroundColor: colors.inkDim }}
    >
      <BottomSheetScrollView contentContainerStyle={{ padding: 20, paddingBottom: 40 }}>
        {proposal === null ? (
          <View style={{ alignItems: 'center', paddingVertical: 24 }}>
            <ActivityIndicator color={colors.accentRun} />
            <Text style={{ fontFamily: 'PressStart2P', fontSize: 8, color: colors.inkDim, marginTop: 12, letterSpacing: 1 }}>
              COACH IS THINKING…
            </Text>
          </View>
        ) : (
          <View>
            <Text style={{ fontFamily: 'PressStart2P', fontSize: 8, color: colors.inkDim, letterSpacing: 1 }}>
              PROPOSED REBALANCE
            </Text>
            <Text style={{ fontFamily: 'VT323', fontSize: 22, color: colors.ink, marginTop: 6, marginBottom: 16, lineHeight: 26 }}>
              {proposal.summary}
            </Text>

            {proposal.options.map((option) => (
              <OptionCard
                key={option.id}
                option={option}
                expanded={expanded === option.id}
                onToggle={() => { setExpanded((cur) => (cur === option.id ? null : option.id)); }}
                onApply={() => { void onApply(option.id); }}
                disabled={submitting}
              />
            ))}

            <View style={{ marginTop: 4 }}>
              <RetroButton label="Just move it" onPress={() => { void onApply('just_move'); }} disabled={submitting} />
            </View>
            <View style={{ marginTop: 8 }}>
              <RetroButton label="Cancel" tone="danger" onPress={() => { void onCancel(); }} disabled={submitting} />
            </View>
          </View>
        )}
      </BottomSheetScrollView>
    </BottomSheet>
  );
});
```

- [ ] **Step 2: Typecheck**

Run: `cd mobile && npx tsc --noEmit`
Expected: 0 errors.

- [ ] **Step 3: Smoke test**

Drag a workout to a different day → ProposalSheet shows new NES styling.

- [ ] **Step 4: Commit**

```bash
git add mobile/src/components/ProposalSheet.tsx
git commit -m "feat(mobile): retro ProposalSheet"
```

---

### Task E5: Restyle `DayCard` + `DraggableWeekList`

**Files:**
- Modify: `mobile/src/components/DayCard.tsx`
- Modify: `mobile/src/components/DraggableWeekList.tsx`

- [ ] **Step 1: Update DayCard**

In `mobile/src/components/DayCard.tsx`, change the day-name rendering to use `PressStart2P` with a `▸` cursor when today, and the rest day "REST" placeholder to use the retro look. Update `Text` style props to use `fontFamily: 'PressStart2P'` for headers and `'VT323'` for body, and replace the `bg-bg-card rounded-xl` className with a `<RetroBorder>` wrapper.

Search-replace key parts (full rewrite recommended for clarity).

- [ ] **Step 2: Update DraggableWeekList**

In `mobile/src/components/DraggableWeekList.tsx`, find the inline day header (around the `▸ MON  05/04` part) and the rest-day placeholder, and update fonts to `'PressStart2P'` and `'VT323'`. The DropZone tint stays the same (`accentRun` 10% on hover) but should also show a 2px dashed border (`borderStyle: 'dashed'`, `borderWidth: 2`, `borderColor: colors.accentRun`) when hovered, for stronger NES-feel feedback.

- [ ] **Step 3: Typecheck**

Run: `cd mobile && npx tsc --noEmit`
Expected: 0 errors.

- [ ] **Step 4: Smoke test**

Week tab shows NES-styled day rows. Drag highlights show dashed accent border.

- [ ] **Step 5: Commit**

```bash
git add mobile/src/components/DayCard.tsx mobile/src/components/DraggableWeekList.tsx
git commit -m "feat(mobile): retro DayCard + DraggableWeekList"
```

---

### Task E6: Restyle `TodayScreen`

**Files:**
- Modify: `mobile/src/screens/TodayScreen.tsx`

- [ ] **Step 1: Rewrite header + cards**

Replace `bg-bg-card`-styled views with `<RetroBorder>` wrappers, all titles to `PressStart2P`, all body to `VT323`. Header reads `▸ TODAY  MM/DD`. Coach brief panel uses `RetroCard`. Recent runs placeholder uses RetroCard.

(Mechanical restyle — preserve all existing logic, only swap visual primitives.)

- [ ] **Step 2: Typecheck**

Run: `cd mobile && npx tsc --noEmit`
Expected: 0 errors.

- [ ] **Step 3: Smoke test**

Today screen shows NES look top-to-bottom.

- [ ] **Step 4: Commit**

```bash
git add mobile/src/screens/TodayScreen.tsx
git commit -m "feat(mobile): retro TodayScreen"
```

---

### Task E7: Restyle `WeekScreen` header

**Files:**
- Modify: `mobile/src/screens/WeekScreen.tsx`

- [ ] **Step 1: Update header bar styles**

Change the prev/next chevrons, week-range label, and "JUMP TO TODAY" button to use NES fonts and a bordered container. Replace the `bg-bg-card` border bottom with a 2px line.

- [ ] **Step 2: Typecheck**

Run: `cd mobile && npx tsc --noEmit`
Expected: 0 errors.

- [ ] **Step 3: Commit**

```bash
git add mobile/src/screens/WeekScreen.tsx
git commit -m "feat(mobile): retro WeekScreen header"
```

---

### Task E8: Restyle `WorkoutDetailScreen`

**Files:**
- Modify: `mobile/src/screens/WorkoutDetailScreen.tsx`

- [ ] **Step 1: Restyle blocks**

Apply NES styling: header back button as `← BACK`, title in `PressStart2P` capitalized, prescription/intent block headers in pixel font, body markdown in VT323. Comparison panel → 2px hard borders, monospace numbers. Skip button → `RetroButton tone="danger"`. Add an `EDIT` button next to Back that opens EditQuestSheet (wired in Phase F).

- [ ] **Step 2: Typecheck**

Run: `cd mobile && npx tsc --noEmit`
Expected: 0 errors.

- [ ] **Step 3: Commit**

```bash
git add mobile/src/screens/WorkoutDetailScreen.tsx
git commit -m "feat(mobile): retro WorkoutDetailScreen"
```

---

### Task E9: Restyle `SettingsScreen`

**Files:**
- Modify: `mobile/src/screens/SettingsScreen.tsx`

- [ ] **Step 1: Restyle blocks**

Wrap each card in `RetroBorder`. Headers in PressStart2P. Body labels/values in VT323. Reauth/sync buttons as RetroButton. Sign out as RetroButton tone="danger".

- [ ] **Step 2: Typecheck**

Run: `cd mobile && npx tsc --noEmit`
Expected: 0 errors.

- [ ] **Step 3: Commit**

```bash
git add mobile/src/screens/SettingsScreen.tsx
git commit -m "feat(mobile): retro SettingsScreen"
```

---

### Task E10: Restyle bottom-tab navigator

**Files:**
- Modify: `mobile/src/navigation/RootNavigator.tsx`

- [ ] **Step 1: Update tabBarStyle, labels, icons**

Tab bar: `backgroundColor: colors.bgPanel`, `borderTopColor: colors.line`, `borderTopWidth: 2`. `tabBarLabelStyle: { fontFamily: 'PressStart2P', fontSize: 8 }`. Replace the existing bullet/dot icons with single-character pixel symbols (e.g., `▣ ▦ ◇ ⚙` per tab) using PressStart2P.

- [ ] **Step 2: Typecheck**

Run: `cd mobile && npx tsc --noEmit`
Expected: 0 errors.

- [ ] **Step 3: Commit**

```bash
git add mobile/src/navigation/RootNavigator.tsx
git commit -m "feat(mobile): retro bottom tab styling"
```

---

## Phase F — Edit feature wiring

### Task F1: `EditQuestSheet` component

**Files:**
- Create: `mobile/src/components/EditQuestSheet.tsx`

- [ ] **Step 1: Build the sheet**

```tsx
import BottomSheet, { BottomSheetScrollView } from '@gorhom/bottom-sheet';
import { forwardRef, useMemo, useState } from 'react';
import { Pressable, Text, TextInput, View } from 'react-native';

import type { EditWorkoutRequest, PlannedWorkoutOut } from '@/api/types';
import { RetroBorder } from '@/components/retro/RetroBorder';
import { RetroButton } from '@/components/retro/RetroButton';
import { colors } from '@/theme/tokens';

interface QuickPick {
  type: string;
  label: string;
  family: 'running' | 'strength' | 'other';
  defaultDistanceMi: number | null;
  defaultDurationMin: number | null;
  defaultTitle: string;
}

const QUICK_PICKS: QuickPick[] = [
  { type: 'easy', label: 'EASY',     family: 'running',  defaultDistanceMi: 5,  defaultDurationMin: 50,  defaultTitle: 'Easy run' },
  { type: 'tempo', label: 'TEMPO',   family: 'running',  defaultDistanceMi: 6,  defaultDurationMin: 55,  defaultTitle: 'Tempo run' },
  { type: 'long', label: 'LONG',     family: 'running',  defaultDistanceMi: 12, defaultDurationMin: 120, defaultTitle: 'Long run' },
  { type: 'intervals', label: 'INTERVAL', family: 'running', defaultDistanceMi: 6, defaultDurationMin: 50, defaultTitle: 'Intervals' },
  { type: 'strength_a', label: 'STR-A', family: 'strength', defaultDistanceMi: null, defaultDurationMin: 45, defaultTitle: 'Strength A' },
  { type: 'strength_b', label: 'STR-B', family: 'strength', defaultDistanceMi: null, defaultDurationMin: 45, defaultTitle: 'Strength B' },
  { type: 'cross', label: 'CROSS',   family: 'other',    defaultDistanceMi: null, defaultDurationMin: 45, defaultTitle: 'Cross-train' },
  { type: 'rest', label: 'REST',     family: 'other',    defaultDistanceMi: null, defaultDurationMin: 0,  defaultTitle: 'Rest' },
];

interface Props {
  workout: PlannedWorkoutOut | null;
  submitting: boolean;
  onConfirm: (body: EditWorkoutRequest) => void;
  onClose: () => void;
}

export const EditQuestSheet = forwardRef<BottomSheet, Props>(function EditQuestSheet(
  { workout, submitting, onConfirm, onClose }, ref,
) {
  const snapPoints = useMemo(() => ['70%', '95%'], []);
  const [picked, setPicked] = useState<QuickPick | null>(null);
  const [tweaking, setTweaking] = useState(false);
  const [distance, setDistance] = useState('');
  const [duration, setDuration] = useState('');
  const [title, setTitle] = useState('');

  const choosePick = (p: QuickPick) => {
    setPicked(p);
    setDistance(p.defaultDistanceMi !== null ? String(p.defaultDistanceMi) : '');
    setDuration(p.defaultDurationMin !== null ? String(p.defaultDurationMin) : '');
    setTitle(p.defaultTitle);
  };

  const submit = () => {
    if (picked === null) return;
    const body: EditWorkoutRequest = { type: picked.type, title };
    const d = parseFloat(distance);
    if (!Number.isNaN(d)) body.distance_mi = d;
    else body.distance_mi = null;
    const m = parseInt(duration, 10);
    if (!Number.isNaN(m)) body.duration_min = m;
    else body.duration_min = null;
    onConfirm(body);
  };

  return (
    <BottomSheet
      ref={ref}
      index={-1}
      snapPoints={snapPoints}
      enablePanDownToClose
      onClose={onClose}
      backgroundStyle={{ backgroundColor: colors.bgPanel, borderTopWidth: 2, borderColor: colors.line, borderRadius: 0 }}
      handleIndicatorStyle={{ backgroundColor: colors.inkDim }}
    >
      <BottomSheetScrollView contentContainerStyle={{ padding: 20, paddingBottom: 40 }}>
        <Text style={{ fontFamily: 'PressStart2P', fontSize: 14, color: colors.accentHi, marginBottom: 14 }}>
          EDIT QUEST
        </Text>
        {workout !== null && (
          <Text style={{ fontFamily: 'VT323', fontSize: 16, color: colors.inkDim, marginBottom: 14 }}>
            currently: {workout.title}
          </Text>
        )}

        <Text style={{ fontFamily: 'PressStart2P', fontSize: 8, color: colors.inkDim, marginBottom: 8, letterSpacing: 1 }}>
          QUICK PICK
        </Text>
        <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: 8, marginBottom: 16 }}>
          {QUICK_PICKS.map((p) => {
            const selected = picked?.type === p.type;
            return (
              <Pressable
                key={p.type}
                onPress={() => { choosePick(p); }}
                style={{
                  borderWidth: 2,
                  borderColor: selected ? colors.accentRun : colors.line,
                  backgroundColor: selected ? colors.accentRun : colors.bgPanelAlt,
                  paddingHorizontal: 10,
                  paddingVertical: 8,
                  width: '47%',
                }}
              >
                <Text style={{
                  fontFamily: 'PressStart2P', fontSize: 8,
                  color: selected ? colors.bg : colors.ink,
                  letterSpacing: 1, textAlign: 'center',
                }}>
                  {p.label}
                </Text>
              </Pressable>
            );
          })}
        </View>

        <Pressable onPress={() => { setTweaking((t) => !t); }} hitSlop={6}>
          <Text style={{ fontFamily: 'PressStart2P', fontSize: 8, color: colors.accentRun, marginBottom: 8 }}>
            {tweaking ? '▾ HIDE STATS' : '▸ TWEAK STATS'}
          </Text>
        </Pressable>

        {tweaking && (
          <RetroBorder style={{ marginBottom: 16 }} background={colors.bgPanelAlt}>
            <View style={{ padding: 12 }}>
              <Text style={{ fontFamily: 'PressStart2P', fontSize: 8, color: colors.inkDim, marginBottom: 4 }}>DISTANCE (MI)</Text>
              <TextInput value={distance} onChangeText={setDistance} keyboardType="decimal-pad"
                style={{ fontFamily: 'VT323', fontSize: 18, color: colors.ink, padding: 6, borderWidth: 2, borderColor: colors.line, marginBottom: 10 }} />
              <Text style={{ fontFamily: 'PressStart2P', fontSize: 8, color: colors.inkDim, marginBottom: 4 }}>DURATION (MIN)</Text>
              <TextInput value={duration} onChangeText={setDuration} keyboardType="number-pad"
                style={{ fontFamily: 'VT323', fontSize: 18, color: colors.ink, padding: 6, borderWidth: 2, borderColor: colors.line, marginBottom: 10 }} />
              <Text style={{ fontFamily: 'PressStart2P', fontSize: 8, color: colors.inkDim, marginBottom: 4 }}>TITLE</Text>
              <TextInput value={title} onChangeText={setTitle}
                style={{ fontFamily: 'VT323', fontSize: 18, color: colors.ink, padding: 6, borderWidth: 2, borderColor: colors.line }} />
            </View>
          </RetroBorder>
        )}

        <View style={{ flexDirection: 'row', gap: 12, marginTop: 8 }}>
          <View style={{ flex: 1 }}>
            <RetroButton label="Cancel" onPress={onClose} disabled={submitting} />
          </View>
          <View style={{ flex: 1 }}>
            <RetroButton label="Confirm" tone="primary" onPress={submit} disabled={submitting || picked === null} />
          </View>
        </View>
      </BottomSheetScrollView>
    </BottomSheet>
  );
});
```

- [ ] **Step 2: Typecheck**

Run: `cd mobile && npx tsc --noEmit`
Expected: 0 errors.

- [ ] **Step 3: Commit**

```bash
git add mobile/src/components/EditQuestSheet.tsx
git commit -m "feat(mobile): EditQuestSheet (quick-pick + tweak stats)"
```

---

### Task F2: `DisplacedSheet` component

**Files:**
- Create: `mobile/src/components/DisplacedSheet.tsx`

- [ ] **Step 1: Build the sheet**

```tsx
import BottomSheet, { BottomSheetScrollView } from '@gorhom/bottom-sheet';
import { forwardRef, useMemo } from 'react';
import { Pressable, Text, View } from 'react-native';

import type { PlannedWorkoutSnapshot } from '@/api/types';
import { RetroButton } from '@/components/retro/RetroButton';
import { addDays, fromIso, toIso } from '@/lib/dates';
import { colors } from '@/theme/tokens';

const DAY_LABELS = ['MON', 'TUE', 'WED', 'THU', 'FRI', 'SAT', 'SUN'];

interface Props {
  snapshot: PlannedWorkoutSnapshot | null;
  weekStartIso: string | null;  // Monday of the week we're picking from
  submitting: boolean;
  onPick: (newDate: string) => void;
  onDrop: () => void;
  onClose: () => void;
}

export const DisplacedSheet = forwardRef<BottomSheet, Props>(function DisplacedSheet(
  { snapshot, weekStartIso, submitting, onPick, onDrop, onClose }, ref,
) {
  const snapPoints = useMemo(() => ['55%'], []);
  const days = weekStartIso !== null
    ? Array.from({ length: 7 }, (_, i) => toIso(addDays(fromIso(weekStartIso), i)))
    : [];

  return (
    <BottomSheet
      ref={ref}
      index={-1}
      snapPoints={snapPoints}
      enablePanDownToClose
      onClose={onClose}
      backgroundStyle={{ backgroundColor: colors.bgPanel, borderTopWidth: 2, borderColor: colors.line, borderRadius: 0 }}
      handleIndicatorStyle={{ backgroundColor: colors.inkDim }}
    >
      <BottomSheetScrollView contentContainerStyle={{ padding: 20, paddingBottom: 40 }}>
        <Text style={{ fontFamily: 'PressStart2P', fontSize: 12, color: colors.accentHi, marginBottom: 6 }}>
          DISPLACED
        </Text>
        <Text style={{ fontFamily: 'VT323', fontSize: 18, color: colors.ink, marginBottom: 16 }}>
          {snapshot?.title ?? '—'}
        </Text>
        <Text style={{ fontFamily: 'PressStart2P', fontSize: 8, color: colors.inkDim, marginBottom: 10, letterSpacing: 1 }}>
          WHERE SHOULD IT GO?
        </Text>
        <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: 8, marginBottom: 18 }}>
          {days.map((iso, i) => (
            <Pressable
              key={iso}
              onPress={() => { onPick(iso); }}
              disabled={submitting}
              style={{
                borderWidth: 2, borderColor: colors.line,
                backgroundColor: colors.bgPanelAlt,
                paddingHorizontal: 10, paddingVertical: 8, width: '22%',
              }}
            >
              <Text style={{ fontFamily: 'PressStart2P', fontSize: 8, color: colors.ink, textAlign: 'center', letterSpacing: 1 }}>
                {DAY_LABELS[i]}
              </Text>
            </Pressable>
          ))}
        </View>
        <RetroButton label="Drop it" tone="danger" onPress={onDrop} disabled={submitting} />
      </BottomSheetScrollView>
    </BottomSheet>
  );
});
```

- [ ] **Step 2: Typecheck**

Run: `cd mobile && npx tsc --noEmit`
Expected: 0 errors.

- [ ] **Step 3: Commit**

```bash
git add mobile/src/components/DisplacedSheet.tsx
git commit -m "feat(mobile): DisplacedSheet (day picker + DROP IT)"
```

---

### Task F3: Wire EDIT button onto Today + Week + Detail screens

**Files:**
- Modify: `mobile/src/screens/TodayScreen.tsx`
- Modify: `mobile/src/screens/WeekScreen.tsx`
- Modify: `mobile/src/screens/WorkoutDetailScreen.tsx`

- [ ] **Step 1: TodayScreen — add EditQuestSheet + DisplacedSheet refs and state**

In `mobile/src/screens/TodayScreen.tsx`, alongside the existing `whyWorkout` state, add:

```tsx
import { EditQuestSheet } from '@/components/EditQuestSheet';
import { DisplacedSheet } from '@/components/DisplacedSheet';
import { ProposalSheet } from '@/components/ProposalSheet';
import { useEditWorkout } from '@/api/hooks/useEditWorkout';
import { useRescheduleOriginal } from '@/api/hooks/useRescheduleOriginal';
import type { EditWorkoutRequest, PlannedWorkoutOut, PlannedWorkoutSnapshot, ProposalOut } from '@/api/types';
import { startOfWeek, toIso } from '@/lib/dates';

// inside the TodayScreen component:
const editSheetRef = useRef<BottomSheet>(null);
const displacedSheetRef = useRef<BottomSheet>(null);
const proposalSheetRef = useRef<BottomSheet>(null);
const [editTarget, setEditTarget] = useState<PlannedWorkoutOut | null>(null);
const [displaced, setDisplaced] = useState<{ workoutId: string; snapshot: PlannedWorkoutSnapshot } | null>(null);
const [proposal, setProposal] = useState<{ workoutId: string; data: ProposalOut } | null>(null);
const editMut = useEditWorkout();
const reschedMut = useRescheduleOriginal();

const openEdit = (w: PlannedWorkoutOut) => {
  setEditTarget(w);
  editSheetRef.current?.snapToIndex(0);
};

const handleEditConfirm = (body: EditWorkoutRequest) => {
  if (editTarget === null) return;
  editMut.mutate(
    { workoutId: editTarget.id, body, preEditSnapshot: editTarget.original_snapshot },
    {
      onSuccess: ({ workout, firstEdit }) => {
        editSheetRef.current?.close();
        if (firstEdit && workout.original_snapshot !== null) {
          setDisplaced({ workoutId: workout.id, snapshot: workout.original_snapshot });
          displacedSheetRef.current?.snapToIndex(0);
        }
      },
    },
  );
};

const handleDisplacedPick = (newDate: string) => {
  if (displaced === null) return;
  reschedMut.mutate(
    { workoutId: displaced.workoutId, body: { new_date: newDate } },
    {
      onSuccess: (data) => {
        displacedSheetRef.current?.close();
        setDisplaced(null);
        setProposal({ workoutId: data.new_workout_id, data: data.proposal });
        proposalSheetRef.current?.snapToIndex(0);
      },
    },
  );
};

const handleDisplacedDrop = () => {
  displacedSheetRef.current?.close();
  setDisplaced(null);
};

const handleProposalApply = async (choice: 'option_a' | 'option_b' | 'just_move' | 'cancel') => {
  if (proposal === null) return;
  // hit /workouts/{newId}/apply-move directly via existing useApplyMove if you want;
  // easier here: inline the call since we already have the workoutId
  const { api } = await import('@/api/client');
  await api.post(`/workouts/${proposal.workoutId}/apply-move`, {
    proposal_id: proposal.data.proposal_id, choice,
  });
  proposalSheetRef.current?.close();
  setProposal(null);
};
```

(Inline-import `api` to avoid restructuring the hook layer; alternatively, refactor to use the existing `useApplyMove` hook — see Task F4.)

Pass `onEdit={() => openEdit(w)}` to each `<WorkoutCard>` instance. Render the three sheets at the end of the component:

```tsx
<EditQuestSheet ref={editSheetRef} workout={editTarget} submitting={editMut.isPending}
  onConfirm={handleEditConfirm} onClose={() => editSheetRef.current?.close()} />
<DisplacedSheet ref={displacedSheetRef}
  snapshot={displaced?.snapshot ?? null}
  weekStartIso={today.data !== undefined ? toIso(startOfWeek(fromIso(today.data.date))) : null}
  submitting={reschedMut.isPending}
  onPick={handleDisplacedPick}
  onDrop={handleDisplacedDrop}
  onClose={() => displacedSheetRef.current?.close()} />
<ProposalSheet ref={proposalSheetRef}
  proposal={proposal?.data ?? null}
  submitting={false}
  onApply={(c) => handleProposalApply(c)}
  onCancel={() => handleProposalApply('cancel')} />
```

- [ ] **Step 2: WeekScreen — same wiring**

Repeat the same state + handlers in `WeekScreen.tsx`. The week-start for DisplacedSheet is the visible week (already in `cursorIso`).

- [ ] **Step 3: WorkoutDetailScreen — add EDIT button**

In `WorkoutDetailScreen.tsx`, add an EDIT button next to Back. Tapping it `navigation.goBack()` then opens edit on the previous screen — simpler: add the same EditQuestSheet/DisplacedSheet/ProposalSheet wiring inline on the detail screen too.

- [ ] **Step 4: Typecheck**

Run: `cd mobile && npx tsc --noEmit`
Expected: 0 errors.

- [ ] **Step 5: Smoke test (full flow)**

Reload :19006 → log in → Today → tap EDIT on Strength A → pick EASY → CONFIRM → DisplacedSheet opens → pick FRI → ProposalSheet opens with rebalance options → tap Cancel → row disappears (the Friday-cloned strength is deleted because of the cancel-deletes sentinel).

Repeat with Apply (option_a) → row stays.
Repeat with Drop It → no Friday strength row created.

- [ ] **Step 6: Commit**

```bash
git add mobile/src/screens/
git commit -m "feat(mobile): wire EditQuestSheet + DisplacedSheet + ProposalSheet on Today/Week/Detail"
```

---

### Task F4 (optional): Extract edit-flow hook

**Files:**
- Create: `mobile/src/hooks/useEditFlow.ts`

- [ ] **Step 1: Build the hook**

If Task F3 ended up duplicating sheet-state across three screens, extract the state (editTarget, displaced, proposal, ref handles, all handlers) into one hook so each screen does:

```tsx
const flow = useEditFlow({ weekStartIso });
// flow.openEdit(w), flow.sheets, etc.
```

The hook returns `{ openEdit, sheets: { edit, displaced, proposal }, refs }` so screens just render `<EditQuestSheet ref={refs.edit} {...sheets.edit} />` etc.

- [ ] **Step 2: Refactor screens to use it**

- [ ] **Step 3: Typecheck**

Run: `cd mobile && npx tsc --noEmit`
Expected: 0 errors.

- [ ] **Step 4: Commit**

```bash
git add mobile/
git commit -m "refactor(mobile): extract useEditFlow shared hook"
```

(Skip this task if duplication is acceptable.)

---

## Phase G — Final QA + close-out

### Task G1: Backend regression run

- [ ] **Step 1: Run all backend tests**

Run: `docker compose exec -T api pytest -v`
Expected: ALL PASS.

- [ ] **Step 2: Lint clean**

Run: `docker compose exec -T api ruff check . && docker compose exec -T api ruff format --check .`
Expected: zero errors.

- [ ] **Step 3: If anything fails, fix and commit**

```bash
git commit -m "chore: lint fixes for edit feature"
```

---

### Task G2: Mobile typecheck + smoke

- [ ] **Step 1: Final typecheck**

Run: `cd mobile && npx tsc --noEmit`
Expected: 0 errors.

- [ ] **Step 2: Manual smoke (web)**

Reload http://localhost:19006:
- Login renders NES style
- Today shows NES workout cards with EDIT button
- EDIT → quick-pick → CONFIRM → DisplacedSheet → day pick → ProposalSheet → all four choices behave correctly
- Drop-it path leaves no orphan rows (verify via `docker compose exec -T db psql -U marathon -d marathon -c "SELECT count(*) FROM planned_workouts;"` before/after — count should be the same)
- Drag-to-move still works (existing flow unaffected)
- Why? sheet still works
- Settings + reauth + sync UI looks right

- [ ] **Step 3: Document any web-only bugs as known issues**

Add a note at the bottom of the spec file under §8 if any bug surfaces.

---

### Task G3: Update CLAUDE.md / PROJECT_TRACKER.md / MEMORY.md

Per the global Session Close-Out Protocol:

- [ ] **Step 1: Update project CLAUDE.md** with any lessons learned (e.g. if Reanimated v4 web required a workaround, document it).

- [ ] **Step 2: Create / update PROJECT_TRACKER.md** with this sprint's deliverables.

- [ ] **Step 3: Update MEMORY.md** with current status.

- [ ] **Step 4: Run /update-notion** to sync the project tracker to Notion.

- [ ] **Step 5: Commit**

```bash
git add CLAUDE.md PROJECT_TRACKER.md MEMORY.md
git commit -m "docs: session close-out for edit + retro feature"
```

---

## Self-review (writing-plans skill)

**Spec coverage:**
- §3 Scope (in/out): every in-scope item maps to A1–F4. Editable fields → A3+B1. Quick-pick types → F1. AI rebalance on reassignment → B4. Full retro restyle → C1–C6 + E1–E10. ✓
- §4 Data model: A1 (column) + A2 (schema). ✓
- §5 Backend endpoints: B1–B6. Allowed quick-pick types are enforced via Pydantic `WorkoutType` enum (validated implicitly in B1). ✓
- §6 Mobile UX: C1–C6 + E1–E10 + F1–F4. ✓
- §7 Build sequence: phases A→F mirror it. ✓
- §8 Risks: G2 covers Reanimated/web smoke; cancel-deletes-row regression is covered by B6 + the explicit move-test re-run.
- §9 Done criteria: G1 + G2 walk every item.

**Placeholder scan:** Task F4 is marked optional ("Skip this task if duplication is acceptable") — that's a real fork, not a placeholder. No "TBD"/"figure out later"/"add error handling" anywhere else.

**Type consistency:**
- `EditWorkoutRequest`, `RescheduleOriginalRequest`, `RescheduleOriginalResponse` defined in A3 used identically in B1, B4, D1, D2, D3, F1, F3.
- `PlannedWorkoutSnapshot` first appears in D1 and is used in D2, F2, F3.
- `original_snapshot` field name consistent everywhere.
- `created_by="reschedule_original"` sentinel matches in B3 (set), B4 (set via the param), B6 (read).

No issues found.

