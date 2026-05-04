# Session 1: Backend Foundation — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Stand up a working FastAPI + PostgreSQL backend that serves the full marathon trilogy training plan, authenticates via JWT, syncs from Garmin, and reconciles planned vs completed workouts.

**Architecture:** Single FastAPI process with async SQLAlchemy 2.0 + asyncpg hitting PostgreSQL 16. Docker Compose for local dev. Plan data parsed from `PLAN.md` and seeded into the DB. Garmin sync via `python-garminconnect` wrapped in `asyncio.to_thread`. Reconciler matches completed workouts to planned ones by date + family.

**Tech Stack:** Python 3.12, uv, FastAPI, Pydantic v2, SQLAlchemy 2.0 (async), Alembic, asyncpg, python-garminconnect, python-jose, passlib, pytest, ruff

---

## File Structure

```
marathon_app/
├── SPEC.md                          # existing — do not modify
├── PLAN.md                          # existing — do not modify
├── schema.sql                       # existing — do not modify
├── SESSION_1.md                     # existing — do not modify
├── pyproject.toml                   # project config, deps, ruff settings
├── Dockerfile                       # API container
├── docker-compose.yml               # postgres + api
├── .env.example                     # env template
├── .env                             # actual env (gitignored)
├── .gitignore
├── alembic.ini                      # alembic config
├── alembic/
│   ├── env.py                       # async migration runner
│   └── versions/                    # migration files
├── app/
│   ├── __init__.py
│   ├── main.py                      # FastAPI app, lifespan, router includes
│   ├── config.py                    # pydantic-settings Settings class
│   ├── db.py                        # async engine, session factory
│   ├── auth.py                      # JWT issue/verify, password hash/verify
│   ├── deps.py                      # get_db, get_current_athlete dependencies
│   ├── models/
│   │   ├── __init__.py              # re-exports all models (for Alembic)
│   │   ├── base.py                  # DeclarativeBase, UUIDMixin, TimestampMixin
│   │   ├── athlete.py               # Athlete model
│   │   ├── plan.py                  # Plan, Cycle models
│   │   ├── workout.py               # PlannedWorkout, CompletedWorkout models
│   │   ├── reconciliation.py        # Reconciliation model
│   │   ├── metrics.py               # DailyMetric model
│   │   ├── agent.py                 # AgentMessage model
│   │   └── garmin.py                # GarminAuthState model
│   ├── schemas/
│   │   ├── __init__.py
│   │   ├── auth.py                  # LoginRequest, TokenResponse
│   │   ├── plan.py                  # PlanOut, CycleOut, CycleProgress
│   │   ├── workout.py               # PlannedWorkoutOut, CompletedWorkoutOut, WorkoutDetailOut
│   │   ├── metrics.py               # DailyMetricOut
│   │   └── garmin.py                # GarminStatusOut, GarminReauthRequest, SyncReport
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── auth.py                  # POST /auth/login
│   │   ├── plan.py                  # GET /plan/current, /plan/today, /plan/week
│   │   ├── workouts.py              # GET /workouts/{id}
│   │   ├── metrics.py               # GET /metrics/recent
│   │   ├── garmin.py                # POST /garmin/reauth, GET /garmin/status
│   │   ├── admin.py                 # POST /admin/sync
│   │   └── chat.py                  # stub: returns 501
│   ├── services/
│   │   ├── __init__.py
│   │   ├── garmin_sync.py           # GarminSyncService
│   │   ├── reconciler.py            # reconcile()
│   │   ├── agent_context.py         # stub build_athlete_context()
│   │   └── agents/
│   │       ├── __init__.py
│   │       ├── daily_coach.py       # stub
│   │       ├── plan_adapter.py      # stub
│   │       └── run_analyst.py       # stub
│   ├── seed/
│   │   ├── __init__.py
│   │   ├── plan_parser.py           # parse PLAN.md into structured data
│   │   └── load_plan.py             # CLI entry point, DB insertion
│   └── lib/
│       ├── __init__.py
│       └── workout_family.py        # type -> family mapping
└── tests/
    ├── __init__.py
    ├── conftest.py                  # fixtures: test DB, async session, seeded data
    ├── test_workout_family.py
    ├── test_seed.py
    ├── test_auth.py
    ├── test_plan_routes.py
    └── test_reconciler.py
```

---

## Task 1: Project Skeleton — pyproject.toml, Docker, Config

**Files:**
- Create: `pyproject.toml`
- Create: `Dockerfile`
- Create: `docker-compose.yml`
- Create: `.env.example`
- Create: `.env`
- Create: `.gitignore`
- Create: `app/__init__.py`
- Create: `app/config.py`

- [ ] **Step 1: Create `.gitignore`**

```gitignore
__pycache__/
*.pyc
.env
*.egg-info/
dist/
.venv/
data/
.pytest_cache/
.ruff_cache/
alembic/versions/*.pyc
node_modules/
mobile/.expo/
```

- [ ] **Step 2: Create `pyproject.toml`**

```toml
[project]
name = "marathon-coach"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = [
    "fastapi>=0.115.0",
    "uvicorn[standard]>=0.30.0",
    "pydantic>=2.9.0",
    "pydantic-settings>=2.5.0",
    "sqlalchemy[asyncio]>=2.0.35",
    "asyncpg>=0.30.0",
    "alembic>=1.14.0",
    "python-jose[cryptography]>=3.3.0",
    "passlib[bcrypt]>=1.7.4",
    "python-garminconnect>=0.2.19",
    "anthropic>=0.39.0",
    "apscheduler>=3.10.0",
    "httpx>=0.27.0",
    "pyyaml>=6.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.3.0",
    "pytest-asyncio>=0.24.0",
    "httpx>=0.27.0",
    "ruff>=0.7.0",
]

[tool.ruff]
target-version = "py312"
line-length = 99

[tool.ruff.lint]
select = ["E", "F", "I", "UP", "B", "SIM"]

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
```

- [ ] **Step 3: Create `.env.example` and `.env`**

`.env.example`:
```env
DATABASE_URL=postgresql+asyncpg://marathon:marathon@db:5432/marathon
SECRET_KEY=change-me-to-a-real-secret
SEED_PASSWORD=change-me
ANTHROPIC_API_KEY=sk-ant-...
TZ=America/New_York
```

`.env` — copy from `.env.example` with real values (use `marathon` for SEED_PASSWORD in dev).

- [ ] **Step 4: Create `Dockerfile`**

```dockerfile
FROM python:3.12-slim

WORKDIR /app

RUN pip install uv

COPY pyproject.toml .
RUN uv pip install --system -e ".[dev]"

COPY . .

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
```

- [ ] **Step 5: Create `docker-compose.yml`**

```yaml
services:
  db:
    image: postgres:16-alpine
    environment:
      POSTGRES_USER: marathon
      POSTGRES_PASSWORD: marathon
      POSTGRES_DB: marathon
    ports:
      - "5432:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U marathon"]
      interval: 5s
      timeout: 3s
      retries: 5

  api:
    build: .
    ports:
      - "8000:8000"
    env_file: .env
    volumes:
      - .:/app
      - ./data:/app/data
    depends_on:
      db:
        condition: service_healthy

volumes:
  pgdata:
```

- [ ] **Step 6: Create `app/__init__.py`** (empty file)

- [ ] **Step 7: Create `app/config.py`**

```python
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    database_url: str = "postgresql+asyncpg://marathon:marathon@db:5432/marathon"
    secret_key: str = "change-me-to-a-real-secret"
    seed_password: str = "marathon"
    anthropic_api_key: str = ""
    tz: str = "America/New_York"
    jwt_expiry_days: int = 30


settings = Settings()
```

- [ ] **Step 8: Create `app/db.py`**

```python
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings

engine = create_async_engine(settings.database_url, echo=False)
async_session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
```

- [ ] **Step 9: Create `app/main.py`** (minimal, just health check)

```python
from contextlib import asynccontextmanager

from fastapi import FastAPI


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


app = FastAPI(title="Marathon Coach", lifespan=lifespan)


@app.get("/health")
async def health():
    return {"status": "ok"}
```

- [ ] **Step 10: Verify Docker Compose starts**

```bash
cd "C:/Coding Projects/marathon_app"
docker compose up --build -d
# Wait for healthy
docker compose ps
curl http://localhost:8000/health
# Expected: {"status":"ok"}
```

- [ ] **Step 11: Commit**

```bash
git add pyproject.toml Dockerfile docker-compose.yml .env.example .gitignore app/__init__.py app/config.py app/db.py app/main.py
git commit -m "feat: project skeleton with Docker Compose, FastAPI, config"
```

---

## Task 2: SQLAlchemy Models

**Files:**
- Create: `app/models/__init__.py`
- Create: `app/models/base.py`
- Create: `app/models/athlete.py`
- Create: `app/models/plan.py`
- Create: `app/models/workout.py`
- Create: `app/models/reconciliation.py`
- Create: `app/models/metrics.py`
- Create: `app/models/agent.py`
- Create: `app/models/garmin.py`

- [ ] **Step 1: Create `app/models/base.py`**

```python
import uuid
from datetime import datetime

from sqlalchemy import func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class UUIDMixin:
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), onupdate=func.now(), nullable=False
    )
```

- [ ] **Step 2: Create `app/models/athlete.py`**

```python
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin


class Athlete(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "athletes"

    name: Mapped[str] = mapped_column(Text, nullable=False)
    email: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(Text, nullable=False)
    hr_zones_json: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    pace_targets_json: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    injury_notes_md: Mapped[str | None] = mapped_column(Text, nullable=True)

    plans: Mapped[list["Plan"]] = relationship(back_populates="athlete")
```

- [ ] **Step 3: Create `app/models/plan.py`**

```python
import uuid
from datetime import date, datetime

from sqlalchemy import Boolean, Date, ForeignKey, SmallInteger, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, UUIDMixin


class Plan(UUIDMixin, Base):
    __tablename__ = "plans"

    athlete_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("athletes.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(Text, nullable=False)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    philosophy_md: Mapped[str] = mapped_column(Text, nullable=False, server_default="")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")
    created_at: Mapped[datetime] = mapped_column(
        server_default="now()", nullable=False
    )

    athlete: Mapped["Athlete"] = relationship(back_populates="plans")
    cycles: Mapped[list["Cycle"]] = relationship(back_populates="plan")


class Cycle(UUIDMixin, Base):
    __tablename__ = "cycles"

    plan_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("plans.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(Text, nullable=False)
    sequence: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    race_name: Mapped[str] = mapped_column(Text, nullable=False)
    race_date: Mapped[date] = mapped_column(Date, nullable=False)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    peak_week_target: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    notes_md: Mapped[str] = mapped_column(Text, nullable=False, server_default="")

    plan: Mapped["Plan"] = relationship(back_populates="cycles")
    planned_workouts: Mapped[list["PlannedWorkout"]] = relationship(back_populates="cycle")
```

