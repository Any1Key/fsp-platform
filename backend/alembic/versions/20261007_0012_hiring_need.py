"""Add the employer-owned current hiring need and skill preferences."""

import sqlalchemy as sa

from alembic import op

revision = "20261007_0012"
down_revision = "20261007_0011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "hiring_need",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("company_id", sa.String(36), nullable=False, unique=True),
        sa.Column("team", sa.String(160), nullable=False),
        sa.Column("role", sa.String(160), nullable=False),
        sa.Column("specialization_id", sa.String(36), nullable=False),
        sa.Column("grade_id", sa.String(36), nullable=False),
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
        sa.ForeignKeyConstraint(["specialization_id"], ["specialization.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["grade_id"], ["grade.id"], ondelete="RESTRICT"),
    )
    op.create_index("ix_hiring_need_company", "hiring_need", ["company_id"])
    op.create_index(
        "ix_hiring_need_specialization_grade",
        "hiring_need",
        ["specialization_id", "grade_id"],
    )

    op.create_table(
        "hiring_need_skill",
        sa.Column("hiring_need_id", sa.String(36), nullable=False),
        sa.Column("skill_id", sa.String(36), nullable=False),
        sa.Column("preference", sa.String(16), nullable=False),
        sa.ForeignKeyConstraint(["hiring_need_id"], ["hiring_need.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["skill_id"], ["skill.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("hiring_need_id", "skill_id"),
        sa.CheckConstraint("preference IN ('required', 'preferred')", name="ck_hiring_need_skill_preference"),
    )
    op.create_index("ix_hiring_need_skill_skill", "hiring_need_skill", ["skill_id"])


def downgrade() -> None:
    op.drop_index("ix_hiring_need_skill_skill", table_name="hiring_need_skill")
    op.drop_table("hiring_need_skill")
    op.drop_index("ix_hiring_need_specialization_grade", table_name="hiring_need")
    op.drop_index("ix_hiring_need_company", table_name="hiring_need")
    op.drop_table("hiring_need")
