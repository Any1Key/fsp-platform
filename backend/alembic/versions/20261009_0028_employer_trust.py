"""Add candidate employer-trust reports and a reviewer queue."""

import sqlalchemy as sa

from alembic import op


revision = "20261009_0028"
down_revision = "20261008_0027"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "employer_trust_report",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("invitation_id", sa.String(36), nullable=False),
        sa.Column("company_id", sa.String(36), nullable=False),
        sa.Column("reporter_identity_id", sa.String(36), nullable=False),
        sa.Column("reason", sa.String(32), nullable=False),
        sa.Column("details", sa.String(500), nullable=True),
        sa.Column("status", sa.String(24), nullable=False, server_default="open"),
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
        sa.ForeignKeyConstraint(["invitation_id"], ["invitation.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["company_id"], ["company.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["reporter_identity_id"], ["user_identity.id"], ondelete="CASCADE"
        ),
        sa.UniqueConstraint(
            "invitation_id",
            "reporter_identity_id",
            name="uq_employer_trust_report_invitation_reporter",
        ),
        sa.CheckConstraint(
            "reason IN ('fake_vacancy', 'fee_request', 'misleading_offer', 'spam', 'other')",
            name="ck_employer_trust_report_reason",
        ),
        sa.CheckConstraint(
            "status IN ('open', 'reviewed', 'closed')",
            name="ck_employer_trust_report_status",
        ),
    )
    op.create_index(
        "ix_employer_trust_report_company_status_created",
        "employer_trust_report",
        ["company_id", "status", "created_at"],
    )
    op.create_index(
        "ix_employer_trust_report_invitation_created",
        "employer_trust_report",
        ["invitation_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_employer_trust_report_invitation_created", table_name="employer_trust_report"
    )
    op.drop_index(
        "ix_employer_trust_report_company_status_created", table_name="employer_trust_report"
    )
    op.drop_table("employer_trust_report")
