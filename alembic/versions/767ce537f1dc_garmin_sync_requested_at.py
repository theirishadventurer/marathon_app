"""garmin sync_requested_at

Revision ID: 767ce537f1dc
Revises: 3ef08f92d555
Create Date: 2026-06-18 09:22:53.393056

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '767ce537f1dc'
down_revision: Union[str, None] = '3ef08f92d555'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "garmin_auth_state",
        sa.Column("sync_requested_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("garmin_auth_state", "sync_requested_at")
