"""Index employer-approved task versions for optional local-AI retrieval."""

import sqlalchemy as sa

from alembic import op

revision = "20261007_0019"
down_revision = "20261007_0018"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "employer_task_example",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("task_version_id", sa.String(36), nullable=False, unique=True),
        sa.Column("company_id", sa.String(36), nullable=False),
        sa.Column("specialization_slug", sa.String(100), nullable=False),
        sa.Column("grade_slug", sa.String(16), nullable=False),
        sa.Column("target_skills", sa.JSON(), nullable=False),
        sa.Column("estimated_minutes", sa.Integer(), nullable=False),
        sa.Column("deadline_hours", sa.Integer(), nullable=False),
        sa.Column("approval_status", sa.String(16), nullable=False, server_default="approved"),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("approved_by_identity_id", sa.String(36), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["task_version_id"], ["employer_task_version.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["company_id"], ["company.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["approved_by_identity_id"], ["user_identity.id"], ondelete="RESTRICT"
        ),
        sa.CheckConstraint(
            "approval_status IN ('approved', 'rejected')",
            name="ck_employer_task_example_approval_status",
        ),
        sa.CheckConstraint(
            "grade_slug IN ('junior', 'middle', 'senior')",
            name="ck_employer_task_example_grade",
        ),
    )
    op.create_index(
        "ix_employer_task_example_company_status",
        "employer_task_example",
        ["company_id", "approval_status"],
    )

    # Preserve already-published examples when upgrading an existing install.
    # The source version ID is a stable migration-time example ID; future
    # publication writes a generated ID through the domain service.
    op.execute(
        sa.text(
            "INSERT INTO employer_task_example "
            "(id, task_version_id, company_id, specialization_slug, grade_slug, "
            "target_skills, estimated_minutes, deadline_hours, approval_status, "
            "approved_at, approved_by_identity_id) "
            "SELECT etv.id, etv.id, hn.company_id, s.slug, g.slug, etv.target_skills, "
            "etv.estimated_minutes, etv.deadline_hours, 'approved', "
            "COALESCE(etv.published_at, etv.updated_at), "
            "COALESCE(etv.published_by_identity_id, etv.updated_by_identity_id) "
            "FROM employer_task_version etv "
            "JOIN employer_task et ON et.id = etv.task_id "
            "JOIN hiring_need hn ON hn.id = et.hiring_need_id "
            "JOIN specialization s ON s.id = hn.specialization_id "
            "JOIN grade g ON g.id = hn.grade_id "
            "WHERE etv.status IN ('published', 'retired')"
        )
    )


def downgrade() -> None:
    op.drop_index(
        "ix_employer_task_example_company_status", table_name="employer_task_example"
    )
    op.drop_table("employer_task_example")
