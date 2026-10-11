"""Add candidate privacy request lifecycle and retention scheduling."""

import sqlalchemy as sa

from alembic import op

revision = "20261011_0029"
down_revision = "20261009_0028"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "privacy_request",
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
    )
    op.add_column("privacy_request", sa.Column("scheduled_for", sa.DateTime(timezone=True), nullable=True))
    op.create_index(
        "uq_privacy_request_active_identity_type",
        "privacy_request",
        ["identity_id", "request_type"],
        unique=True,
        sqlite_where=sa.text("status IN ('requested', 'processing')"),
        postgresql_where=sa.text("status IN ('requested', 'processing')"),
    )


def downgrade() -> None:
    op.drop_index("uq_privacy_request_active_identity_type", table_name="privacy_request")
    op.drop_column("privacy_request", "scheduled_for")
    op.drop_column("privacy_request", "updated_at")
