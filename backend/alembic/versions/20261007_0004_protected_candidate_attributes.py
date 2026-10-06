"""Add private candidate date-of-birth storage.

Revision ID: 20261007_0004
Revises: 20261007_0003
Create Date: 2026-10-07
"""

import sqlalchemy as sa

from alembic import op

revision = "20261007_0004"
down_revision = "20261007_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("candidate_profile", sa.Column("date_of_birth", sa.Date(), nullable=True))


def downgrade() -> None:
    op.drop_column("candidate_profile", "date_of_birth")
