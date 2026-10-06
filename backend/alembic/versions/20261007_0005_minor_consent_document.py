"""Add private minor representative-consent document metadata.

The bytes are kept in configured private storage; this table contains only
safe metadata and ownership/audit references.
"""

import sqlalchemy as sa

from alembic import op

revision = "20261007_0005"
down_revision = "20261007_0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "minor_consent_document",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("candidate_profile_id", sa.String(36), nullable=False),
        sa.Column("policy_version", sa.String(64), nullable=False),
        sa.Column("original_filename", sa.String(255), nullable=False),
        sa.Column("content_type", sa.String(100), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("sha256", sa.String(64), nullable=False),
        sa.Column("storage_key", sa.String(255), nullable=False, unique=True),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column(
            "uploaded_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reviewer_identity_id", sa.String(36), nullable=True),
        sa.ForeignKeyConstraint(["candidate_profile_id"], ["candidate_profile.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["reviewer_identity_id"], ["user_identity.id"], ondelete="SET NULL"),
        sa.CheckConstraint(
            "status IN ('submitted', 'approved', 'rejected', 'replaced', 'withdrawn')",
            name="ck_minor_consent_document_status",
        ),
    )
    op.create_index(
        "ix_minor_consent_document_candidate_status",
        "minor_consent_document",
        ["candidate_profile_id", "status", "uploaded_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_minor_consent_document_candidate_status", table_name="minor_consent_document")
    op.drop_table("minor_consent_document")
