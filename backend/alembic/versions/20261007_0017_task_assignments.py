"""Add match-bound employer task assignments and candidate submissions."""

import sqlalchemy as sa

from alembic import op

revision = "20261007_0017"
down_revision = "20261007_0016"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "task_assignment",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("match_id", sa.String(36), nullable=False),
        sa.Column("candidate_profile_id", sa.String(36), nullable=False),
        sa.Column("task_id", sa.String(36), nullable=False),
        sa.Column("task_version_id", sa.String(36), nullable=False),
        sa.Column("pipeline_stage_id", sa.String(36), nullable=False),
        sa.Column("status", sa.String(16), nullable=False, server_default="assigned"),
        sa.Column(
            "assigned_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["match_id"], ["talent_match.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["candidate_profile_id"], ["candidate_profile.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["task_id"], ["employer_task.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["task_version_id"], ["employer_task_version.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["pipeline_stage_id"], ["pipeline_stage.id"], ondelete="RESTRICT"
        ),
        sa.UniqueConstraint("match_id", "task_id", name="uq_task_assignment_match_task"),
        sa.CheckConstraint(
            "status IN ('assigned', 'submitted', 'expired')",
            name="ck_task_assignment_status",
        ),
    )
    op.create_index(
        "ix_task_assignment_candidate_status",
        "task_assignment",
        ["candidate_profile_id", "status", "due_at"],
    )
    op.create_index(
        "ix_task_assignment_match",
        "task_assignment",
        ["match_id", "task_id"],
    )

    op.create_table(
        "task_submission",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("assignment_id", sa.String(36), nullable=False),
        sa.Column("attempt_number", sa.Integer(), nullable=False),
        sa.Column("response_text", sa.Text(), nullable=False),
        sa.Column(
            "submitted_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["assignment_id"], ["task_assignment.id"], ondelete="CASCADE"
        ),
        sa.UniqueConstraint("assignment_id", "attempt_number", name="uq_task_submission_attempt"),
        sa.CheckConstraint("attempt_number > 0", name="ck_task_submission_attempt_positive"),
        sa.CheckConstraint(
            "length(response_text) BETWEEN 1 AND 20000",
            name="ck_task_submission_response_length",
        ),
    )
    op.create_index(
        "ix_task_submission_assignment_submitted",
        "task_submission",
        ["assignment_id", "submitted_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_task_submission_assignment_submitted", table_name="task_submission")
    op.drop_table("task_submission")
    op.drop_index("ix_task_assignment_match", table_name="task_assignment")
    op.drop_index("ix_task_assignment_candidate_status", table_name="task_assignment")
    op.drop_table("task_assignment")
