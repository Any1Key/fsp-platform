"""Store structured candidate resume extraction awaiting review."""

import sqlalchemy as sa

from alembic import op

revision = "20261007_0007"
down_revision = "20261007_0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "resume_extraction",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("resume_document_id", sa.String(36), nullable=False, unique=True),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("parser_version", sa.String(80), nullable=False),
        sa.Column("fields", sa.Text(), nullable=False),
        sa.Column("reviewed_fields", sa.Text(), nullable=True),
        sa.Column("extracted_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["resume_document_id"], ["resume_document.id"], ondelete="CASCADE"),
        sa.CheckConstraint(
            "status IN ('needs_review', 'accepted', 'rejected', 'unsupported')",
            name="ck_resume_extraction_status",
        ),
    )


def downgrade() -> None:
    op.drop_table("resume_extraction")
