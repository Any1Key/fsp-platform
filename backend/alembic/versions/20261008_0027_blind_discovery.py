"""Persist whether a reverse-recruitment invitation was sent in blind mode."""

import sqlalchemy as sa

from alembic import op

revision = "20261008_0027"
down_revision = "20261008_0026"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "invitation",
        sa.Column("blind_discovery", sa.Boolean(), nullable=False, server_default=sa.false()),
    )


def downgrade() -> None:
    op.drop_column("invitation", "blind_discovery")
