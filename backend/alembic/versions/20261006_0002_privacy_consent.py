"""Add versioned candidate consent, privacy audit and export requests.

Revision ID: 20261006_0002
Revises: 20261006_0001
Create Date: 2026-10-06
"""

import sqlalchemy as sa

from alembic import op

revision = "20261006_0002"
down_revision = "20261006_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("candidate_profile", sa.Column("processing_consent_version", sa.String(64), nullable=True))
    op.add_column("candidate_profile", sa.Column("processing_consent_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("candidate_profile", sa.Column("processing_consent_source", sa.String(32), nullable=True))
    op.add_column("candidate_profile", sa.Column("publication_consent_version", sa.String(64), nullable=True))
    op.add_column("candidate_profile", sa.Column("publication_consent_source", sa.String(32), nullable=True))

    op.create_table(
        "audit_event",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("actor_identity_id", sa.String(36), nullable=False),
        sa.Column("event_type", sa.String(80), nullable=False),
        sa.Column("details", sa.Text(), nullable=False),
        sa.Column(
            "occurred_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["actor_identity_id"], ["user_identity.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_audit_event_actor_time", "audit_event", ["actor_identity_id", "occurred_at"])

    op.create_table(
        "privacy_request",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("identity_id", sa.String(36), nullable=False),
        sa.Column("request_type", sa.String(32), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["identity_id"], ["user_identity.id"], ondelete="CASCADE"),
        sa.CheckConstraint("request_type IN ('export', 'deletion')", name="ck_privacy_request_type"),
        sa.CheckConstraint(
            "status IN ('requested', 'processing', 'fulfilled', 'rejected', 'cancelled')",
            name="ck_privacy_request_status",
        ),
    )
    op.create_index("ix_privacy_request_identity_created", "privacy_request", ["identity_id", "created_at"])


def downgrade() -> None:
    op.drop_index("ix_privacy_request_identity_created", table_name="privacy_request")
    op.drop_table("privacy_request")
    op.drop_index("ix_audit_event_actor_time", table_name="audit_event")
    op.drop_table("audit_event")
    op.drop_column("candidate_profile", "publication_consent_source")
    op.drop_column("candidate_profile", "publication_consent_version")
    op.drop_column("candidate_profile", "processing_consent_source")
    op.drop_column("candidate_profile", "processing_consent_at")
    op.drop_column("candidate_profile", "processing_consent_version")
