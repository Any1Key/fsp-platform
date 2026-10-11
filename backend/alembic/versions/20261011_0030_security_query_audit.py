"""Add indexes identified by the M15 secret/log and query audit."""


from alembic import op

revision = "20261011_0030"
down_revision = "20261011_0029"
branch_labels = None
depends_on = None


INDEXES = (
    (
        "ix_candidate_profile_discoverable_updated",
        "candidate_profile",
        ("is_discoverable", "updated_at", "id"),
    ),
    (
        "ix_hiring_need_skill_need_preference",
        "hiring_need_skill",
        ("hiring_need_id", "preference", "skill_id"),
    ),
    ("ix_match_candidate", "talent_match", ("candidate_profile_id", "created_at")),
    (
        "ix_invitation_employer_candidate_status",
        "invitation",
        ("employer_identity_id", "candidate_profile_id", "status"),
    ),
    ("ix_invitation_company_created", "invitation", ("company_id", "created_at")),
    (
        "ix_conversation_contact_conversation_created",
        "conversation_contact_exchange",
        ("conversation_id", "created_at", "id"),
    ),
    (
        "ix_employer_trust_report_status_created",
        "employer_trust_report",
        ("status", "created_at", "id"),
    ),
)


def upgrade() -> None:
    for name, table, columns in INDEXES:
        op.create_index(name, table, list(columns))


def downgrade() -> None:
    for name, table, _ in reversed(INDEXES):
        op.drop_index(name, table_name=table)
