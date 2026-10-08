"""Add candidate vacancy applications and append-only status history."""

import sqlalchemy as sa

from alembic import op

revision = "20261008_0023"
down_revision = "20261008_0022"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "application",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("vacancy_id", sa.String(36), nullable=False),
        sa.Column("candidate_profile_id", sa.String(36), nullable=False),
        sa.Column("status", sa.String(16), nullable=False, server_default="submitted"),
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
        sa.ForeignKeyConstraint(["vacancy_id"], ["vacancy.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["candidate_profile_id"], ["candidate_profile.id"], ondelete="CASCADE"
        ),
        sa.UniqueConstraint(
            "vacancy_id", "candidate_profile_id", name="uq_application_vacancy_candidate"
        ),
        sa.CheckConstraint(
            "status IN ('submitted', 'reviewing', 'shortlisted', 'rejected', 'withdrawn')",
            name="ck_application_status",
        ),
    )
    op.create_index(
        "ix_application_candidate_created",
        "application",
        ["candidate_profile_id", "created_at"],
    )
    op.create_index(
        "ix_application_vacancy_status",
        "application",
        ["vacancy_id", "status"],
    )

    op.create_table(
        "application_status_history",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("application_id", sa.String(36), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column(
            "changed_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["application_id"], ["application.id"], ondelete="CASCADE"
        ),
        sa.CheckConstraint(
            "status IN ('submitted', 'reviewing', 'shortlisted', 'rejected', 'withdrawn')",
            name="ck_application_status_history_status",
        ),
    )
    op.create_index(
        "ix_application_status_history_application",
        "application_status_history",
        ["application_id", "changed_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_application_status_history_application",
        table_name="application_status_history",
    )
    op.drop_table("application_status_history")
    op.drop_index("ix_application_vacancy_status", table_name="application")
    op.drop_index("ix_application_candidate_created", table_name="application")
    op.drop_table("application")
