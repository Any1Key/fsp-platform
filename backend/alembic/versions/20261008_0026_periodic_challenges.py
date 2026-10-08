"""Add recurring, match-bound employer challenge cycles."""

import sqlalchemy as sa

from alembic import op

revision = "20261008_0026"
down_revision = "20261008_0025"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "challenge",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("company_id", sa.String(36), nullable=False),
        sa.Column("match_id", sa.String(36), nullable=False),
        sa.Column("created_by_identity_id", sa.String(36), nullable=False),
        sa.Column("title", sa.String(160), nullable=False),
        sa.Column("instructions", sa.Text(), nullable=False),
        sa.Column("target_skill", sa.String(80), nullable=False),
        sa.Column("estimated_minutes", sa.Integer(), nullable=False),
        sa.Column("cadence_days", sa.Integer(), nullable=False),
        sa.Column("rubric", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(16), nullable=False, server_default="active"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["company_id"], ["company.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["match_id"], ["talent_match.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by_identity_id"], ["user_identity.id"], ondelete="CASCADE"),
        sa.CheckConstraint("estimated_minutes BETWEEN 5 AND 20", name="ck_challenge_duration"),
        sa.CheckConstraint("cadence_days BETWEEN 1 AND 90", name="ck_challenge_cadence"),
        sa.CheckConstraint("status IN ('active', 'paused')", name="ck_challenge_status"),
    )
    op.create_index("ix_challenge_company_status", "challenge", ["company_id", "status"])
    op.create_index("ix_challenge_match", "challenge", ["match_id"])

    op.create_table(
        "challenge_assignment",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("challenge_id", sa.String(36), nullable=False),
        sa.Column("cycle_number", sa.Integer(), nullable=False),
        sa.Column("assigned_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(16), nullable=False, server_default="assigned"),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["challenge_id"], ["challenge.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("challenge_id", "cycle_number", name="uq_challenge_cycle"),
        sa.CheckConstraint("cycle_number > 0", name="ck_challenge_cycle_positive"),
        sa.CheckConstraint("status IN ('assigned', 'submitted', 'graded', 'expired')", name="ck_challenge_assignment_status"),
    )
    op.create_index("ix_challenge_assignment_due", "challenge_assignment", ["challenge_id", "due_at"])

    op.create_table(
        "challenge_submission",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("assignment_id", sa.String(36), nullable=False, unique=True),
        sa.Column("response_text", sa.Text(), nullable=False),
        sa.Column("submitted_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["assignment_id"], ["challenge_assignment.id"], ondelete="CASCADE"),
    )

    op.create_table(
        "challenge_result",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("assignment_id", sa.String(36), nullable=False, unique=True),
        sa.Column("employer_identity_id", sa.String(36), nullable=False),
        sa.Column("score", sa.Integer(), nullable=False),
        sa.Column("rubric_scores", sa.JSON(), nullable=False),
        sa.Column("feedback", sa.Text(), nullable=True),
        sa.Column("status", sa.String(16), nullable=False, server_default="draft"),
        sa.Column("evidence_fresh_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("released_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["assignment_id"], ["challenge_assignment.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["employer_identity_id"], ["user_identity.id"], ondelete="CASCADE"),
        sa.CheckConstraint("score BETWEEN 0 AND 100", name="ck_challenge_result_score"),
        sa.CheckConstraint("status IN ('draft', 'released')", name="ck_challenge_result_status"),
    )
    op.create_index("ix_challenge_result_freshness", "challenge_result", ["evidence_fresh_until"])


def downgrade() -> None:
    op.drop_index("ix_challenge_result_freshness", table_name="challenge_result")
    op.drop_table("challenge_result")
    op.drop_table("challenge_submission")
    op.drop_index("ix_challenge_assignment_due", table_name="challenge_assignment")
    op.drop_table("challenge_assignment")
    op.drop_index("ix_challenge_match", table_name="challenge")
    op.drop_index("ix_challenge_company_status", table_name="challenge")
    op.drop_table("challenge")
