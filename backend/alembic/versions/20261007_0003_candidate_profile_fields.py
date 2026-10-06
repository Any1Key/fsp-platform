"""Add fields used by the manual candidate profile editor.

Revision ID: 20261007_0003
Revises: 20261006_0002
Create Date: 2026-10-07
"""

import sqlalchemy as sa

from alembic import op

revision = "20261007_0003"
down_revision = "20261006_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("candidate_profile", sa.Column("display_name", sa.String(120), nullable=True))
    op.add_column("candidate_profile", sa.Column("headline", sa.String(160), nullable=True))
    op.add_column("candidate_profile", sa.Column("location", sa.String(120), nullable=True))


def downgrade() -> None:
    op.drop_column("candidate_profile", "location")
    op.drop_column("candidate_profile", "headline")
    op.drop_column("candidate_profile", "display_name")