- [ ] **Step 4: Create `app/models/workout.py`**

```python
import enum
import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    Date,
    BigInteger,
    Enum,
    ForeignKey,
    Integer,
    Numeric,
    SmallInteger,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, UUIDMixin


class WorkoutType(str, enum.Enum):
    easy = "easy"
    long = "long"
    tempo = "tempo"
    intervals = "intervals"
    hills = "hills"
    mp_long = "mp_long"
    recovery = "recovery"
    strides = "strides"
    strength_a = "strength_a"
    strength_b = "strength_b"
    cross = "cross"
    rest = "rest"
    race = "race"


class WorkoutFamily(str, enum.Enum):
    running = "running"
    strength = "strength"
    other = "other"


class WorkoutStatus(str, enum.Enum):
    planned = "planned"
    moved = "moved"
    skipped = "skipped"
    done = "done"


class PlannedWorkout(UUIDMixin, Base):
    __tablename__ = "planned_workouts"

    cycle_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("cycles.id", ondelete="CASCADE"), nullable=False
    )
    scheduled_date: Mapped[date] = mapped_column(Date, nullable=False)
    original_date: Mapped[date] = mapped_column(Date, nullable=False)
    week_number: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    type: Mapped[WorkoutType] = mapped_column(
        Enum(WorkoutType, name="workout_type", create_constraint=False, native_enum=True),
        nullable=False,
    )
    family: Mapped[WorkoutFamily] = mapped_column(
        Enum(WorkoutFamily, name="workout_family", create_constraint=False, native_enum=True),
        nullable=False,
    )
    status: Mapped[WorkoutStatus] = mapped_column(
        Enum(WorkoutStatus, name="workout_status", create_constraint=False, native_enum=True),
        nullable=False,
        server_default="planned",
    )
    duration_min: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    distance_mi: Mapped[Decimal | None] = mapped_column(Numeric(4, 1), nullable=True)
    target_pace: Mapped[str | None] = mapped_column(Text, nullable=True)
    target_hr_zone: Mapped[str | None] = mapped_column(Text, nullable=True)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    description_md: Mapped[str] = mapped_column(Text, nullable=False)
    intent_md: Mapped[str] = mapped_column(Text, nullable=False, server_default="")
    created_at: Mapped[datetime] = mapped_column(server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), onupdate=func.now(), nullable=False
    )

    cycle: Mapped["Cycle"] = relationship(back_populates="planned_workouts")


class CompletedWorkout(UUIDMixin, Base):
    __tablename__ = "completed_workouts"

    athlete_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("athletes.id", ondelete="CASCADE"), nullable=False
    )
    garmin_activity_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False)
    activity_date: Mapped[date] = mapped_column(Date, nullable=False)
    started_at: Mapped[datetime] = mapped_column(nullable=False)
    activity_type: Mapped[str] = mapped_column(Text, nullable=False)
    family: Mapped[WorkoutFamily] = mapped_column(
        Enum(WorkoutFamily, name="workout_family", create_constraint=False, native_enum=True),
        nullable=False,
    )
    duration_s: Mapped[int] = mapped_column(Integer, nullable=False)
    distance_m: Mapped[Decimal | None] = mapped_column(Numeric(8, 2), nullable=True)
    avg_hr: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    max_hr: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    avg_pace_s_per_km: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    elevation_gain_m: Mapped[Decimal | None] = mapped_column(Numeric(6, 1), nullable=True)
    calories: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    fit_file_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    raw_summary_json: Mapped[dict] = mapped_column(JSONB, nullable=False)
    synced_at: Mapped[datetime] = mapped_column(server_default=func.now(), nullable=False)
```

- [ ] **Step 5: Create `app/models/reconciliation.py`**

```python
import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import CheckConstraint, ForeignKey, Numeric, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, UUIDMixin


class Reconciliation(UUIDMixin, Base):
    __tablename__ = "reconciliations"
    __table_args__ = (
        CheckConstraint(
            "planned_id IS NOT NULL OR completed_id IS NOT NULL",
            name="recon_at_least_one",
        ),
    )

    athlete_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("athletes.id", ondelete="CASCADE"), nullable=False
    )
    planned_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("planned_workouts.id", ondelete="SET NULL"),
        nullable=True,
    )
    completed_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("completed_workouts.id", ondelete="SET NULL"),
        nullable=True,
    )
    match_confidence: Mapped[Decimal | None] = mapped_column(Numeric(3, 2), nullable=True)
    deviation_notes_md: Mapped[str] = mapped_column(Text, nullable=False, server_default="")
    agent_review_md: Mapped[str | None] = mapped_column(Text, nullable=True)
    agent_reviewed_at: Mapped[datetime | None] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now(), nullable=False)
```

- [ ] **Step 6: Create `app/models/metrics.py`**

```python
import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Date, ForeignKey, Integer, Numeric, SmallInteger, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, UUIDMixin


class DailyMetric(UUIDMixin, Base):
    __tablename__ = "daily_metrics"
    __table_args__ = (UniqueConstraint("athlete_id", "metric_date"),)

    athlete_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("athletes.id", ondelete="CASCADE"), nullable=False
    )
    metric_date: Mapped[date] = mapped_column(Date, nullable=False)
    sleep_score: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    sleep_duration_s: Mapped[int | None] = mapped_column(Integer, nullable=True)
    hrv_overnight_ms: Mapped[Decimal | None] = mapped_column(Numeric(5, 1), nullable=True)
    resting_hr: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    body_battery_high: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    body_battery_low: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    training_readiness: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    training_status: Mapped[str | None] = mapped_column(Text, nullable=True)
    raw_json: Mapped[dict] = mapped_column(JSONB, nullable=False)
    synced_at: Mapped[datetime] = mapped_column(server_default=func.now(), nullable=False)
```

- [ ] **Step 7: Create `app/models/agent.py`**

```python
import enum
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import Enum, ForeignKey, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, UUIDMixin


class AgentKind(str, enum.Enum):
    daily_coach = "daily_coach"
    plan_adapter = "plan_adapter"
    run_analyst = "run_analyst"
    user_chat = "user_chat"


class MessageRole(str, enum.Enum):
    system = "system"
    user = "user"
    assistant = "assistant"


class AgentMessage(UUIDMixin, Base):
    __tablename__ = "agent_messages"

    athlete_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("athletes.id", ondelete="CASCADE"), nullable=False
    )
    agent: Mapped[AgentKind] = mapped_column(
        Enum(AgentKind, name="agent_kind", create_constraint=False, native_enum=True),
        nullable=False,
    )
    role: Mapped[MessageRole] = mapped_column(
        Enum(MessageRole, name="message_role", create_constraint=False, native_enum=True),
        nullable=False,
    )
    content_md: Mapped[str] = mapped_column(Text, nullable=False)
    context_snapshot_json: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    related_workout_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("planned_workouts.id", ondelete="SET NULL"),
        nullable=True,
    )
    related_reconciliation_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("reconciliations.id", ondelete="SET NULL"),
        nullable=True,
    )
    proposal_state_json: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now(), nullable=False)
```

- [ ] **Step 8: Create `app/models/garmin.py`**

```python
import uuid
from datetime import datetime

from sqlalchemy import Boolean, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class GarminAuthState(Base):
    __tablename__ = "garmin_auth_state"

    athlete_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("athletes.id", ondelete="CASCADE"),
        primary_key=True,
    )
    token_dir_path: Mapped[str] = mapped_column(Text, nullable=False)
    last_successful_sync: Mapped[datetime | None] = mapped_column(nullable=True)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_error_at: Mapped[datetime | None] = mapped_column(nullable=True)
    needs_reauth: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
```

- [ ] **Step 9: Create `app/models/__init__.py`**

```python
from app.models.agent import AgentKind, AgentMessage, MessageRole
from app.models.athlete import Athlete
from app.models.base import Base
from app.models.garmin import GarminAuthState
from app.models.metrics import DailyMetric
from app.models.plan import Cycle, Plan
from app.models.reconciliation import Reconciliation
from app.models.workout import (
    CompletedWorkout,
    PlannedWorkout,
    WorkoutFamily,
    WorkoutStatus,
    WorkoutType,
)

__all__ = [
    "AgentKind",
    "AgentMessage",
    "Athlete",
    "Base",
    "CompletedWorkout",
    "Cycle",
    "DailyMetric",
    "GarminAuthState",
    "MessageRole",
    "Plan",
    "PlannedWorkout",
    "Reconciliation",
    "WorkoutFamily",
    "WorkoutStatus",
    "WorkoutType",
]
```

- [ ] **Step 10: Commit**

```bash
git add app/models/
git commit -m "feat: SQLAlchemy 2.0 models matching schema.sql"
```

---

## Task 3: Alembic Setup + Initial Migration

**Files:**
- Create: `alembic.ini`
- Create: `alembic/env.py`
- Generate: `alembic/versions/` (initial migration)

- [ ] **Step 1: Create `alembic.ini`**

```ini
[alembic]
script_location = alembic
sqlalchemy.url = postgresql+asyncpg://marathon:marathon@db:5432/marathon

[loggers]
keys = root,sqlalchemy,alembic

[handlers]
keys = console

[formatters]
keys = generic

[logger_root]
level = WARN
handlers = console

[logger_sqlalchemy]
level = WARN
handlers =
qualname = sqlalchemy.engine

[logger_alembic]
level = INFO
handlers =
qualname = alembic

[handler_console]
class = StreamHandler
args = (sys.stderr,)
level = NOTSET
formatter = generic

[formatter_generic]
format = %(levelname)-5.5s [%(name)s] %(message)s
datefmt = %H:%M:%S
```

- [ ] **Step 2: Create `alembic/env.py`**

```python
import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy.ext.asyncio import create_async_engine

from app.config import settings
from app.models import Base

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = settings.database_url
    context.configure(url=url, target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection):
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    connectable = create_async_engine(settings.database_url)
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
```

