"""Add the data-driven taxonomy catalog and seed the initial vocabulary."""

import sqlalchemy as sa

from alembic import op

revision = "20261007_0008"
down_revision = "20261007_0007"
branch_labels = None
depends_on = None


SPECIALIZATIONS = (
    ("00000000-0000-4000-8000-000000000001", "backend-engineering", "Backend Engineering"),
    ("00000000-0000-4000-8000-000000000002", "frontend-engineering", "Frontend Engineering"),
    ("00000000-0000-4000-8000-000000000003", "full-stack-engineering", "Full-stack Engineering"),
    ("00000000-0000-4000-8000-000000000004", "qa-test-automation", "QA / Test Automation"),
    ("00000000-0000-4000-8000-000000000005", "devops-sre", "DevOps / SRE"),
    ("00000000-0000-4000-8000-000000000006", "data-engineering", "Data Engineering"),
    ("00000000-0000-4000-8000-000000000007", "data-science-ml", "Data Science / ML"),
    ("00000000-0000-4000-8000-000000000008", "mobile-engineering", "Mobile Engineering"),
)

GRADES = (
    ("00000000-0000-4000-8100-000000000001", "junior", "Junior", 1),
    ("00000000-0000-4000-8100-000000000002", "middle", "Middle", 2),
    ("00000000-0000-4000-8100-000000000003", "senior", "Senior", 3),
)

SKILLS = (
    ("00000000-0000-4000-8200-000000000001", "python", "Python"),
    ("00000000-0000-4000-8200-000000000002", "typescript", "TypeScript"),
    ("00000000-0000-4000-8200-000000000003", "sql", "SQL"),
    ("00000000-0000-4000-8200-000000000004", "rest-apis", "REST APIs"),
    ("00000000-0000-4000-8200-000000000005", "automated-testing", "Automated testing"),
    ("00000000-0000-4000-8200-000000000006", "git", "Git"),
    ("00000000-0000-4000-8200-000000000007", "docker", "Docker"),
    ("00000000-0000-4000-8200-000000000008", "kubernetes", "Kubernetes"),
    ("00000000-0000-4000-8200-000000000009", "data-modeling", "Data modeling"),
    ("00000000-0000-4000-8200-000000000010", "machine-learning", "Machine learning"),
    ("00000000-0000-4000-8200-000000000011", "swift", "Swift"),
)

SPECIALIZATION_SKILLS = {
    "backend-engineering": ("python", "sql", "rest-apis", "git"),
    "frontend-engineering": ("typescript", "automated-testing", "git"),
    "full-stack-engineering": ("python", "typescript", "sql", "rest-apis", "git"),
    "qa-test-automation": ("automated-testing", "python", "sql", "git"),
    "devops-sre": ("docker", "kubernetes", "python", "git"),
    "data-engineering": ("python", "sql", "data-modeling", "docker"),
    "data-science-ml": ("python", "sql", "machine-learning", "data-modeling"),
    "mobile-engineering": ("swift", "automated-testing", "git"),
}


def _timestamp() -> sa.Column:
    return sa.Column(
        "created_at",
        sa.DateTime(timezone=True),
        server_default=sa.text("CURRENT_TIMESTAMP"),
        nullable=False,
    )


def upgrade() -> None:
    op.create_table(
        "skill",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("slug", sa.String(100), nullable=False, unique=True),
        sa.Column("name", sa.String(160), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        _timestamp(),
    )
    op.create_table(
        "specialization_skill",
        sa.Column("specialization_id", sa.String(36), nullable=False),
        sa.Column("skill_id", sa.String(36), nullable=False),
        sa.Column("is_core", sa.Boolean(), nullable=False, server_default=sa.true()),
        _timestamp(),
        sa.ForeignKeyConstraint(["specialization_id"], ["specialization.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["skill_id"], ["skill.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("specialization_id", "skill_id"),
    )
    op.create_index(
        "ix_specialization_skill_skill",
        "specialization_skill",
        ["skill_id", "specialization_id"],
    )

    op.bulk_insert(
        sa.table(
            "specialization",
            sa.column("id", sa.String),
            sa.column("slug", sa.String),
            sa.column("name", sa.String),
        ),
        [{"id": id_, "slug": slug, "name": name} for id_, slug, name in SPECIALIZATIONS],
    )
    op.bulk_insert(
        sa.table(
            "grade",
            sa.column("id", sa.String),
            sa.column("slug", sa.String),
            sa.column("name", sa.String),
            sa.column("rank", sa.Integer),
        ),
        [{"id": id_, "slug": slug, "name": name, "rank": rank} for id_, slug, name, rank in GRADES],
    )
    op.bulk_insert(
        sa.table(
            "skill",
            sa.column("id", sa.String),
            sa.column("slug", sa.String),
            sa.column("name", sa.String),
        ),
        [{"id": id_, "slug": slug, "name": name} for id_, slug, name in SKILLS],
    )

    specialization_ids = {slug: id_ for id_, slug, _ in SPECIALIZATIONS}
    skill_ids = {slug: id_ for id_, slug, _ in SKILLS}
    mappings = []
    for specialization_slug, skill_slugs in SPECIALIZATION_SKILLS.items():
        for position, skill_slug in enumerate(skill_slugs):
            mappings.append(
                {
                    "specialization_id": specialization_ids[specialization_slug],
                    "skill_id": skill_ids[skill_slug],
                    "is_core": position < 2,
                }
            )
    op.bulk_insert(
        sa.table(
            "specialization_skill",
            sa.column("specialization_id", sa.String),
            sa.column("skill_id", sa.String),
            sa.column("is_core", sa.Boolean),
        ),
        mappings,
    )


def downgrade() -> None:
    op.drop_index("ix_specialization_skill_skill", table_name="specialization_skill")
    op.drop_table("specialization_skill")
    op.drop_table("skill")

    specialization_slugs = tuple(slug for _, slug, _ in SPECIALIZATIONS)
    grade_slugs = tuple(slug for _, slug, _, _ in GRADES)
    # The catalog is owned by this migration. Delete only these deterministic
    # seed rows so a downgrade cannot remove later administrator-created data.
    op.execute(
        sa.text("DELETE FROM specialization WHERE slug IN (" + ",".join(repr(slug) for slug in specialization_slugs) + ")")
    )
    op.execute(
        sa.text("DELETE FROM grade WHERE slug IN (" + ",".join(repr(slug) for slug in grade_slugs) + ")")
    )
