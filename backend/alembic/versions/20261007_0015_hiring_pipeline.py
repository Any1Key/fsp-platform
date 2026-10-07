"""Add employer-owned ordered hiring pipelines and safe invitation previews."""

import sqlalchemy as sa

from alembic import op

revision = "20261007_0015"
down_revision = "20261007_0014"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "hiring_pipeline",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("hiring_need_id", sa.String(36), nullable=False, unique=True),
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
    )
    op.create_index("ix_hiring_pipeline_need", "hiring_pipeline", ["hiring_need_id"])

    op.create_table(
        "pipeline_stage",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("pipeline_id", sa.String(36), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("stage_type", sa.String(32), nullable=False),
        sa.Column("title", sa.String(120), nullable=False),
        sa.Column("required", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("estimated_minutes", sa.Integer(), nullable=False, server_default="30"),
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
        sa.ForeignKeyConstraint(["pipeline_id"], ["hiring_pipeline.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("pipeline_id", "position", name="uq_pipeline_stage_position"),
        sa.CheckConstraint(
            "stage_type IN ('platform_review', 'employer_task', 'questionnaire', "
            "'portfolio_review', 'interview', 'custom', 'final_decision')",
            name="ck_pipeline_stage_type",
        ),
        sa.CheckConstraint("position >= 0", name="ck_pipeline_stage_position_positive"),
        sa.CheckConstraint(
            "estimated_minutes BETWEEN 5 AND 480",
            name="ck_pipeline_stage_duration",
        ),
    )
    op.create_index("ix_pipeline_stage_order", "pipeline_stage", ["pipeline_id", "position"])
    op.add_column("invitation", sa.Column("pipeline_snapshot", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("invitation", "pipeline_snapshot")
    op.drop_index("ix_pipeline_stage_order", table_name="pipeline_stage")
    op.drop_table("pipeline_stage")
    op.drop_index("ix_hiring_pipeline_need", table_name="hiring_pipeline")
    op.drop_table("hiring_pipeline")