- [ ] **Step 3: Create `alembic/script.py.mako`**

```mako
"""${message}

Revision ID: ${up_revision}
Revises: ${down_revision | comma,n}
Create Date: ${create_date}

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
${imports if imports else ""}

# revision identifiers, used by Alembic.
revision: str = ${repr(up_revision)}
down_revision: Union[str, None] = ${repr(down_revision)}
branch_labels: Union[str, Sequence[str], None] = ${repr(branch_labels)}
depends_on: Union[str, Sequence[str], None] = ${repr(depends_on)}


def upgrade() -> None:
    ${upgrades if upgrades else "pass"}


def downgrade() -> None:
    ${downgrades if downgrades else "pass"}
```

- [ ] **Step 4: Generate initial migration inside Docker**

```bash
docker compose exec api alembic revision --autogenerate -m "initial schema"
```

- [ ] **Step 5: Run migration and verify**

```bash
docker compose exec api alembic upgrade head
docker compose exec api alembic check
# Expected: No new upgrade operations detected
```

- [ ] **Step 6: Commit**

```bash
git add alembic.ini alembic/
git commit -m "feat: Alembic setup with initial migration"
```

---

## Task 4: Auth — JWT + Password Hashing

**Files:**
- Create: `app/auth.py`
- Create: `app/deps.py`
- Create: `app/schemas/__init__.py`
- Create: `app/schemas/auth.py`
- Create: `app/routes/__init__.py`
- Create: `app/routes/auth.py`
- Create: `tests/__init__.py`
- Create: `tests/conftest.py`
- Create: `tests/test_auth.py`

- [ ] **Step 1: Create `app/auth.py`**

```python
from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

ALGORITHM = "HS256"


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def create_access_token(athlete_id: str) -> tuple[str, datetime]:
    expires = datetime.now(timezone.utc) + timedelta(days=settings.jwt_expiry_days)
    payload = {"sub": athlete_id, "exp": expires}
    token = jwt.encode(payload, settings.secret_key, algorithm=ALGORITHM)
    return token, expires


def decode_access_token(token: str) -> str | None:
    """Returns athlete_id or None if invalid."""
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[ALGORITHM])
        return payload.get("sub")
    except JWTError:
        return None
```

- [ ] **Step 2: Create `app/deps.py`**

```python
import uuid
from typing import AsyncGenerator

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import decode_access_token
from app.db import async_session_factory
from app.models.athlete import Athlete

security = HTTPBearer()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_factory() as session:
        yield session


async def get_current_athlete(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> Athlete:
    athlete_id = decode_access_token(credentials.credentials)
    if athlete_id is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    result = await db.execute(select(Athlete).where(Athlete.id == uuid.UUID(athlete_id)))
    athlete = result.scalar_one_or_none()
    if athlete is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Athlete not found")
    return athlete
```

- [ ] **Step 3: Create `app/schemas/__init__.py`** (empty) and `app/schemas/auth.py`

```python
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class LoginRequest(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    token: str
    expires_at: datetime
```

- [ ] **Step 4: Create `app/routes/__init__.py`** (empty) and `app/routes/auth.py`

```python
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import create_access_token, verify_password
from app.deps import get_db
from app.models.athlete import Athlete
from app.schemas.auth import LoginRequest, TokenResponse

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Athlete).where(Athlete.email == body.email))
    athlete = result.scalar_one_or_none()
    if athlete is None or not verify_password(body.password, athlete.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Bad credentials")
    token, expires = create_access_token(str(athlete.id))
    return TokenResponse(token=token, expires_at=expires)
```

- [ ] **Step 5: Wire auth router into `app/main.py`**

Update `app/main.py` to import and include the auth router:

```python
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.routes.auth import router as auth_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


app = FastAPI(title="Marathon Coach", lifespan=lifespan)
app.include_router(auth_router)


@app.get("/health")
async def health():
    return {"status": "ok"}
```

- [ ] **Step 6: Create `tests/__init__.py`** (empty) and `tests/conftest.py`**

```python
import uuid
from typing import AsyncGenerator

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.auth import hash_password
from app.config import settings
from app.db import async_session_factory
from app.deps import get_db
from app.main import app
from app.models import Base
from app.models.athlete import Athlete

# Use the same DB but with a test schema or just the dev DB for now
# In Docker, tests run against the same postgres
engine = create_async_engine(settings.database_url, echo=False)
test_session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


@pytest.fixture
async def db() -> AsyncGenerator[AsyncSession, None]:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with test_session_factory() as session:
        yield session
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
async def client(db: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    async def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
async def athlete(db: AsyncSession) -> Athlete:
    a = Athlete(
        id=uuid.uuid4(),
        name="Test Runner",
        email="test@marathon.dev",
        password_hash=hash_password("testpass"),
        hr_zones_json={"z1": [0, 130], "z2": [131, 145]},
        pace_targets_json={"easy": "12:00-13:30"},
        injury_notes_md="No current injuries",
    )
    db.add(a)
    await db.commit()
    await db.refresh(a)
    return a


@pytest.fixture
async def auth_token(athlete: Athlete) -> str:
    from app.auth import create_access_token

    token, _ = create_access_token(str(athlete.id))
    return token


@pytest.fixture
async def auth_headers(auth_token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {auth_token}"}
```

- [ ] **Step 7: Write `tests/test_auth.py`**

```python
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_login_success(client: AsyncClient, athlete):
    resp = await client.post("/auth/login", json={"email": "test@marathon.dev", "password": "testpass"})
    assert resp.status_code == 200
    data = resp.json()
    assert "token" in data
    assert "expires_at" in data


@pytest.mark.asyncio
async def test_login_bad_password(client: AsyncClient, athlete):
    resp = await client.post("/auth/login", json={"email": "test@marathon.dev", "password": "wrong"})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_login_unknown_email(client: AsyncClient, athlete):
    resp = await client.post("/auth/login", json={"email": "nobody@test.dev", "password": "testpass"})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_protected_route_no_token(client: AsyncClient):
    resp = await client.get("/health")
    # health is unprotected
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_jwt_validates(client: AsyncClient, athlete, auth_headers):
    # We'll test this once plan routes exist; for now, verify token creation works
    from app.auth import create_access_token, decode_access_token

    token, _ = create_access_token(str(athlete.id))
    decoded = decode_access_token(token)
    assert decoded == str(athlete.id)


@pytest.mark.asyncio
async def test_jwt_invalid_token():
    from app.auth import decode_access_token

    assert decode_access_token("garbage.token.here") is None
```

- [ ] **Step 8: Run tests**

```bash
docker compose exec api pytest tests/test_auth.py -v
# Expected: all pass
```

- [ ] **Step 9: Commit**

```bash
git add app/auth.py app/deps.py app/schemas/ app/routes/ tests/
git commit -m "feat: JWT auth with login endpoint and tests"
```

---

## Task 5: Workout Family Mapping

**Files:**
- Create: `app/lib/__init__.py`
- Create: `app/lib/workout_family.py`
- Create: `tests/test_workout_family.py`

- [ ] **Step 1: Write failing test `tests/test_workout_family.py`**

```python
from app.lib.workout_family import family_for_garmin_activity_type, family_for_planned
from app.models.workout import WorkoutFamily, WorkoutType


def test_all_workout_types_map_to_family():
    """Every WorkoutType must map to a family."""
    for wt in WorkoutType:
        result = family_for_planned(wt)
        assert isinstance(result, WorkoutFamily), f"{wt} did not return a WorkoutFamily"


def test_running_family():
    running_types = [
        WorkoutType.easy, WorkoutType.long, WorkoutType.tempo,
        WorkoutType.intervals, WorkoutType.hills, WorkoutType.mp_long,
        WorkoutType.recovery, WorkoutType.strides, WorkoutType.race,
    ]
    for wt in running_types:
        assert family_for_planned(wt) == WorkoutFamily.running


def test_strength_family():
    assert family_for_planned(WorkoutType.strength_a) == WorkoutFamily.strength
    assert family_for_planned(WorkoutType.strength_b) == WorkoutFamily.strength


def test_other_family():
    assert family_for_planned(WorkoutType.cross) == WorkoutFamily.other
    assert family_for_planned(WorkoutType.rest) == WorkoutFamily.other


def test_garmin_running():
    assert family_for_garmin_activity_type("running") == WorkoutFamily.running
    assert family_for_garmin_activity_type("trail_running") == WorkoutFamily.running
    assert family_for_garmin_activity_type("treadmill_running") == WorkoutFamily.running


def test_garmin_strength():
    assert family_for_garmin_activity_type("strength_training") == WorkoutFamily.strength


def test_garmin_other():
    assert family_for_garmin_activity_type("cycling") == WorkoutFamily.other
    assert family_for_garmin_activity_type("swimming") == WorkoutFamily.other
    assert family_for_garmin_activity_type("unknown_activity") == WorkoutFamily.other
```

- [ ] **Step 2: Run test to verify it fails**

```bash
docker compose exec api pytest tests/test_workout_family.py -v
# Expected: FAIL — module not found
```

- [ ] **Step 3: Implement `app/lib/__init__.py`** (empty) and `app/lib/workout_family.py`**

```python
from app.models.workout import WorkoutFamily, WorkoutType

_PLANNED_TO_FAMILY: dict[WorkoutType, WorkoutFamily] = {
    WorkoutType.easy: WorkoutFamily.running,
    WorkoutType.long: WorkoutFamily.running,
    WorkoutType.tempo: WorkoutFamily.running,
    WorkoutType.intervals: WorkoutFamily.running,
    WorkoutType.hills: WorkoutFamily.running,
    WorkoutType.mp_long: WorkoutFamily.running,
    WorkoutType.recovery: WorkoutFamily.running,
    WorkoutType.strides: WorkoutFamily.running,
    WorkoutType.race: WorkoutFamily.running,
    WorkoutType.strength_a: WorkoutFamily.strength,
    WorkoutType.strength_b: WorkoutFamily.strength,
    WorkoutType.cross: WorkoutFamily.other,
    WorkoutType.rest: WorkoutFamily.other,
}

_GARMIN_RUNNING_TYPES = {
    "running", "trail_running", "treadmill_running", "track_running",
    "indoor_running", "virtual_run",
}

_GARMIN_STRENGTH_TYPES = {"strength_training"}


def family_for_planned(workout_type: WorkoutType) -> WorkoutFamily:
    return _PLANNED_TO_FAMILY[workout_type]


def family_for_garmin_activity_type(activity_type: str) -> WorkoutFamily:
    normalized = activity_type.lower().strip()
    if normalized in _GARMIN_RUNNING_TYPES:
        return WorkoutFamily.running
    if normalized in _GARMIN_STRENGTH_TYPES:
        return WorkoutFamily.strength
    return WorkoutFamily.other
```

