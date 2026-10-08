"""Allow employers to accept applications and link their match bridge."""

import sqlalchemy as sa

from alembic import op

revision = "20261008_0024"
down_revision = "20261008_0023"
branch_labels = None
depends_on = None


def _replace_status_check(
    table_name: str, constraint_name: str, expression: str
) -> None:
    """Replace a check constraint without recreating FK-referenced tables."""

    if op.get_bind().dialect.name == "postgresql":
        # PostgreSQL cannot recreate ``application`` while the history table's
        # foreign key still references its primary key.  Direct ALTER TABLE
        # keeps that dependency intact during this additive migration.
        op.drop_constraint(constraint_name, table_name=table_name, type_="check")
        op.create_check_constraint(constraint_name, table_name, expression)
        return

    # SQLite has no general ALTER TABLE support for constraints, so retain
    # Alembic's table-copy implementation for the test/dev database.
    with op.batch_alter_table(table_name, recreate="always") as batch_op:
        batch_op.drop_constraint(constraint_name, type_="check")
        batch_op.create_check_constraint(constraint_name, expression)


def upgrade() -> None:
    _replace_status_check(
        "application",
        "ck_application_status",
        "status IN ('submitted', 'reviewing', 'shortlisted', 'accepted', 'rejected', 'withdrawn')",
    )
    _replace_status_check(
        "application_status_history",
        "ck_application_status_history_status",
        "status IN ('submitted', 'reviewing', 'shortlisted', 'accepted', 'rejected', 'withdrawn')",
    )

    with op.batch_alter_table("invitation") as batch_op:
        batch_op.add_column(sa.Column("source_application_id", sa.String(36), nullable=True))
        batch_op.create_foreign_key(
            "fk_invitation_source_application",
            "application",
            ["source_application_id"],
            ["id"],
            ondelete="SET NULL",
        )
        batch_op.create_unique_constraint(
            "uq_invitation_source_application", ["source_application_id"]
        )


def downgrade() -> None:
    with op.batch_alter_table("invitation") as batch_op:
        batch_op.drop_constraint("uq_invitation_source_application", type_="unique")
        batch_op.drop_constraint("fk_invitation_source_application", type_="foreignkey")
        batch_op.drop_column("source_application_id")

    _replace_status_check(
        "application_status_history",
        "ck_application_status_history_status",
        "status IN ('submitted', 'reviewing', 'shortlisted', 'rejected', 'withdrawn')",
    )
    _replace_status_check(
        "application",
        "ck_application_status",
        "status IN ('submitted', 'reviewing', 'shortlisted', 'rejected', 'withdrawn')",
    )
