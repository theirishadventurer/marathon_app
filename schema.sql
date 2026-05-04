-- Marathon Coach — PostgreSQL schema
-- Canonical reference. SQLAlchemy models in app/models/ must match this.
-- Alembic migrations are generated FROM the models, so keep models == this file.

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- =============================================================
-- ATHLETES
-- =============================================================
CREATE TABLE athletes (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name            TEXT NOT NULL,
    email           TEXT UNIQUE NOT NULL,
    password_hash   TEXT NOT NULL,
    hr_zones_json       JSONB,
    pace_targets_json   JSONB,
    injury_notes_md     TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- =============================================================
-- PLANS  (the whole 12-month program)
-- =============================================================
CREATE TABLE plans (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    athlete_id      UUID NOT NULL REFERENCES athletes(id) ON DELETE CASCADE,
    name            TEXT NOT NULL,
    start_date      DATE NOT NULL,
    end_date        DATE NOT NULL,
    philosophy_md   TEXT NOT NULL DEFAULT '',
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX plans_athlete_active_idx
    ON plans(athlete_id) WHERE is_active = TRUE;

-- =============================================================
-- CYCLES  (each marathon block within a plan)
-- =============================================================
CREATE TABLE cycles (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    plan_id             UUID NOT NULL REFERENCES plans(id) ON DELETE CASCADE,
    name                TEXT NOT NULL,           -- "Phase 1: MCM"
    sequence            SMALLINT NOT NULL,       -- 1, 2, 3
    race_name           TEXT NOT NULL,
    race_date           DATE NOT NULL,
    start_date          DATE NOT NULL,
    end_date            DATE NOT NULL,
    peak_week_target    SMALLINT,
    notes_md            TEXT NOT NULL DEFAULT ''
);

CREATE INDEX cycles_plan_idx ON cycles(plan_id, sequence);

-- =============================================================
-- ENUMS
-- =============================================================
CREATE TYPE workout_type AS ENUM (
    'easy', 'long', 'tempo', 'intervals', 'hills', 'mp_long',
    'recovery', 'strides', 'strength_a', 'strength_b',
    'cross', 'rest', 'race'
);

-- Used for reconciler matching. Stored as a derived column for index speed.
CREATE TYPE workout_family AS ENUM ('running', 'strength', 'other');

CREATE TYPE workout_status AS ENUM (
    'planned', 'moved', 'skipped', 'done'
);

-- =============================================================
-- PLANNED_WORKOUTS  (the program — source of truth)
-- =============================================================
CREATE TABLE planned_workouts (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    cycle_id            UUID NOT NULL REFERENCES cycles(id) ON DELETE CASCADE,

    scheduled_date      DATE NOT NULL,
    original_date       DATE NOT NULL,
    week_number         SMALLINT NOT NULL,
    type                workout_type NOT NULL,
    family              workout_family NOT NULL,   -- derived from type, denormalized for reconciler
    status              workout_status NOT NULL DEFAULT 'planned',

    duration_min        SMALLINT,
    distance_mi         NUMERIC(4,1),
    target_pace         TEXT,
    target_hr_zone      TEXT,

    title               TEXT NOT NULL,
    description_md      TEXT NOT NULL,
    intent_md           TEXT NOT NULL DEFAULT '',

    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX planned_workouts_cycle_idx ON planned_workouts(cycle_id, scheduled_date);
CREATE INDEX planned_workouts_date_idx ON planned_workouts(scheduled_date);
CREATE INDEX planned_workouts_recon_idx
    ON planned_workouts(scheduled_date, family) WHERE status IN ('planned', 'moved');

-- =============================================================
-- COMPLETED_WORKOUTS  (what Garmin saw)
-- =============================================================
CREATE TABLE completed_workouts (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    athlete_id          UUID NOT NULL REFERENCES athletes(id) ON DELETE CASCADE,

    garmin_activity_id  BIGINT UNIQUE NOT NULL,
    activity_date       DATE NOT NULL,
    started_at          TIMESTAMPTZ NOT NULL,
    activity_type       TEXT NOT NULL,           -- raw Garmin string: "running", "strength_training", etc.
    family              workout_family NOT NULL, -- derived; for reconciler

    duration_s          INTEGER NOT NULL,
    distance_m          NUMERIC(8,2),
    avg_hr              SMALLINT,
    max_hr              SMALLINT,
    avg_pace_s_per_km   SMALLINT,
    elevation_gain_m    NUMERIC(6,1),
    calories            SMALLINT,

    fit_file_path       TEXT,
    raw_summary_json    JSONB NOT NULL,
    synced_at           TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX completed_workouts_date_idx ON completed_workouts(athlete_id, activity_date DESC);
CREATE INDEX completed_workouts_recon_idx ON completed_workouts(activity_date, family);

-- =============================================================
-- RECONCILIATIONS
-- =============================================================
CREATE TABLE reconciliations (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    athlete_id          UUID NOT NULL REFERENCES athletes(id) ON DELETE CASCADE,
    planned_id          UUID REFERENCES planned_workouts(id) ON DELETE SET NULL,
    completed_id        UUID REFERENCES completed_workouts(id) ON DELETE SET NULL,
    match_confidence    NUMERIC(3,2),
    deviation_notes_md  TEXT NOT NULL DEFAULT '',
    agent_review_md     TEXT,
    agent_reviewed_at   TIMESTAMPTZ,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT recon_at_least_one CHECK (
        planned_id IS NOT NULL OR completed_id IS NOT NULL
    )
);

CREATE UNIQUE INDEX reconciliations_planned_unique
    ON reconciliations(planned_id) WHERE planned_id IS NOT NULL;
CREATE UNIQUE INDEX reconciliations_completed_unique
    ON reconciliations(completed_id) WHERE completed_id IS NOT NULL;

-- =============================================================
-- DAILY_METRICS
-- =============================================================
CREATE TABLE daily_metrics (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    athlete_id          UUID NOT NULL REFERENCES athletes(id) ON DELETE CASCADE,
    metric_date         DATE NOT NULL,
    sleep_score         SMALLINT,
    sleep_duration_s    INTEGER,
    hrv_overnight_ms    NUMERIC(5,1),
    resting_hr          SMALLINT,
    body_battery_high   SMALLINT,
    body_battery_low    SMALLINT,
    training_readiness  SMALLINT,
    training_status     TEXT,
    raw_json            JSONB NOT NULL,
    synced_at           TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (athlete_id, metric_date)
);

CREATE INDEX daily_metrics_date_idx ON daily_metrics(athlete_id, metric_date DESC);

-- =============================================================
-- AGENT_MESSAGES
-- =============================================================
CREATE TYPE agent_kind AS ENUM (
    'daily_coach', 'plan_adapter', 'run_analyst', 'user_chat'
);

CREATE TYPE message_role AS ENUM ('system', 'user', 'assistant');

CREATE TABLE agent_messages (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    athlete_id          UUID NOT NULL REFERENCES athletes(id) ON DELETE CASCADE,
    agent               agent_kind NOT NULL,
    role                message_role NOT NULL,
    content_md          TEXT NOT NULL,
    context_snapshot_json   JSONB,
    related_workout_id      UUID REFERENCES planned_workouts(id) ON DELETE SET NULL,
    related_reconciliation_id UUID REFERENCES reconciliations(id) ON DELETE SET NULL,
    proposal_state_json     JSONB,    -- Plan Adapter: lives until applied/discarded
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX agent_messages_athlete_agent_idx
    ON agent_messages(athlete_id, agent, created_at DESC);
CREATE INDEX agent_messages_chat_idx
    ON agent_messages(athlete_id, created_at DESC)
    WHERE agent = 'user_chat';

-- =============================================================
-- GARMIN_AUTH_STATE
-- =============================================================
CREATE TABLE garmin_auth_state (
    athlete_id              UUID PRIMARY KEY REFERENCES athletes(id) ON DELETE CASCADE,
    token_dir_path          TEXT NOT NULL,
    last_successful_sync    TIMESTAMPTZ,
    last_error              TEXT,
    last_error_at           TIMESTAMPTZ,
    needs_reauth            BOOLEAN NOT NULL DEFAULT FALSE
);