- [ ] **Step 4: Run tests**

```bash
docker compose exec api pytest tests/test_workout_family.py -v
# Expected: all pass
```

- [ ] **Step 5: Commit**

```bash
git add app/lib/ tests/test_workout_family.py
git commit -m "feat: workout type to family mapping with tests"
```

---

## Task 6: Plan Parser + Seed Script

**Files:**
- Create: `app/seed/__init__.py`
- Create: `app/seed/plan_parser.py`
- Create: `app/seed/load_plan.py`
- Create: `tests/test_seed.py`

- [ ] **Step 1: Write failing test `tests/test_seed.py`**

```python
import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.athlete import Athlete
from app.models.plan import Cycle, Plan
from app.models.workout import PlannedWorkout


@pytest.mark.asyncio
async def test_plan_parser_parses_plan_md():
    from app.seed.plan_parser import parse_plan

    data = parse_plan("PLAN.md")
    assert data["athlete"]["name"] != ""
    assert len(data["cycles"]) == 3
    assert data["cycles"][0]["race_name"] == "Marine Corps Marathon"
    assert data["cycles"][1]["race_name"] == "Walt Disney World Marathon"
    assert data["cycles"][2]["race_name"] == "Coastal Delaware Marathon"
    assert data["philosophy"] != ""

    total_workouts = sum(len(c["workouts"]) for c in data["cycles"])
    assert total_workouts == 364, f"Expected 364 workouts, got {total_workouts}"


@pytest.mark.asyncio
async def test_seed_creates_correct_counts(db: AsyncSession):
    from app.seed.load_plan import seed_plan

    await seed_plan(db, plan_path="PLAN.md", password="testpass")

    athlete_count = (await db.execute(select(func.count()).select_from(Athlete))).scalar()
    assert athlete_count == 1

    plan_count = (await db.execute(select(func.count()).select_from(Plan))).scalar()
    assert plan_count == 1

    cycle_count = (await db.execute(select(func.count()).select_from(Cycle))).scalar()
    assert cycle_count == 3

    workout_count = (await db.execute(select(func.count()).select_from(PlannedWorkout))).scalar()
    assert workout_count == 364


@pytest.mark.asyncio
async def test_seed_is_idempotent(db: AsyncSession):
    from app.seed.load_plan import seed_plan

    await seed_plan(db, plan_path="PLAN.md", password="testpass")
    await seed_plan(db, plan_path="PLAN.md", password="testpass")

    workout_count = (await db.execute(select(func.count()).select_from(PlannedWorkout))).scalar()
    assert workout_count == 364
```

- [ ] **Step 2: Run test to verify it fails**

```bash
docker compose exec api pytest tests/test_seed.py -v
# Expected: FAIL — module not found
```

- [ ] **Step 3: Implement `app/seed/__init__.py`** (empty) and `app/seed/plan_parser.py`**

```python
"""Parse PLAN.md into structured data for seeding."""

import re
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

# Cycle anchor dates from SESSION_1.md
CYCLE_ANCHORS = [
    {
        "name": "Phase 1: MCM",
        "race_name": "Marine Corps Marathon",
        "race_date": date(2026, 10, 25),
        "start_date": date(2026, 4, 13),
        "sequence": 1,
    },
    {
        "name": "Phase 2: Disney",
        "race_name": "Walt Disney World Marathon",
        "race_date": date(2027, 1, 10),
        "start_date": date(2026, 10, 26),
        "sequence": 2,
    },
    {
        "name": "Phase 3: Delaware",
        "race_name": "Coastal Delaware Marathon",
        "race_date": date(2027, 4, 11),
        "start_date": date(2027, 1, 11),
        "sequence": 3,
    },
]

DAY_OFFSETS = {"Mon": 0, "Tue": 1, "Wed": 2, "Thu": 3, "Fri": 4, "Sat": 5, "Sun": 6}


def parse_plan(plan_path: str) -> dict[str, Any]:
    """Parse PLAN.md and return structured data."""
    text = Path(plan_path).read_text(encoding="utf-8")

    athlete = _parse_athlete_profile(text)
    philosophy = _parse_philosophy(text)
    cycles = _parse_all_cycles(text)

    return {"athlete": athlete, "philosophy": philosophy, "cycles": cycles}


def _parse_athlete_profile(text: str) -> dict[str, Any]:
    """Extract athlete profile YAML block."""
    match = re.search(r"## Athlete Profile\s*```yaml\s*(.*?)```", text, re.DOTALL)
    if not match:
        raise ValueError("Could not find Athlete Profile YAML block in PLAN.md")

    yaml_text = match.group(1)
    profile: dict[str, Any] = {}

    name_match = re.search(r'name:\s*"([^"]*)"', yaml_text)
    profile["name"] = name_match.group(1) if name_match else "Marathon Runner"

    email_match = re.search(r'email:\s*"([^"]*)"', yaml_text)
    profile["email"] = email_match.group(1) if email_match else "runner@marathon.dev"

    # Parse hr_zones
    hr_zones = {}
    for m in re.finditer(r"(z\d+):\s*\[(\d+),\s*(\d+)\]", yaml_text):
        hr_zones[m.group(1)] = [int(m.group(2)), int(m.group(3))]
    profile["hr_zones"] = hr_zones

    # Parse pace_targets
    pace_targets = {}
    for m in re.finditer(r'(\w+):\s*"([^"]+)"', yaml_text):
        key = m.group(1)
        if key in ("name", "email"):
            continue
        pace_targets[key] = m.group(2)
    profile["pace_targets"] = pace_targets

    # Parse injury notes
    injury_match = re.search(r"injury_notes_md:\s*\|\s*\n((?:\s+.+\n)+)", yaml_text)
    profile["injury_notes"] = injury_match.group(1).strip() if injury_match else ""

    return profile


def _parse_philosophy(text: str) -> str:
    """Extract plan philosophy markdown block."""
    match = re.search(
        r"## Plan Philosophy.*?```markdown\s*(.*?)```", text, re.DOTALL
    )
    return match.group(1).strip() if match else ""


def _parse_all_cycles(text: str) -> list[dict[str, Any]]:
    """Parse workout tables for all 3 phases."""
    cycles = []

    # Find each phase's workout table (inside ``` blocks after Phase headers)
    phase_pattern = re.compile(
        r"## Phase \d+ Workout Table.*?```\s*\n(.*?)```"
        r"|# Phase \d+.*?```\s*\n(.*?)```",
        re.DOTALL,
    )

    # Simpler: split by phase headers and find code blocks
    phase_sections = re.split(r"# Phase \d+", text)[1:]  # skip preamble

    for i, section in enumerate(phase_sections):
        anchor = CYCLE_ANCHORS[i]

        # Find the workout code block
        code_match = re.search(r"```\s*\n(.*?)```", section, re.DOTALL)
        if not code_match:
            raise ValueError(f"Could not find workout table for {anchor['name']}")

        workouts = _parse_workout_table(code_match.group(1), anchor)
        end_date = anchor["race_date"]

        cycles.append({
            **anchor,
            "end_date": end_date,
            "workouts": workouts,
        })

    return cycles


def _parse_workout_table(table_text: str, anchor: dict) -> list[dict[str, Any]]:
    """Parse a workout table block into workout dicts."""
    workouts = []
    current_week = 0

    for line in table_text.strip().split("\n"):
        line = line.strip()
        if not line:
            continue

        # Week header: "WEEK 1 — Foundation start" or "WEEK 1"
        week_match = re.match(r"WEEK\s+(\d+)", line)
        if week_match:
            current_week = int(week_match.group(1))
            continue

        # Workout line: "Mon | easy | 4 | 35 | description | intent"
        parts = [p.strip() for p in line.split("|")]
        if len(parts) < 4:
            continue

        day_str = parts[0][:3]  # "Mon", "Tue", etc.
        if day_str not in DAY_OFFSETS:
            continue

        workout_type = parts[1].strip()
        dist_str = parts[2].strip()
        dur_str = parts[3].strip()
        description = parts[4].strip() if len(parts) > 4 else ""
        intent = parts[5].strip() if len(parts) > 5 else ""

        # Calculate date
        week_offset = (current_week - 1) * 7
        day_offset = DAY_OFFSETS[day_str]
        workout_date = anchor["start_date"] + timedelta(days=week_offset + day_offset)

        # Parse distance
        distance: Decimal | None = None
        if dist_str:
            try:
                distance = Decimal(dist_str)
            except InvalidOperation:
                distance = None

        # Parse duration
        duration: int | None = None
        if dur_str:
            try:
                duration = int(dur_str)
            except ValueError:
                duration = None

        # Build title
        title = _build_title(workout_type, distance, description)

        workouts.append({
            "week_number": current_week,
            "day": day_str,
            "type": workout_type,
            "date": workout_date,
            "distance_mi": distance,
            "duration_min": duration,
            "title": title,
            "description_md": description,
            "intent_md": intent,
        })

    return workouts


def _build_title(workout_type: str, distance: Decimal | None, description: str) -> str:
    """Build a human-readable title for a workout."""
    type_labels = {
        "easy": "Easy Run",
        "long": "Long Run",
        "tempo": "Tempo Run",
        "intervals": "Intervals",
        "hills": "Hill Repeats",
        "mp_long": "Marathon Pace",
        "recovery": "Recovery Run",
        "strides": "Strides",
        "strength_a": "Strength A",
        "strength_b": "Strength B",
        "cross": "Cross-Training",
        "rest": "Rest Day",
        "race": "Race Day",
    }
    label = type_labels.get(workout_type, workout_type.replace("_", " ").title())
    if distance:
        return f"{label} - {distance}mi"
    return label
```

- [ ] **Step 4: Implement `app/seed/load_plan.py`**

```python
"""Seed the database from PLAN.md. Idempotent."""

import asyncio
import sys

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import hash_password
from app.config import settings
from app.db import async_session_factory
from app.lib.workout_family import family_for_planned
from app.models.athlete import Athlete
from app.models.plan import Cycle, Plan
from app.models.workout import PlannedWorkout, WorkoutType
from app.seed.plan_parser import parse_plan


