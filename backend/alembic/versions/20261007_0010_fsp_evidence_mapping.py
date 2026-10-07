"""Persist normalized canonical fields for FSP evidence snapshots."""

import sqlalchemy as sa

from alembic import op

revision = "20261007_0010"
down_revision = "20261007_0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("fsp_achievement", sa.Column("canonical_specialization_slug", sa.String(100), nullable=True))
    op.add_column(
        "fsp_achievement",
        sa.Column("canonical_skill_slugs", sa.String(600), nullable=False, server_default="[]"),
    )
    op.add_column("fsp_achievement", sa.Column("result_score", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("fsp_achievement", sa.Column("result_label", sa.String(40), nullable=False, server_default="recorded"))


def downgrade() -> None:
    op.drop_column("fsp_achievement", "result_label")
    op.drop_column("fsp_achievement", "result_score")
    op.drop_column("fsp_achievement", "canonical_skill_slugs")
    op.drop_column("fsp_achievement", "canonical_specialization_slug")
