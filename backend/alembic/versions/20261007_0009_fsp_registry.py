"""Add candidate-owned FSP links and synthetic achievement snapshots."""

import sqlalchemy as sa

from alembic import op

revision = "20261007_0009"
down_revision = "20261007_0008"
branch_labels = None
depends_on = None


def _timestamp(name: str = "created_at") -> sa.Column:
    return sa.Column(
        name,
        sa.DateTime(timezone=True),
        server_default=sa.text("CURRENT_TIMESTAMP"),
        nullable=False,
    )


def upgrade() -> None:
    op.create_table(
        "fsp_link",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("candidate_profile_id", sa.String(36), nullable=False, unique=True),
        sa.Column("provider", sa.String(40), nullable=False),
        sa.Column("participant_id", sa.String(120), nullable=False),
        _timestamp("linked_at"),
        _timestamp("updated_at"),
        sa.ForeignKeyConstraint(["candidate_profile_id"], ["candidate_profile.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("provider", "participant_id", name="uq_fsp_link_provider_participant"),
    )
    op.create_table(
        "fsp_achievement",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("fsp_link_id", sa.String(36), nullable=False),
        sa.Column("external_achievement_id", sa.String(120), nullable=False),
        sa.Column("event_name", sa.String(200), nullable=False),
        sa.Column("event_date", sa.Date(), nullable=False),
        sa.Column("discipline", sa.String(120), nullable=False),
        sa.Column("level", sa.String(80), nullable=False),
        sa.Column("achievement_type", sa.String(80), nullable=False),
        sa.Column("placement", sa.String(80), nullable=True),
        sa.Column("result", sa.String(240), nullable=True),
        sa.Column("verification", sa.String(120), nullable=False),
        sa.Column("mapping_version", sa.String(40), nullable=False),
        _timestamp(),
        sa.ForeignKeyConstraint(["fsp_link_id"], ["fsp_link.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("fsp_link_id", "external_achievement_id", name="uq_fsp_achievement_link_external"),
    )
    op.create_index(
        "ix_fsp_achievement_link_date",
        "fsp_achievement",
        ["fsp_link_id", "event_date"],
    )


def downgrade() -> None:
    op.drop_index("ix_fsp_achievement_link_date", table_name="fsp_achievement")
    op.drop_table("fsp_achievement")
    op.drop_table("fsp_link")
