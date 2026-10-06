"""Add private candidate resume document metadata."""

import sqlalchemy as sa

from alembic import op

revision = "20261007_0006"
down_revision = "20261007_0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "resume_document",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("candidate_profile_id", sa.String(36), nullable=False),
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
        sa.ForeignKeyConstraint(["candidate_profile_id"], ["candidate_profile.id"], ondelete="CASCADE"),
        sa.CheckConstraint(
            "status IN ('uploaded', 'replaced', 'withdrawn')",
            name="ck_resume_document_status",
        ),
    )
    op.create_index(
        "ix_resume_document_candidate_status",
        "resume_document",
        ["candidate_profile_id", "status", "uploaded_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_resume_document_candidate_status", table_name="resume_document")
    op.drop_table("resume_document")
