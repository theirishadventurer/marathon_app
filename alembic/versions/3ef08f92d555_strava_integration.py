"""strava integration

Revision ID: 3ef08f92d555
Revises: 0c4898e874d4
Create Date: 2026-06-17 00:12:32.555356

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '3ef08f92d555'
down_revision: Union[str, None] = '0c4898e874d4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "strava_auth_state",
        sa.Column("athlete_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("access_token", sa.Text(), nullable=False),
        sa.Column("refresh_token", sa.Text(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("athlete_strava_id", sa.BigInteger(), nullable=True),
        sa.Column("scope", sa.Text(), nullable=True),
        sa.Column("last_successful_sync", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("last_error_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["athlete_id"], ["athletes.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("athlete_id"),
    )

    op.add_column("completed_workouts", sa.Column("strava_activity_id", sa.BigInteger(), nullable=True))
    op.create_unique_constraint(
        "uq_completed_strava_activity_id", "completed_workouts", ["strava_activity_id"]
    )
    op.add_column(
        "completed_workouts",
        sa.Column("source", sa.Text(), nullable=False, server_default="manual"),
    )
    op.add_column("completed_workouts", sa.Column("avg_cadence", sa.Numeric(5, 1), nullable=True))
    op.add_column("completed_workouts", sa.Column("avg_watts", sa.Numeric(6, 1), nullable=True))
    op.add_column("completed_workouts", sa.Column("relative_effort", sa.SmallInteger(), nullable=True))

    op.execute(
        "UPDATE completed_workouts SET source = 'garmin' WHERE garmin_activity_id IS NOT NULL"
    )


def downgrade() -> None:
    op.drop_column("completed_workouts", "relative_effort")
    op.drop_column("completed_workouts", "avg_watts")
    op.drop_column("completed_workouts", "avg_cadence")
    op.drop_column("completed_workouts", "source")
    op.drop_constraint("uq_completed_strava_activity_id", "completed_workouts", type_="unique")
    op.drop_column("completed_workouts", "strava_activity_id")
    op.drop_table("strava_auth_state")
