"""Add match-bound internal conversations, messages and privacy-safe moderation."""

import sqlalchemy as sa

from alembic import op

revision = "20261007_0014"
down_revision = "20261007_0013"
branch_labels = None
depends_on = None


def _created_at() -> sa.Column:
    return sa.Column(
        "created_at",
        sa.DateTime(timezone=True),
        server_default=sa.text("CURRENT_TIMESTAMP"),
        nullable=False,
    )


def upgrade() -> None:
    op.create_table(
        "conversation",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("match_id", sa.String(36), nullable=False, unique=True),
        _created_at(),
        sa.Column("last_message_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["match_id"], ["talent_match.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_conversation_last_message", "conversation", ["last_message_at"])

    op.create_table(
        "conversation_member",
        sa.Column("conversation_id", sa.String(36), nullable=False),
        sa.Column("identity_id", sa.String(36), nullable=False),
        sa.Column(
            "joined_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["conversation_id"], ["conversation.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["identity_id"], ["user_identity.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("conversation_id", "identity_id"),
    )
    op.create_index("ix_conversation_member_identity", "conversation_member", ["identity_id"])

    op.create_table(
        "message",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("conversation_id", sa.String(36), nullable=False),
        sa.Column("sender_identity_id", sa.String(36), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        _created_at(),
        sa.ForeignKeyConstraint(["conversation_id"], ["conversation.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["sender_identity_id"], ["user_identity.id"], ondelete="CASCADE"),
        sa.CheckConstraint("length(body) BETWEEN 1 AND 4000", name="ck_message_body_length"),
    )
    op.create_index("ix_message_conversation_created", "message", ["conversation_id", "created_at"])

    op.create_table(
        "message_read",
        sa.Column("message_id", sa.String(36), nullable=False),
        sa.Column("identity_id", sa.String(36), nullable=False),
        sa.Column(
            "read_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["message_id"], ["message.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["identity_id"], ["user_identity.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("message_id", "identity_id"),
    )
    op.create_index("ix_message_read_identity", "message_read", ["identity_id", "read_at"])

    op.create_table(
        "conversation_contact_exchange",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("conversation_id", sa.String(36), nullable=False),
        sa.Column("identity_id", sa.String(36), nullable=False),
        sa.Column("contact_type", sa.String(24), nullable=False),
        sa.Column("contact_value", sa.String(160), nullable=False),
        _created_at(),
        sa.ForeignKeyConstraint(["conversation_id"], ["conversation.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["identity_id"], ["user_identity.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("conversation_id", "identity_id", name="uq_conversation_contact_identity"),
        sa.CheckConstraint(
            "contact_type IN ('email', 'phone', 'telegram', 'other')",
            name="ck_contact_exchange_type",
        ),
    )

    op.create_table(
        "conversation_report",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("conversation_id", sa.String(36), nullable=False),
        sa.Column("reporter_identity_id", sa.String(36), nullable=False),
        sa.Column("reason", sa.String(32), nullable=False),
        sa.Column("details", sa.String(500), nullable=True),
        sa.Column("status", sa.String(24), nullable=False, server_default="open"),
        _created_at(),
        sa.ForeignKeyConstraint(["conversation_id"], ["conversation.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["reporter_identity_id"], ["user_identity.id"], ondelete="CASCADE"),
        sa.CheckConstraint(
            "reason IN ('spam', 'harassment', 'inappropriate', 'other')",
            name="ck_conversation_report_reason",
        ),
        sa.CheckConstraint("status IN ('open', 'reviewed', 'closed')", name="ck_conversation_report_status"),
    )
    op.create_index(
        "ix_conversation_report_conversation_created",
        "conversation_report",
        ["conversation_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_conversation_report_conversation_created", table_name="conversation_report")
    op.drop_table("conversation_report")
    op.drop_table("conversation_contact_exchange")
    op.drop_index("ix_message_read_identity", table_name="message_read")
    op.drop_table("message_read")
    op.drop_index("ix_message_conversation_created", table_name="message")
    op.drop_table("message")
    op.drop_index("ix_conversation_member_identity", table_name="conversation_member")
    op.drop_table("conversation_member")
    op.drop_index("ix_conversation_last_message", table_name="conversation")
    op.drop_table("conversation")
