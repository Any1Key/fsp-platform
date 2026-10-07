"""Add the employer-owned company profile boundary."""

import sqlalchemy as sa

from alembic import op

revision = "20261007_0011"
down_revision = "20261007_0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "company",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("owner_identity_id", sa.String(36), nullable=False, unique=True),
        sa.Column("name", sa.String(160), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("industry", sa.String(120), nullable=True),
        sa.Column("website", sa.String(255), nullable=True),
        sa.Column("location", sa.String(120), nullable=True),
        sa.Column("public_contact_method", sa.String(160), nullable=True),
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
        sa.ForeignKeyConstraint(["owner_identity_id"], ["user_identity.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_company_owner_identity", "company", ["owner_identity_id"])


def downgrade() -> None:
    op.drop_index("ix_company_owner_identity", table_name="company")
    op.drop_table("company")
