"""Add employer-owned vacancies with a salary-bearing publication lifecycle."""

import sqlalchemy as sa

from alembic import op

revision = "20261008_0022"
down_revision = "20261008_0021"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "vacancy",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("company_id", sa.String(36), nullable=False),
        sa.Column("title", sa.String(160), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("location", sa.String(120), nullable=True),
        sa.Column("work_mode", sa.String(16), nullable=True),
        sa.Column("employment_type", sa.String(16), nullable=True),
        sa.Column("salary_min_rub", sa.Integer(), nullable=False),
        sa.Column("salary_max_rub", sa.Integer(), nullable=False),
        sa.Column("specialization_id", sa.String(36), nullable=True),
        sa.Column("grade_id", sa.String(36), nullable=True),
        sa.Column("status", sa.String(16), nullable=False, server_default="draft"),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
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
        sa.ForeignKeyConstraint(["company_id"], ["company.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["specialization_id"], ["specialization.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(["grade_id"], ["grade.id"], ondelete="RESTRICT"),
        sa.CheckConstraint(
            "salary_min_rub > 0 AND salary_max_rub >= salary_min_rub",
            name="ck_vacancy_salary_range",
        ),
        sa.CheckConstraint(
            "status IN ('draft', 'published', 'closed')",
            name="ck_vacancy_status",
        ),
        sa.CheckConstraint(
            "work_mode IS NULL OR work_mode IN ('office', 'hybrid', 'remote')",
            name="ck_vacancy_work_mode",
        ),
        sa.CheckConstraint(
            "employment_type IS NULL OR employment_type IN ('full_time', 'part_time', 'project')",
            name="ck_vacancy_employment_type",
        ),
    )
    op.create_index("ix_vacancy_company_status", "vacancy", ["company_id", "status"])
    op.create_index("ix_vacancy_publication", "vacancy", ["status", "published_at"])


def downgrade() -> None:
    op.drop_index("ix_vacancy_publication", table_name="vacancy")
    op.drop_index("ix_vacancy_company_status", table_name="vacancy")
    op.drop_table("vacancy")
