"""create_rate_limits_table

Revision ID: e6f7a8b9c0d1
Revises: d5e6f7a8b9c0
Create Date: 2026-08-15 16:15:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e6f7a8b9c0d1"
down_revision: Union[str, Sequence[str], None] = "d5e6f7a8b9c0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "rate_limits",
        sa.Column("subject_hash", sa.String(length=64), nullable=False),
        sa.Column("endpoint", sa.String(length=50), nullable=False),
        sa.Column("window_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("count", sa.Integer(), nullable=False, server_default="1"),
        sa.PrimaryKeyConstraint("subject_hash", "endpoint", "window_start", name="pk_rate_limits"),
    )
    op.create_index("idx_rate_limits_window", "rate_limits", ["window_start"], unique=False)


def downgrade() -> None:
    op.drop_index("idx_rate_limits_window", table_name="rate_limits")
    op.drop_table("rate_limits")
