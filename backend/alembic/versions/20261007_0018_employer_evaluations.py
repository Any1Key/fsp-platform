"""Add employer-owned evaluation evidence for matched task assignments."""

import sqlalchemy as sa

from alembic import op

revision = "20261007_0018"
down_revision = "20261007_0017"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "employer_evaluation",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("assignment_id", sa.String(36), nullable=False, unique=True),
        sa.Column("employer_identity_id", sa.String(36), nullable=False),
        sa.Column("score", sa.Integer(), nullable=False),
        sa.Column("rubric_scores", sa.JSON(), nullable=False),
        sa.Column("feedback", sa.Text(), nullable=True),
        sa.Column("status", sa.String(16), nullable=False, server_default="draft"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column("released_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["assignment_id"], ["task_assignment.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["employer_identity_id"], ["user_identity.id"], ondelete="RESTRICT"
        ),
        sa.CheckConstraint("score BETWEEN 0 AND 100", name="ck_employer_evaluation_score"),
        sa.CheckConstraint(
            "status IN ('draft', 'released')",
            name="ck_employer_evaluation_status",
        ),
        sa.CheckConstraint(
            "(status = 'released' AND released_at IS NOT NULL) OR "
            "(status = 'draft' AND released_at IS NULL)",
            name="ck_employer_evaluation_release_consistency",
        ),
    )
    op.create_index(
        "ix_employer_evaluation_employer_status",
        "employer_evaluation",
        ["employer_identity_id", "status", "updated_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_employer_evaluation_employer_status", table_name="employer_evaluation"
    )
    op.drop_table("employer_evaluation")