async def seed_plan(
    db: AsyncSession,
    plan_path: str = "PLAN.md",
    password: str | None = None,
) -> None:
    """Load the full training plan into the database. Idempotent."""
    data = parse_plan(plan_path)
    pw = password or settings.seed_password

    # --- Athlete (upsert by email) ---
    profile = data["athlete"]
    email = profile["email"] if profile["email"] != "[FILL IN]" else "runner@marathon.dev"
    name = profile["name"] if profile["name"] != "[FILL IN]" else "Marathon Runner"

    result = await db.execute(select(Athlete).where(Athlete.email == email))
    athlete = result.scalar_one_or_none()
    if athlete is None:
        athlete = Athlete(
            name=name,
            email=email,
            password_hash=hash_password(pw),
            hr_zones_json=profile["hr_zones"],
            pace_targets_json=profile["pace_targets"],
            injury_notes_md=profile["injury_notes"],
        )
        db.add(athlete)
        await db.flush()

    # --- Plan (upsert by athlete + name) ---
    plan_name = "Marathon Trilogy 2026-2027"
    result = await db.execute(
        select(Plan).where(Plan.athlete_id == athlete.id, Plan.name == plan_name)
    )
    plan = result.scalar_one_or_none()
    if plan is None:
        plan = Plan(
            athlete_id=athlete.id,
            name=plan_name,
            start_date=data["cycles"][0]["start_date"],
            end_date=data["cycles"][-1]["end_date"],
            philosophy_md=data["philosophy"],
            is_active=True,
        )
        db.add(plan)
        await db.flush()

    # --- Cycles + Workouts ---
    for cycle_data in data["cycles"]:
        result = await db.execute(
            select(Cycle).where(
                Cycle.plan_id == plan.id,
                Cycle.sequence == cycle_data["sequence"],
            )
        )
        cycle = result.scalar_one_or_none()
        if cycle is None:
            cycle = Cycle(
                plan_id=plan.id,
                name=cycle_data["name"],
                sequence=cycle_data["sequence"],
                race_name=cycle_data["race_name"],
                race_date=cycle_data["race_date"],
                start_date=cycle_data["start_date"],
                end_date=cycle_data["end_date"],
            )
            db.add(cycle)
            await db.flush()

        # Check if workouts already exist for this cycle
        existing = await db.execute(
            select(PlannedWorkout).where(PlannedWorkout.cycle_id == cycle.id).limit(1)
        )
        if existing.scalar_one_or_none() is not None:
            continue  # already seeded

        for w in cycle_data["workouts"]:
            wtype = WorkoutType(w["type"])
            family = family_for_planned(wtype)
            workout = PlannedWorkout(
                cycle_id=cycle.id,
                scheduled_date=w["date"],
                original_date=w["date"],
                week_number=w["week_number"],
                type=wtype,
                family=family,
                distance_mi=w["distance_mi"],
                duration_min=w["duration_min"],
                title=w["title"],
                description_md=w["description_md"],
                intent_md=w["intent_md"],
            )
            db.add(workout)

    await db.commit()

    # Print summary
    from sqlalchemy import func

    athlete_count = (await db.execute(select(func.count()).select_from(Athlete))).scalar()
    plan_count = (await db.execute(select(func.count()).select_from(Plan))).scalar()
    cycle_count = (await db.execute(select(func.count()).select_from(Cycle))).scalar()
    workout_count = (await db.execute(select(func.count()).select_from(PlannedWorkout))).scalar()
    print(
        f"Loaded {athlete_count} athlete, {plan_count} plan, "
        f"{cycle_count} cycles, {workout_count} planned workouts."
    )


async def main():
    pw = settings.seed_password
    if "--interactive" in sys.argv:
        import getpass
        pw = getpass.getpass("Seed password: ")
    async with async_session_factory() as db:
        await seed_plan(db, password=pw)


if __name__ == "__main__":
    asyncio.run(main())
```

- [ ] **Step 5: Run tests**

```bash
docker compose exec api pytest tests/test_seed.py -v
# Expected: all pass, including exact count of 364
```

- [ ] **Step 6: Run seed in Docker**

```bash
docker compose exec api python -m app.seed.load_plan
# Expected: "Loaded 1 athlete, 1 plan, 3 cycles, 364 planned workouts."
```

- [ ] **Step 7: Commit**

```bash
git add app/seed/ tests/test_seed.py
git commit -m "feat: plan parser and seed script, loads 364 workouts from PLAN.md"
```

---

## Task 7: Plan Read Endpoints

**Files:**
- Create: `app/schemas/plan.py`
- Create: `app/schemas/workout.py`
- Create: `app/routes/plan.py`
- Create: `app/routes/workouts.py`
- Create: `tests/test_plan_routes.py`

- [ ] **Step 1: Create `app/schemas/plan.py`**

```python
from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class PlannedWorkoutOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    cycle_id: UUID
    scheduled_date: date
    original_date: date
    week_number: int
    type: str
    family: str
    status: str
    duration_min: int | None
    distance_mi: Decimal | None
    target_pace: str | None
    target_hr_zone: str | None
    title: str
    description_md: str
    intent_md: str


class CycleOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    sequence: int
    race_name: str
    race_date: date
    start_date: date
    end_date: date


class CycleProgress(BaseModel):
    week: int
    total_weeks: int
    days_to_race: int


class PlanCurrentOut(BaseModel):
    plan_name: str
    plan_id: UUID
    active_cycle: CycleOut | None
    cycle_progress: CycleProgress | None


class DayWorkouts(BaseModel):
    date: date
    workouts: list[PlannedWorkoutOut]


class WeekOut(BaseModel):
    week_start: date
    days: list[DayWorkouts]


class TodayOut(BaseModel):
    date: date
    workouts: list[PlannedWorkoutOut]
    coach_brief: str | None = None
```

- [ ] **Step 2: Create `app/routes/plan.py`**

```python
from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import get_current_athlete, get_db
from app.models.athlete import Athlete
from app.models.plan import Cycle, Plan
from app.models.workout import PlannedWorkout
from app.schemas.plan import (
    CycleOut,
    CycleProgress,
    DayWorkouts,
    PlanCurrentOut,
    PlannedWorkoutOut,
    TodayOut,
    WeekOut,
)

router = APIRouter(prefix="/plan", tags=["plan"])


def _find_active_cycle(cycles: list[Cycle], today: date) -> Cycle | None:
    for c in sorted(cycles, key=lambda c: c.sequence):
        if c.start_date <= today <= c.end_date:
            return c
    # If between cycles or past all, return the latest one that started
    started = [c for c in cycles if c.start_date <= today]
    return max(started, key=lambda c: c.sequence) if started else cycles[0] if cycles else None


