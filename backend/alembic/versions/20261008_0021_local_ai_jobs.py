"""Persist queued optional local-AI task-draft jobs."""

import sqlalchemy as sa

from alembic import op

revision = "20261008_0021"
down_revision = "20261008_0020"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "employer_task_draft_job",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("company_id", sa.String(36), nullable=False),
        sa.Column("hiring_need_id", sa.String(36), nullable=False),
        sa.Column("created_by_identity_id", sa.String(36), nullable=False),
        sa.Column("status", sa.String(16), nullable=False, server_default="queued"),
        sa.Column("context_snapshot", sa.JSON(), nullable=False),
        sa.Column("result", sa.JSON(), nullable=True),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["company_id"], ["company.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["hiring_need_id"], ["hiring_need.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["created_by_identity_id"], ["user_identity.id"], ondelete="RESTRICT"
        ),
        sa.CheckConstraint(
            "status IN ('queued', 'running', 'completed', 'failed')",
            name="ck_employer_task_draft_job_status",
        ),
        sa.CheckConstraint("attempts >= 0", name="ck_employer_task_draft_job_attempts"),
    )
    op.create_index(
        "ix_employer_task_draft_job_company_status_created",
        "employer_task_draft_job",
        ["company_id", "status", "created_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_employer_task_draft_job_company_status_created",
        table_name="employer_task_draft_job",
    )
    op.drop_table("employer_task_draft_job")
