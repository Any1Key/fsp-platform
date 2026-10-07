"""Add employer-owned task drafts and immutable published versions."""

import sqlalchemy as sa

from alembic import op

revision = "20261007_0016"
down_revision = "20261007_0015"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "employer_task",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("hiring_need_id", sa.String(36), nullable=False),
        sa.Column("pipeline_stage_id", sa.String(36), nullable=True),
        sa.Column("created_by_identity_id", sa.String(36), nullable=False),
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
        sa.ForeignKeyConstraint(["hiring_need_id"], ["hiring_need.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["pipeline_stage_id"], ["pipeline_stage.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(
            ["created_by_identity_id"], ["user_identity.id"], ondelete="RESTRICT"
        ),
    )
    op.create_index("ix_employer_task_need", "employer_task", ["hiring_need_id"])
    op.create_index("ix_employer_task_stage", "employer_task", ["pipeline_stage_id"])

    op.create_table(
        "employer_task_version",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("task_id", sa.String(36), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(16), nullable=False, server_default="draft"),
        sa.Column("title", sa.String(160), nullable=False),
        sa.Column("instructions", sa.Text(), nullable=False),
        sa.Column("target_skills", sa.JSON(), nullable=False),
        sa.Column("expected_grade", sa.String(16), nullable=False),
        sa.Column("estimated_minutes", sa.Integer(), nullable=False),
        sa.Column("deadline_hours", sa.Integer(), nullable=False),
        sa.Column("rubric", sa.JSON(), nullable=False),
        sa.Column("created_by_identity_id", sa.String(36), nullable=False),
        sa.Column("updated_by_identity_id", sa.String(36), nullable=False),
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
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("published_by_identity_id", sa.String(36), nullable=True),
        sa.ForeignKeyConstraint(["task_id"], ["employer_task.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["created_by_identity_id"], ["user_identity.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["updated_by_identity_id"], ["user_identity.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["published_by_identity_id"], ["user_identity.id"], ondelete="RESTRICT"
        ),
        sa.UniqueConstraint("task_id", "version_number", name="uq_employer_task_version_number"),
        sa.CheckConstraint(
            "status IN ('draft', 'published', 'retired')",
            name="ck_employer_task_version_status",
        ),
        sa.CheckConstraint(
            "expected_grade IN ('junior', 'middle', 'senior')",
            name="ck_employer_task_version_grade",
        ),
        sa.CheckConstraint(
            "estimated_minutes BETWEEN 5 AND 480",
            name="ck_employer_task_version_duration",
        ),
        sa.CheckConstraint(
            "deadline_hours BETWEEN 1 AND 720",
            name="ck_employer_task_version_deadline",
        ),
    )
    op.create_index(
        "ix_employer_task_version_task_status",
        "employer_task_version",
        ["task_id", "status", "version_number"],
    )


def downgrade() -> None:
    op.drop_index("ix_employer_task_version_task_status", table_name="employer_task_version")
    op.drop_table("employer_task_version")
    op.drop_index("ix_employer_task_stage", table_name="employer_task")
    op.drop_index("ix_employer_task_need", table_name="employer_task")
    op.drop_table("employer_task")
