"""Read-only taxonomy catalog used by onboarding and later matching modules."""

from __future__ import annotations

from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session


def list_taxonomy(db: Session) -> dict[str, Any]:
    """Return the active catalog and explicit specialization/grade categories.

    The query intentionally reads the database rather than importing a Python
    constant. This keeps labels and IDs consistent with future administered
    taxonomy versions and makes the API useful to clients before sign-in.
    """

    specializations: dict[str, dict[str, Any]] = {}
    rows = db.execute(
        text(
            "SELECT s.id AS specialization_id, s.slug AS specialization_slug, "
            "s.name AS specialization_name, sk.id AS skill_id, sk.slug AS skill_slug, "
            "sk.name AS skill_name, ss.is_core "
            "FROM specialization s "
            "LEFT JOIN specialization_skill ss ON ss.specialization_id = s.id "
            "LEFT JOIN skill sk ON sk.id = ss.skill_id AND sk.active = :active "
            "WHERE s.active = :active "
            "ORDER BY s.name, sk.name"
        ),
        {"active": True},
    ).mappings()
    for row in rows:
        specialization = specializations.setdefault(
            row["specialization_slug"],
            {
                "id": row["specialization_id"],
                "slug": row["specialization_slug"],
                "name": row["specialization_name"],
                "skills": [],
            },
        )
        if row["skill_id"] is not None:
            specialization["skills"].append(
                {
                    "id": row["skill_id"],
                    "slug": row["skill_slug"],
                    "name": row["skill_name"],
                    "is_core": bool(row["is_core"]),
                }
            )

    grades = [
        dict(row)
        for row in db.execute(
            text(
                "SELECT id, slug, name, rank FROM grade "
                "ORDER BY rank, name"
            )
        ).mappings()
    ]
    categories = [
        {
            "key": f"{specialization['slug']}:{grade['slug']}",
            "specialization_slug": specialization["slug"],
            "grade_slug": grade["slug"],
            "label": f"{specialization['name']} · {grade['name']}",
        }
        for specialization in specializations.values()
        for grade in grades
    ]
    return {
        "specializations": list(specializations.values()),
        "grades": grades,
        "categories": categories,
    }
