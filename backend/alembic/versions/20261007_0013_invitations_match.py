"""Add salary-bearing reverse-recruitment invitations and matches."""

import sqlalchemy as sa

from alembic import op

revision = "20261007_0013"
down_revision = "20261007_0012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "invitation",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("employer_identity_id", sa.String(36), nullable=False),
        sa.Column("company_id", sa.String(36), nullable=False),
        sa.Column("candidate_profile_id", sa.String(36), nullable=False),
        sa.Column("salary_min_rub", sa.Integer(), nullable=False),
        sa.Column("salary_max_rub", sa.Integer(), nullable=False),
        sa.Column("offer_description", sa.Text(), nullable=False),
        sa.Column("company_name_snapshot", sa.String(160), nullable=False),
        sa.Column("contact_method_snapshot", sa.String(160), nullable=False),
        sa.Column("status", sa.String(24), nullable=False, server_default="pending"),
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
        sa.Column("responded_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("matched_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("contact_unlocked_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["employer_identity_id"], ["user_identity.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["company_id"], ["company.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["candidate_profile_id"], ["candidate_profile.id"], ondelete="CASCADE"),
        sa.CheckConstraint("salary_min_rub > 0", name="ck_invitation_salary_min_positive"),
        sa.CheckConstraint("salary_max_rub >= salary_min_rub", name="ck_invitation_salary_range"),
        sa.CheckConstraint(
            "status IN ('pending', 'accepted', 'declined')",
            name="ck_invitation_status",
        ),
    )
    op.create_index(
        "ix_invitation_employer_created",
        "invitation",
        ["employer_identity_id", "created_at"],
    )
    op.create_index(
        "ix_invitation_candidate_created",
        "invitation",
        ["candidate_profile_id", "created_at"],
    )
    op.create_index(
        "ix_invitation_candidate_status",
        "invitation",
        ["candidate_profile_id", "status"],
    )

    op.create_table(
        "talent_match",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("invitation_id", sa.String(36), nullable=False, unique=True),
        sa.Column("employer_identity_id", sa.String(36), nullable=False),
        sa.Column("candidate_profile_id", sa.String(36), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "contact_unlocked_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["invitation_id"], ["invitation.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["employer_identity_id"], ["user_identity.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["candidate_profile_id"], ["candidate_profile.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_match_employer_candidate", "talent_match", ["employer_identity_id", "candidate_profile_id"])

    op.create_table(
        "domain_event",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("event_type", sa.String(80), nullable=False),
        sa.Column("aggregate_type", sa.String(80), nullable=False),
        sa.Column("aggregate_id", sa.String(36), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column(
            "occurred_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.UniqueConstraint("event_type", "aggregate_type", "aggregate_id", name="uq_domain_event_once"),
    )
    op.create_index(
        "ix_domain_event_aggregate_time",
        "domain_event",
        ["aggregate_type", "aggregate_id", "occurred_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_domain_event_aggregate_time", table_name="domain_event")
    op.drop_table("domain_event")
    op.drop_index("ix_match_employer_candidate", table_name="talent_match")
    op.drop_table("talent_match")
    op.drop_index("ix_invitation_candidate_status", table_name="invitation")
    op.drop_index("ix_invitation_candidate_created", table_name="invitation")
    op.drop_index("ix_invitation_employer_created", table_name="invitation")
    op.drop_table("invitation")