@router.get("/current", response_model=PlanCurrentOut)
async def plan_current(
    athlete: Athlete = Depends(get_current_athlete),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Plan).where(Plan.athlete_id == athlete.id, Plan.is_active.is_(True))
    )
    plan = result.scalar_one_or_none()
    if plan is None:
        raise HTTPException(status_code=404, detail="No active plan")

    await db.refresh(plan, ["cycles"])
    today = date.today()
    active = _find_active_cycle(plan.cycles, today)

    progress = None
    if active:
        week = max(1, ((today - active.start_date).days // 7) + 1)
        total = ((active.end_date - active.start_date).days // 7) + 1
        days_to_race = (active.race_date - today).days
        progress = CycleProgress(week=week, total_weeks=total, days_to_race=days_to_race)

    return PlanCurrentOut(
        plan_name=plan.name,
        plan_id=plan.id,
        active_cycle=CycleOut.model_validate(active) if active else None,
        cycle_progress=progress,
    )


@router.get("/today", response_model=TodayOut)
async def plan_today(
    athlete: Athlete = Depends(get_current_athlete),
    db: AsyncSession = Depends(get_db),
):
    today = date.today()
    result = await db.execute(
        select(PlannedWorkout)
        .join(Cycle)
        .join(Plan)
        .where(Plan.athlete_id == athlete.id, PlannedWorkout.scheduled_date == today)
        .order_by(PlannedWorkout.type)
    )
    workouts = result.scalars().all()
    return TodayOut(
        date=today,
        workouts=[PlannedWorkoutOut.model_validate(w) for w in workouts],
        coach_brief=None,
    )


@router.get("/week", response_model=WeekOut)
async def plan_week(
    date_param: date = Query(alias="date", default=None),
    athlete: Athlete = Depends(get_current_athlete),
    db: AsyncSession = Depends(get_db),
):
    target = date_param or date.today()
    # Monday of the week containing target
    week_start = target - timedelta(days=target.weekday())
    week_end = week_start + timedelta(days=6)

    result = await db.execute(
        select(PlannedWorkout)
        .join(Cycle)
        .join(Plan)
        .where(
            Plan.athlete_id == athlete.id,
            PlannedWorkout.scheduled_date >= week_start,
            PlannedWorkout.scheduled_date <= week_end,
        )
        .order_by(PlannedWorkout.scheduled_date, PlannedWorkout.type)
    )
    workouts = result.scalars().all()

    days = []
    for offset in range(7):
        d = week_start + timedelta(days=offset)
        day_workouts = [
            PlannedWorkoutOut.model_validate(w)
            for w in workouts
            if w.scheduled_date == d
        ]
        days.append(DayWorkouts(date=d, workouts=day_workouts))

    return WeekOut(week_start=week_start, days=days)
```

- [ ] **Step 3: Create `app/schemas/workout.py`**

```python
from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class CompletedWorkoutOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    garmin_activity_id: int
    activity_date: date
    started_at: datetime
    activity_type: str
    family: str
    duration_s: int
    distance_m: Decimal | None
    avg_hr: int | None
    max_hr: int | None
    avg_pace_s_per_km: int | None
    elevation_gain_m: Decimal | None
    calories: int | None


class ReconciliationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    planned_id: UUID | None
    completed_id: UUID | None
    match_confidence: Decimal | None
    deviation_notes_md: str
    agent_review_md: str | None
    agent_reviewed_at: datetime | None


class WorkoutDetailOut(BaseModel):
    planned: "PlannedWorkoutOut | None" = None
    completed: CompletedWorkoutOut | None = None
    reconciliation: ReconciliationOut | None = None


from app.schemas.plan import PlannedWorkoutOut  # noqa: E402

WorkoutDetailOut.model_rebuild()
```

- [ ] **Step 4: Create `app/routes/workouts.py`**

```python
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import get_current_athlete, get_db
from app.models.athlete import Athlete
from app.models.plan import Cycle, Plan
from app.models.reconciliation import Reconciliation
from app.models.workout import CompletedWorkout, PlannedWorkout
from app.schemas.plan import PlannedWorkoutOut
from app.schemas.workout import CompletedWorkoutOut, ReconciliationOut, WorkoutDetailOut

router = APIRouter(prefix="/workouts", tags=["workouts"])


@router.get("/{workout_id}", response_model=WorkoutDetailOut)
async def get_workout(
    workout_id: uuid.UUID,
    athlete: Athlete = Depends(get_current_athlete),
    db: AsyncSession = Depends(get_db),
):
    # Try planned workout first
    result = await db.execute(
        select(PlannedWorkout)
        .join(Cycle)
        .join(Plan)
        .where(PlannedWorkout.id == workout_id, Plan.athlete_id == athlete.id)
    )
    planned = result.scalar_one_or_none()
    if planned is None:
        raise HTTPException(status_code=404, detail="Workout not found")

    # Find reconciliation
    recon_result = await db.execute(
        select(Reconciliation).where(Reconciliation.planned_id == workout_id)
    )
    recon = recon_result.scalar_one_or_none()

    # Find completed via reconciliation
    completed = None
    if recon and recon.completed_id:
        comp_result = await db.execute(
            select(CompletedWorkout).where(CompletedWorkout.id == recon.completed_id)
        )
        completed = comp_result.scalar_one_or_none()

    return WorkoutDetailOut(
        planned=PlannedWorkoutOut.model_validate(planned),
        completed=CompletedWorkoutOut.model_validate(completed) if completed else None,
        reconciliation=ReconciliationOut.model_validate(recon) if recon else None,
    )
```

- [ ] **Step 5: Create `app/schemas/metrics.py`**

```python
from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class DailyMetricOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    metric_date: date
    sleep_score: int | None
    sleep_duration_s: int | None
    hrv_overnight_ms: Decimal | None
    resting_hr: int | None
    body_battery_high: int | None
    body_battery_low: int | None
    training_readiness: int | None
    training_status: str | None
```

- [ ] **Step 6: Create `app/routes/metrics.py`**

```python
from datetime import date, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import get_current_athlete, get_db
from app.models.athlete import Athlete
from app.models.metrics import DailyMetric
from app.schemas.metrics import DailyMetricOut

router = APIRouter(prefix="/metrics", tags=["metrics"])


@router.get("/recent", response_model=list[DailyMetricOut])
async def recent_metrics(
    days: int = Query(default=14, ge=1, le=90),
    athlete: Athlete = Depends(get_current_athlete),
    db: AsyncSession = Depends(get_db),
):
    since = date.today() - timedelta(days=days)
    result = await db.execute(
        select(DailyMetric)
        .where(DailyMetric.athlete_id == athlete.id, DailyMetric.metric_date >= since)
        .order_by(DailyMetric.metric_date.desc())
    )
    return [DailyMetricOut.model_validate(m) for m in result.scalars().all()]
```

- [ ] **Step 7: Wire all routers into `app/main.py`**

```python
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.routes.auth import router as auth_router
from app.routes.metrics import router as metrics_router
from app.routes.plan import router as plan_router
from app.routes.workouts import router as workouts_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


app = FastAPI(title="Marathon Coach", lifespan=lifespan)
app.include_router(auth_router)
app.include_router(plan_router)
app.include_router(workouts_router)
app.include_router(metrics_router)


@app.get("/health")
async def health():
    return {"status": "ok"}
```

- [ ] **Step 8: Write `tests/test_plan_routes.py`**

```python
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.seed.load_plan import seed_plan


@pytest.fixture
async def seeded_db(db: AsyncSession) -> AsyncSession:
    await seed_plan(db, plan_path="PLAN.md", password="testpass")
    return db


@pytest.fixture
async def seeded_client(seeded_db: AsyncSession, client: AsyncClient) -> AsyncClient:
    return client


@pytest.fixture
async def seeded_auth_headers(seeded_db: AsyncSession) -> dict[str, str]:
    from sqlalchemy import select

    from app.auth import create_access_token
    from app.models.athlete import Athlete

    result = await seeded_db.execute(select(Athlete).limit(1))
    athlete = result.scalar_one()
    token, _ = create_access_token(str(athlete.id))
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_plan_today_requires_auth(seeded_client: AsyncClient):
    resp = await seeded_client.get("/plan/today")
    assert resp.status_code == 403  # no token


@pytest.mark.asyncio
async def test_plan_today_returns_shape(
    seeded_client: AsyncClient, seeded_auth_headers: dict
):
    resp = await seeded_client.get("/plan/today", headers=seeded_auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "date" in data
    assert "workouts" in data
    assert isinstance(data["workouts"], list)
    assert data["coach_brief"] is None


@pytest.mark.asyncio
async def test_plan_week_returns_7_days(
    seeded_client: AsyncClient, seeded_auth_headers: dict
):
    resp = await seeded_client.get(
        "/plan/week?date=2026-10-19", headers=seeded_auth_headers
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["days"]) == 7
    # MCM race week — should have workouts
    total = sum(len(d["workouts"]) for d in data["days"])
    assert total == 7  # every day has a workout in the plan


@pytest.mark.asyncio
async def test_plan_current_returns_shape(
    seeded_client: AsyncClient, seeded_auth_headers: dict
):
    resp = await seeded_client.get("/plan/current", headers=seeded_auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "plan_name" in data
    assert "active_cycle" in data
```

- [ ] **Step 9: Run tests**

```bash
docker compose exec api pytest tests/test_plan_routes.py -v
# Expected: all pass
```

- [ ] **Step 10: Commit**

```bash
git add app/schemas/ app/routes/ tests/test_plan_routes.py
git commit -m "feat: plan, workout, and metrics read endpoints with tests"
```

---

## Task 8: Garmin Sync Service + Endpoints

**Files:**
- Create: `app/services/__init__.py`
- Create: `app/services/garmin_sync.py`
- Create: `app/schemas/garmin.py`
- Create: `app/routes/garmin.py`
- Create: `app/routes/admin.py`

- [ ] **Step 1: Create `app/services/__init__.py`** (empty)

- [ ] **Step 2: Create `app/services/garmin_sync.py`**

```python
"""Garmin Connect sync service. Wraps python-garminconnect (sync lib) in asyncio.to_thread."""

import asyncio
import json
import logging
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from garminconnect import Garmin, GarminConnectAuthenticationError
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.lib.workout_family import family_for_garmin_activity_type
from app.models.garmin import GarminAuthState
from app.models.metrics import DailyMetric
from app.models.workout import CompletedWorkout

logger = logging.getLogger(__name__)


class SyncReport:
    def __init__(self):
        self.synced_activities: int = 0
        self.synced_metrics: int = 0
        self.errors: list[str] = []

    def to_dict(self) -> dict[str, Any]:
        return {
            "synced_activities": self.synced_activities,
            "synced_metrics": self.synced_metrics,
            "errors": self.errors,
        }


class GarminSyncService:
    def __init__(self, db: AsyncSession, athlete_id: str):
        self.db = db
        self.athlete_id = athlete_id
        self._client: Garmin | None = None

    async def _get_client(self) -> Garmin:
        """Load or create Garmin client with stored tokens."""
        if self._client:
            return self._client

        result = await self.db.execute(
            select(GarminAuthState).where(
                GarminAuthState.athlete_id == self.athlete_id
            )
        )
        auth_state = result.scalar_one_or_none()
        if auth_state is None:
            raise RuntimeError("No Garmin auth state found. Run reauth first.")

        token_dir = Path(auth_state.token_dir_path)
        token_file = token_dir / "tokens.json"

        def _init_client() -> Garmin:
            client = Garmin()
            if token_file.exists():
                tokens = json.loads(token_file.read_text())
                client.login(tokens)
            else:
                raise GarminConnectAuthenticationError("No stored tokens. Reauth required.")
            return client

        self._client = await asyncio.to_thread(_init_client)
        return self._client

    async def reauth(self, email: str, password: str) -> None:
        """Authenticate with Garmin and store tokens."""
        result = await self.db.execute(
            select(GarminAuthState).where(
                GarminAuthState.athlete_id == self.athlete_id
            )
        )
        auth_state = result.scalar_one_or_none()

        token_dir = Path(f"./data/garmin_tokens/{self.athlete_id}")
        token_dir.mkdir(parents=True, exist_ok=True)

        def _do_auth() -> dict:
            client = Garmin(email, password)
            client.login()
            return client.garth.dumps()

        try:
            tokens = await asyncio.to_thread(_do_auth)
            (token_dir / "tokens.json").write_text(json.dumps(tokens))

            if auth_state is None:
                auth_state = GarminAuthState(
                    athlete_id=self.athlete_id,
                    token_dir_path=str(token_dir),
                    needs_reauth=False,
                )
                self.db.add(auth_state)
            else:
                auth_state.needs_reauth = False
                auth_state.last_error = None
                auth_state.last_error_at = None

            await self.db.commit()
        except Exception as e:
            logger.error(f"Garmin reauth failed: {e}")
            raise

    async def sync_activities(self, since_date: date) -> list[CompletedWorkout]:
        """Sync activities from Garmin since the given date."""
        client = await self._get_client()
        today = date.today()

        def _fetch():
            return client.get_activities_by_date(
                since_date.isoformat(), today.isoformat()
            )

        try:
            activities = await asyncio.to_thread(_fetch)
        except GarminConnectAuthenticationError as e:
            await self._mark_needs_reauth(str(e))
            return []

        new_workouts = []
        for act in activities:
            activity_id = act.get("activityId")
            if not activity_id:
                continue

            # Check if already synced
            existing = await self.db.execute(
                select(CompletedWorkout).where(
                    CompletedWorkout.garmin_activity_id == activity_id
                )
            )
            if existing.scalar_one_or_none():
                continue

            activity_type = act.get("activityType", {}).get("typeKey", "other")
            family = family_for_garmin_activity_type(activity_type)

            started = act.get("startTimeLocal", act.get("startTimeGMT", ""))
            started_dt = datetime.fromisoformat(started) if started else datetime.now(timezone.utc)

            workout = CompletedWorkout(
                athlete_id=self.athlete_id,
                garmin_activity_id=activity_id,
                activity_date=started_dt.date(),
                started_at=started_dt,
                activity_type=activity_type,
                family=family,
                duration_s=int(act.get("duration", 0)),
                distance_m=act.get("distance"),
                avg_hr=act.get("averageHR"),
                max_hr=act.get("maxHR"),
                avg_pace_s_per_km=act.get("averageSpeed"),
                elevation_gain_m=act.get("elevationGain"),
                calories=act.get("calories"),
                raw_summary_json=act,
            )
            self.db.add(workout)
            new_workouts.append(workout)

        if new_workouts:
            await self.db.flush()

        return new_workouts

    async def sync_daily_metrics(self, since_date: date) -> list[DailyMetric]:
        """Sync daily health metrics from Garmin."""
        client = await self._get_client()
        new_metrics = []

        def _fetch_stats(d: str):
            return client.get_stats_and_body(d)

        current = since_date
        today = date.today()
        while current <= today:
            ds = current.isoformat()

            # Check if already synced
            existing = await self.db.execute(
                select(DailyMetric).where(
                    DailyMetric.athlete_id == self.athlete_id,
                    DailyMetric.metric_date == current,
                )
            )
            if existing.scalar_one_or_none():
                current += timedelta(days=1)
                continue

            try:
                stats = await asyncio.to_thread(_fetch_stats, ds)
            except GarminConnectAuthenticationError as e:
                await self._mark_needs_reauth(str(e))
                return new_metrics
            except Exception as e:
                logger.warning(f"Failed to fetch metrics for {ds}: {e}")
                current += timedelta(days=1)
                continue

            if stats:
                metric = DailyMetric(
                    athlete_id=self.athlete_id,
                    metric_date=current,
                    sleep_score=stats.get("sleepScore"),
                    sleep_duration_s=stats.get("sleepDurationSeconds"),
                    resting_hr=stats.get("restingHeartRate"),
                    body_battery_high=stats.get("bodyBatteryHighestValue"),
                    body_battery_low=stats.get("bodyBatteryLowestValue"),
                    raw_json=stats,
                )
                self.db.add(metric)
                new_metrics.append(metric)

            current += timedelta(days=1)

        if new_metrics:
            await self.db.flush()

        return new_metrics

    async def sync_all(self, days_back: int = 7) -> SyncReport:
        """Full sync: activities + metrics. Returns report."""
        report = SyncReport()
        since = date.today() - timedelta(days=days_back)

        try:
            activities = await self.sync_activities(since)
            report.synced_activities = len(activities)
        except Exception as e:
            report.errors.append(f"Activity sync error: {e}")

        try:
            metrics = await self.sync_daily_metrics(since)
            report.synced_metrics = len(metrics)
        except Exception as e:
            report.errors.append(f"Metrics sync error: {e}")

        await self.db.commit()

        # Update last_successful_sync
        await self.db.execute(
            update(GarminAuthState)
            .where(GarminAuthState.athlete_id == self.athlete_id)
            .values(last_successful_sync=datetime.now(timezone.utc))
        )
        await self.db.commit()

        return report

    async def _mark_needs_reauth(self, error: str) -> None:
        await self.db.execute(
            update(GarminAuthState)
            .where(GarminAuthState.athlete_id == self.athlete_id)
            .values(
                needs_reauth=True,
                last_error=error,
                last_error_at=datetime.now(timezone.utc),
            )
        )
        await self.db.commit()
```

- [ ] **Step 3: Create `app/schemas/garmin.py`**

```python
from datetime import datetime

from pydantic import BaseModel


class GarminReauthRequest(BaseModel):
    email: str
    password: str


class GarminStatusOut(BaseModel):
    needs_reauth: bool
    last_sync: datetime | None
    last_error: str | None
    last_error_at: datetime | None


class SyncReportOut(BaseModel):
    synced_activities: int
    synced_metrics: int
    errors: list[str]
```

- [ ] **Step 4: Create `app/routes/garmin.py`**

```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import get_current_athlete, get_db
from app.models.athlete import Athlete
from app.models.garmin import GarminAuthState
from app.schemas.garmin import GarminReauthRequest, GarminStatusOut
from app.services.garmin_sync import GarminSyncService

router = APIRouter(prefix="/garmin", tags=["garmin"])


@router.post("/reauth")
async def reauth(
    body: GarminReauthRequest,
    athlete: Athlete = Depends(get_current_athlete),
    db: AsyncSession = Depends(get_db),
):
    svc = GarminSyncService(db, str(athlete.id))
    try:
        await svc.reauth(body.email, body.password)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"ok": True}


@router.get("/status", response_model=GarminStatusOut)
async def status(
    athlete: Athlete = Depends(get_current_athlete),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(GarminAuthState).where(GarminAuthState.athlete_id == athlete.id)
    )
    state = result.scalar_one_or_none()
    if state is None:
        return GarminStatusOut(
            needs_reauth=True, last_sync=None, last_error=None, last_error_at=None
        )
    return GarminStatusOut(
        needs_reauth=state.needs_reauth,
        last_sync=state.last_successful_sync,
        last_error=state.last_error,
        last_error_at=state.last_error_at,
    )
```

- [ ] **Step 5: Create `app/routes/admin.py`**

```python
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import get_current_athlete, get_db
from app.models.athlete import Athlete
from app.schemas.garmin import SyncReportOut
from app.services.garmin_sync import GarminSyncService

router = APIRouter(prefix="/admin", tags=["admin"])


@router.post("/sync", response_model=SyncReportOut)
async def trigger_sync(
    athlete: Athlete = Depends(get_current_athlete),
    db: AsyncSession = Depends(get_db),
):
    svc = GarminSyncService(db, str(athlete.id))
    report = await svc.sync_all()
    return SyncReportOut(**report.to_dict())
```

- [ ] **Step 6: Wire garmin + admin routers into `app/main.py`**

Add to `app/main.py`:

```python
from app.routes.admin import router as admin_router
from app.routes.garmin import router as garmin_router

# ... existing routers ...
app.include_router(garmin_router)
app.include_router(admin_router)
```

- [ ] **Step 7: Commit**

```bash
git add app/services/garmin_sync.py app/schemas/garmin.py app/routes/garmin.py app/routes/admin.py app/main.py app/services/__init__.py
git commit -m "feat: Garmin sync service with reauth, status, and admin sync endpoints"
```

---

## Task 9: Reconciler

**Files:**
- Create: `app/services/reconciler.py`
- Create: `tests/test_reconciler.py`

- [ ] **Step 1: Write failing test `tests/test_reconciler.py`**

```python
import uuid
from datetime import date, datetime, timezone
from decimal import Decimal

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.plan import Cycle, Plan
from app.models.reconciliation import Reconciliation
from app.models.workout import (
    CompletedWorkout,
    PlannedWorkout,
    WorkoutFamily,
    WorkoutStatus,
    WorkoutType,
)


async def _create_plan_with_workout(
    db: AsyncSession,
    athlete_id: uuid.UUID,
    workout_date: date,
    workout_type: WorkoutType = WorkoutType.easy,
    distance_mi: Decimal | None = Decimal("5.0"),
) -> PlannedWorkout:
    """Helper to create a plan -> cycle -> planned workout."""
    plan = Plan(
        athlete_id=athlete_id,
        name="Test Plan",
        start_date=date(2026, 4, 13),
        end_date=date(2027, 4, 11),
        philosophy_md="test",
    )
    db.add(plan)
    await db.flush()

    cycle = Cycle(
        plan_id=plan.id,
        name="Test Cycle",
        sequence=1,
        race_name="Test Race",
        race_date=date(2026, 10, 25),
        start_date=date(2026, 4, 13),
        end_date=date(2026, 10, 25),
    )
    db.add(cycle)
    await db.flush()

    from app.lib.workout_family import family_for_planned

    pw = PlannedWorkout(
        cycle_id=cycle.id,
        scheduled_date=workout_date,
        original_date=workout_date,
        week_number=1,
        type=workout_type,
        family=family_for_planned(workout_type),
        distance_mi=distance_mi,
        duration_min=45,
        title="Test Workout",
        description_md="Test",
        intent_md="Test intent",
    )
    db.add(pw)
    await db.flush()
    return pw


async def _create_completed(
    db: AsyncSession,
    athlete_id: uuid.UUID,
    activity_date: date,
    family: WorkoutFamily = WorkoutFamily.running,
    distance_m: Decimal | None = Decimal("8046.72"),
    garmin_id: int | None = None,
) -> CompletedWorkout:
    cw = CompletedWorkout(
        athlete_id=athlete_id,
        garmin_activity_id=garmin_id or int(uuid.uuid4().int % 10**9),
        activity_date=activity_date,
        started_at=datetime.now(timezone.utc),
        activity_type="running",
        family=family,
        duration_s=2700,
        distance_m=distance_m,
        raw_summary_json={"test": True},
    )
    db.add(cw)
    await db.flush()
    return cw


@pytest.mark.asyncio
async def test_single_match(db: AsyncSession, athlete):
    d = date(2026, 5, 1)
    pw = await _create_plan_with_workout(db, athlete.id, d)
    cw = await _create_completed(db, athlete.id, d)
    await db.commit()

    from app.services.reconciler import reconcile

    report = await reconcile(db, athlete.id)
    assert report["matched"] >= 1

    result = await db.execute(
        select(Reconciliation).where(
            Reconciliation.planned_id == pw.id,
            Reconciliation.completed_id == cw.id,
        )
    )
    recon = result.scalar_one()
    assert recon.match_confidence == Decimal("1.00")

    # Planned workout should be marked done
    await db.refresh(pw)
    assert pw.status == WorkoutStatus.done


@pytest.mark.asyncio
async def test_no_match_creates_bonus(db: AsyncSession, athlete):
    d = date(2026, 5, 1)
    cw = await _create_completed(db, athlete.id, d)
    await db.commit()

    from app.services.reconciler import reconcile

    await reconcile(db, athlete.id)

    result = await db.execute(
        select(Reconciliation).where(Reconciliation.completed_id == cw.id)
    )
    recon = result.scalar_one()
    assert recon.planned_id is None


@pytest.mark.asyncio
async def test_idempotent(db: AsyncSession, athlete):
    d = date(2026, 5, 1)
    await _create_plan_with_workout(db, athlete.id, d)
    await _create_completed(db, athlete.id, d)
    await db.commit()

    from app.services.reconciler import reconcile

    await reconcile(db, athlete.id)
    await reconcile(db, athlete.id)

    count = (
        await db.execute(select(Reconciliation).where(Reconciliation.athlete_id == athlete.id))
    ).scalars().all()
    assert len(count) == 1
```

- [ ] **Step 2: Run test to verify it fails**

```bash
docker compose exec api pytest tests/test_reconciler.py -v
# Expected: FAIL — module not found
```

- [ ] **Step 3: Implement `app/services/reconciler.py`**

```python
"""Reconciler: matches completed workouts to planned workouts by date + family."""

import logging
from datetime import date, timedelta, timezone
from decimal import Decimal
from typing import Any

from sqlalchemy import and_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.reconciliation import Reconciliation
from app.models.workout import (
    CompletedWorkout,
    PlannedWorkout,
    WorkoutFamily,
    WorkoutStatus,
)

logger = logging.getLogger(__name__)


async def reconcile(db: AsyncSession, athlete_id) -> dict[str, Any]:
    """Run reconciliation for an athlete. Returns a report dict."""
    matched = 0
    bonus = 0
    skipped = 0

    # --- Match completed workouts to planned ---
    # Find completed workouts with no reconciliation
    unmatched_completed = await db.execute(
        select(CompletedWorkout).where(
            CompletedWorkout.athlete_id == athlete_id,
            ~CompletedWorkout.id.in_(
                select(Reconciliation.completed_id).where(
                    Reconciliation.completed_id.isnot(None)
                )
            ),
        )
    )

    for cw in unmatched_completed.scalars().all():
        # Find planned workouts on the same date, same family, available
        candidates = await db.execute(
            select(PlannedWorkout).where(
                PlannedWorkout.scheduled_date == cw.activity_date,
                PlannedWorkout.family == cw.family,
                PlannedWorkout.status.in_([WorkoutStatus.planned, WorkoutStatus.moved]),
                ~PlannedWorkout.id.in_(
                    select(Reconciliation.planned_id).where(
                        Reconciliation.planned_id.isnot(None)
                    )
                ),
            )
        )
        candidates_list = candidates.scalars().all()

        if len(candidates_list) == 0:
            # Bonus / unscheduled run
            recon = Reconciliation(
                athlete_id=athlete_id,
                planned_id=None,
                completed_id=cw.id,
                match_confidence=None,
                deviation_notes_md="Unscheduled activity — no matching planned workout.",
            )
            db.add(recon)
            bonus += 1

        elif len(candidates_list) == 1:
            pw = candidates_list[0]
            recon = Reconciliation(
                athlete_id=athlete_id,
                planned_id=pw.id,
                completed_id=cw.id,
                match_confidence=Decimal("1.00"),
            )
            db.add(recon)
            pw.status = WorkoutStatus.done
            matched += 1

        else:
            # Multiple candidates — pick closest by distance
            def _distance_diff(pw: PlannedWorkout) -> float:
                if pw.distance_mi and cw.distance_m:
                    planned_m = float(pw.distance_mi) * 1609.34
                    return abs(planned_m - float(cw.distance_m))
                if pw.duration_min and cw.duration_s:
                    planned_s = pw.duration_min * 60
                    return abs(planned_s - cw.duration_s)
                return 0.0

            best = min(candidates_list, key=_distance_diff)
            recon = Reconciliation(
                athlete_id=athlete_id,
                planned_id=best.id,
                completed_id=cw.id,
                match_confidence=Decimal("0.70"),
            )
            db.add(recon)
            best.status = WorkoutStatus.done
            matched += 1

    # --- Detect skipped planned workouts ---
    # Planned workouts >24h past their scheduled date with no reconciliation
    cutoff = date.today() - timedelta(days=1)
    overdue = await db.execute(
        select(PlannedWorkout)
        .join(
            # Need to join through cycle -> plan to filter by athlete
            PlannedWorkout.cycle,
        )
        .where(
            PlannedWorkout.scheduled_date < cutoff,
            PlannedWorkout.status.in_([WorkoutStatus.planned, WorkoutStatus.moved]),
            ~PlannedWorkout.id.in_(
                select(Reconciliation.planned_id).where(
                    Reconciliation.planned_id.isnot(None)
                )
            ),
        )
    )

    for pw in overdue.scalars().all():
        recon = Reconciliation(
            athlete_id=athlete_id,
            planned_id=pw.id,
            completed_id=None,
            match_confidence=None,
            deviation_notes_md="Skipped — no matching completed activity found.",
        )
        db.add(recon)
        pw.status = WorkoutStatus.skipped
        skipped += 1

    await db.commit()

    report = {"matched": matched, "bonus": bonus, "skipped": skipped}
    logger.info(f"Reconciliation report: {report}")
    return report
```

- [ ] **Step 4: Run tests**

```bash
docker compose exec api pytest tests/test_reconciler.py -v
# Expected: all pass
```

- [ ] **Step 5: Wire reconciler into Garmin sync**

In `app/services/garmin_sync.py`, add at the end of `sync_all()`, before the last `await self.db.commit()`:

```python
from app.services.reconciler import reconcile

# ... at end of sync_all, after syncing activities and metrics:
await reconcile(self.db, self.athlete_id)
```

- [ ] **Step 6: Commit**

```bash
git add app/services/reconciler.py tests/test_reconciler.py app/services/garmin_sync.py
git commit -m "feat: reconciler matches completed workouts to plan, with tests"
```

---

## Task 10: Agent + Chat Stubs

**Files:**
- Create: `app/services/agent_context.py`
- Create: `app/services/agents/__init__.py`
- Create: `app/services/agents/daily_coach.py`
- Create: `app/services/agents/plan_adapter.py`
- Create: `app/services/agents/run_analyst.py`
- Create: `app/routes/chat.py`

- [ ] **Step 1: Create stubs**

`app/services/agent_context.py`:
```python
import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession


async def build_athlete_context(db: AsyncSession, athlete_id: uuid.UUID) -> dict[str, Any]:
    """Build the shared context dict used by all agents. Wired in session 3."""
    raise NotImplementedError("Wired in session 3")
```

`app/services/agents/__init__.py`: (empty)

`app/services/agents/daily_coach.py`:
```python
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.agent import AgentMessage


async def generate_daily_brief(db: AsyncSession, athlete_id: uuid.UUID) -> AgentMessage:
    """Generate morning coaching brief. Wired in session 3."""
    raise NotImplementedError("Wired in session 3")
```

`app/services/agents/plan_adapter.py`:
```python
import uuid
from datetime import date
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession


async def propose_rebalance(
    db: AsyncSession, athlete_id: uuid.UUID, workout_id: uuid.UUID, new_date: date
) -> dict[str, Any]:
    """Propose rebalance options when a workout is moved. Wired in session 2."""
    raise NotImplementedError("Wired in session 2")
```

`app/services/agents/run_analyst.py`:
```python
import uuid

from sqlalchemy.ext.asyncio import AsyncSession


async def review_reconciliation(db: AsyncSession, reconciliation_id: uuid.UUID) -> str:
    """Review a reconciled workout pair. Wired in session 3."""
    raise NotImplementedError("Wired in session 3")
```

- [ ] **Step 2: Create `app/routes/chat.py`**

```python
from fastapi import APIRouter
from starlette.responses import JSONResponse

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("")
async def post_chat():
    return JSONResponse(status_code=501, content={"detail": "Chat not implemented — session 3"})


@router.get("")
async def get_chat():
    return JSONResponse(status_code=501, content={"detail": "Chat not implemented — session 3"})
```

- [ ] **Step 3: Wire chat router + coach endpoint stub into `app/main.py`**

Add:
```python
from app.routes.chat import router as chat_router
app.include_router(chat_router)
```

- [ ] **Step 4: Commit**

```bash
git add app/services/agent_context.py app/services/agents/ app/routes/chat.py app/main.py
git commit -m "feat: agent and chat stubs for sessions 2-3"
```

---

## Task 11: Full Test Suite + Lint Pass

**Files:**
- Modify: All test files
- Run: ruff check + format

- [ ] **Step 1: Run full test suite**

```bash
docker compose exec api pytest -v
# Expected: all tests pass
```

- [ ] **Step 2: Run ruff check**

```bash
docker compose exec api ruff check app/ tests/
# Fix any issues found
```

- [ ] **Step 3: Run ruff format**

```bash
docker compose exec api ruff format app/ tests/
docker compose exec api ruff format --check app/ tests/
# Expected: already formatted
```

- [ ] **Step 4: End-to-end smoke test**

```bash
# Seed the plan
docker compose exec api python -m app.seed.load_plan

# Login
TOKEN=$(curl -s -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"runner@marathon.dev","password":"marathon"}' | python -c "import sys,json; print(json.load(sys.stdin)['token'])")

# Plan today
curl -s -H "Authorization: Bearer $TOKEN" http://localhost:8000/plan/today | python -m json.tool

# Plan week (MCM race week)
curl -s -H "Authorization: Bearer $TOKEN" "http://localhost:8000/plan/week?date=2026-10-19" | python -m json.tool

# Plan current
curl -s -H "Authorization: Bearer $TOKEN" http://localhost:8000/plan/current | python -m json.tool

# Chat stub
curl -s -X POST http://localhost:8000/chat -H "Authorization: Bearer $TOKEN" | python -m json.tool
# Expected: 501
```

- [ ] **Step 5: Commit final state**

```bash
git add -A
git commit -m "chore: full test suite passes, ruff clean, smoke tests verified"
```

---

## Done Criteria Verification

After completing all tasks, verify every item from the session brief:

- [ ] `docker compose up` brings up healthy postgres + api
- [ ] `alembic upgrade head` succeeds
- [ ] `alembic check` shows no schema drift
- [ ] `python -m app.seed.load_plan` loads 1 athlete, 1 plan, 3 cycles, 364 workouts
- [ ] Re-running seed doesn't duplicate (still 364)
- [ ] `POST /auth/login` returns JWT
- [ ] `GET /plan/today` returns today's workouts (with auth)
- [ ] `GET /plan/week?date=2026-10-19` returns 7 days
- [ ] `GET /plan/current` returns active cycle
- [ ] `GET /workouts/{id}` returns planned + completed + reconciliation
- [ ] Agent stubs exist with correct signatures
- [ ] `/chat` returns 501
- [ ] `pytest` all green
- [ ] `ruff check` clean
- [ ] `ruff format --check` clean
