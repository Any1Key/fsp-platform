"""Make application status history order deterministic."""

import sqlalchemy as sa

from alembic import op

revision = "20261008_0025"
down_revision = "20261008_0024"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "application_status_history",
        sa.Column("sequence", sa.Integer(), nullable=False, server_default="1"),
    )


def downgrade() -> None:
    op.drop_column("application_status_history", "sequence")
