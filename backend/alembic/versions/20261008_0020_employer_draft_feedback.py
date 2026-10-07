"""Persist employer review decisions for optional local-AI task drafts."""

import sqlalchemy as sa

from alembic import op

revision = "20261008_0020"
down_revision = "20261007_0019"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "employer_task_draft_feedback",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("company_id", sa.String(36), nullable=False),
        sa.Column("hiring_need_id", sa.String(36), nullable=False),
        sa.Column("decision", sa.String(16), nullable=False),
        sa.Column("reviewed_draft", sa.JSON(), nullable=True),
        sa.Column("feedback_note", sa.String(1000), nullable=True),
        sa.Column("need_snapshot", sa.JSON(), nullable=False),
        sa.Column("created_by_identity_id", sa.String(36), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["company_id"], ["company.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["hiring_need_id"], ["hiring_need.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["created_by_identity_id"], ["user_identity.id"], ondelete="RESTRICT"
        ),
        sa.CheckConstraint(
            "decision IN ('approved', 'edited', 'rejected')",
            name="ck_employer_task_draft_feedback_decision",
        ),
        sa.CheckConstraint(
            "(decision = 'rejected' AND reviewed_draft IS NULL) OR "
            "(decision IN ('approved', 'edited') AND reviewed_draft IS NOT NULL)",
            name="ck_employer_task_draft_feedback_draft_consistency",
        ),
    )
    op.create_index(
        "ix_employer_task_draft_feedback_company_need_created",
        "employer_task_draft_feedback",
        ["company_id", "hiring_need_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_employer_task_draft_feedback_company_need_created",
        table_name="employer_task_draft_feedback",
    )
    op.drop_table("employer_task_draft_feedback")
