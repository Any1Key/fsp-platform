"""Create identity, taxonomy, and assessment foundation tables.

Revision ID: 20261006_0001
Revises:
Create Date: 2026-10-06
"""

import sqlalchemy as sa

from alembic import op

revision = "20261006_0001"
down_revision = None
branch_labels = None
depends_on = None


def _timestamp() -> sa.Column:
    return sa.Column(
        "created_at",
        sa.DateTime(timezone=True),
        server_default=sa.text("CURRENT_TIMESTAMP"),
        nullable=False,
    )


def upgrade() -> None:
    op.create_table(
        "user_identity",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("keycloak_sub", sa.String(255), nullable=False, unique=True),
        sa.Column("email", sa.String(320), nullable=False, unique=True),
        sa.Column("role", sa.String(32), nullable=False),
        sa.Column("email_verified", sa.Boolean(), nullable=False, server_default=sa.false()),
        _timestamp(),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.CheckConstraint("role IN ('candidate', 'employer', 'admin', 'reviewer')", name="ck_user_identity_role"),
    )

    op.create_table(
        "specialization",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("slug", sa.String(100), nullable=False, unique=True),
        sa.Column("name", sa.String(160), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        _timestamp(),
    )
    op.create_table(
        "grade",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("slug", sa.String(50), nullable=False, unique=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("rank", sa.Integer(), nullable=False),
        _timestamp(),
    )
    op.create_table(
        "candidate_profile",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("identity_id", sa.String(36), nullable=False, unique=True),
        sa.Column("specialization_id", sa.String(36), nullable=True),
        sa.Column("declared_grade_id", sa.String(36), nullable=True),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("experience", sa.JSON(), nullable=True),
        sa.Column("preferences", sa.JSON(), nullable=True),
        sa.Column("is_discoverable", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("publication_consent_at", sa.DateTime(timezone=True), nullable=True),
        _timestamp(),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["identity_id"], ["user_identity.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["specialization_id"], ["specialization.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["declared_grade_id"], ["grade.id"], ondelete="RESTRICT"),
    )

    op.create_table(
        "assessment_blueprint",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("specialization_id", sa.String(36), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(160), nullable=False),
        sa.Column("configuration", sa.JSON(), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        _timestamp(),
        sa.ForeignKeyConstraint(["specialization_id"], ["specialization.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("specialization_id", "version", name="uq_assessment_blueprint_specialization_version"),
    )
    op.create_table(
        "question_family",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("blueprint_id", sa.String(36), nullable=False),
        sa.Column("family_key", sa.String(100), nullable=False),
        sa.Column("target_difficulty", sa.Float(), nullable=False),
        sa.Column("exposure_budget", sa.Integer(), nullable=False),
        sa.Column("cooldown_seconds", sa.Integer(), nullable=False),
        _timestamp(),
        sa.ForeignKeyConstraint(["blueprint_id"], ["assessment_blueprint.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("blueprint_id", "family_key", name="uq_question_family_blueprint_key"),
    )
    op.create_table(
        "question_template",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("family_id", sa.String(36), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("prompt_template", sa.Text(), nullable=False),
        sa.Column("rubric", sa.JSON(), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        _timestamp(),
        sa.ForeignKeyConstraint(["family_id"], ["question_family.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("family_id", "version", name="uq_question_template_family_version"),
    )
    op.create_table(
        "question_variant",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("template_id", sa.String(36), nullable=False),
        sa.Column("variant_key", sa.String(100), nullable=False),
        sa.Column("parameter_schema", sa.JSON(), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        _timestamp(),
        sa.ForeignKeyConstraint(["template_id"], ["question_template.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("template_id", "variant_key", name="uq_question_variant_template_key"),
    )
    op.create_table(
        "assessment_attempt",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("candidate_id", sa.String(36), nullable=False),
        sa.Column("blueprint_id", sa.String(36), nullable=False),
        sa.Column("specialization_id", sa.String(36), nullable=False),
        sa.Column("declared_grade_id", sa.String(36), nullable=True),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("form_fingerprint", sa.String(128), nullable=False),
        _timestamp(),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["candidate_id"], ["candidate_profile.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["blueprint_id"], ["assessment_blueprint.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["specialization_id"], ["specialization.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["declared_grade_id"], ["grade.id"], ondelete="RESTRICT"),
        sa.CheckConstraint("status IN ('started', 'submitted', 'expired', 'locked')", name="ck_assessment_attempt_status"),
    )
    op.create_table(
        "assessment_attempt_item",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("attempt_id", sa.String(36), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("family_id", sa.String(36), nullable=False),
        sa.Column("template_id", sa.String(36), nullable=False),
        sa.Column("variant_id", sa.String(36), nullable=False),
        sa.Column("prompt_artifact", sa.JSON(), nullable=False),
        sa.Column("answer_key_digest", sa.String(128), nullable=False),
        sa.ForeignKeyConstraint(["attempt_id"], ["assessment_attempt.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["family_id"], ["question_family.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["template_id"], ["question_template.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["variant_id"], ["question_variant.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("attempt_id", "position", name="uq_attempt_item_position"),
    )
    op.create_table(
        "assessment_answer",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("item_id", sa.String(36), nullable=False, unique=True),
        sa.Column("answer_payload", sa.JSON(), nullable=False),
        sa.Column("followup_payload", sa.JSON(), nullable=True),
        _timestamp(),
        sa.ForeignKeyConstraint(["item_id"], ["assessment_attempt_item.id"], ondelete="CASCADE"),
    )
    op.create_table(
        "assessment_result",
        sa.Column("attempt_id", sa.String(36), primary_key=True),
        sa.Column("raw_score", sa.Float(), nullable=False),
        sa.Column("normalized_score", sa.Float(), nullable=False),
        sa.Column("verified_grade_id", sa.String(36), nullable=True),
        sa.Column("decision", sa.String(32), nullable=False),
        sa.Column("scoring_version", sa.String(50), nullable=False),
        sa.Column("integrity_signals", sa.JSON(), nullable=False),
        _timestamp(),
        sa.ForeignKeyConstraint(["attempt_id"], ["assessment_attempt.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["verified_grade_id"], ["grade.id"], ondelete="RESTRICT"),
        sa.CheckConstraint("decision IN ('passed', 'not_passed', 'unconfirmed')", name="ck_assessment_result_decision"),
    )

    op.create_index("ix_candidate_profile_specialization_grade", "candidate_profile", ["specialization_id", "declared_grade_id"])
    op.create_index("ix_assessment_attempt_candidate_status", "assessment_attempt", ["candidate_id", "status"])
    op.create_index("ix_assessment_attempt_item_variant", "assessment_attempt_item", ["variant_id"])


def downgrade() -> None:
    op.drop_index("ix_assessment_attempt_item_variant", table_name="assessment_attempt_item")
    op.drop_index("ix_assessment_attempt_candidate_status", table_name="assessment_attempt")
    op.drop_index("ix_candidate_profile_specialization_grade", table_name="candidate_profile")
    op.drop_table("assessment_result")
    op.drop_table("assessment_answer")
    op.drop_table("assessment_attempt_item")
    op.drop_table("assessment_attempt")
    op.drop_table("question_variant")
    op.drop_table("question_template")
    op.drop_table("question_family")
    op.drop_table("assessment_blueprint")
    op.drop_table("candidate_profile")
    op.drop_table("grade")
    op.drop_table("specialization")
    op.drop_table("user_identity")
