"""Employer-owned hiring need input for later Talent Radar matching."""

from __future__ import annotations

from typing import Any
from uuid import uuid4

from fastapi import HTTPException, status
from sqlalchemy import bindparam, text
from sqlalchemy.orm import Session

from .auth import Principal
from .companies import _ensure_company

NEED_FIELDS = ("team", "role", "specialization", "grade", "required_skills", "preferred_skills")


def _clean_text(value: Any) -> Any:
    return value.strip() if isinstance(value, str) else value


def _validate_catalog(
    db: Session,
    *,
    specialization: str,
    grade: str,
    required_skills: list[str],
    preferred_skills: list[str],
) -> dict[str, Any]:
    specialization_row = db.execute(
        text(
            "SELECT id, slug, name FROM specialization "
            "WHERE slug = :slug AND active = :active"
        ),
        {"slug": specialization, "active": True},
    ).mappings().one_or_none()
    grade_row = db.execute(
        text("SELECT id, slug, name FROM grade WHERE slug = :slug"),
        {"slug": grade},
    ).mappings().one_or_none()
    if specialization_row is None or grade_row is None:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="hiring_need_taxonomy_invalid")

    combined = required_skills + preferred_skills
    if len(set(combined)) != len(combined):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="hiring_need_duplicate_skill")

    if len(combined) > 20:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="hiring_need_too_many_skills")

    if not combined:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="hiring_need_skills_required")

    skill_rows = list(
        db.execute(
            text(
                "SELECT sk.id, sk.slug, sk.name "
                "FROM skill sk "
                "WHERE sk.active = :active "
                "AND sk.slug IN :slugs ORDER BY sk.name"
            ).bindparams(bindparam("slugs", expanding=True)),
            {
                "active": True,
                "slugs": tuple(combined),
            },
        ).mappings()
    )
    if {row["slug"] for row in skill_rows} != set(combined):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="hiring_need_skill_not_available",
        )
    skills_by_slug = {row["slug"]: dict(row) for row in skill_rows}
    return {
        "specialization": dict(specialization_row),
        "grade": dict(grade_row),
        "required_skills": [skills_by_slug[slug] for slug in required_skills],
        "preferred_skills": [skills_by_slug[slug] for slug in preferred_skills],
    }


def _need_response(db: Session, need_id: str) -> dict[str, Any]:
    need = db.execute(
        text(
            "SELECT hn.id, hn.team, hn.role, hn.created_at, hn.updated_at, "
            "s.slug AS specialization_slug, s.name AS specialization_name, "
            "g.slug AS grade_slug, g.name AS grade_name "
            "FROM hiring_need hn "
            "JOIN specialization s ON s.id = hn.specialization_id "
            "JOIN grade g ON g.id = hn.grade_id WHERE hn.id = :need_id"
        ),
        {"need_id": need_id},
    ).mappings().one()
    skill_rows = db.execute(
        text(
            "SELECT sk.slug, sk.name, hns.preference FROM hiring_need_skill hns "
            "JOIN skill sk ON sk.id = hns.skill_id "
            "WHERE hns.hiring_need_id = :need_id ORDER BY sk.name"
        ),
        {"need_id": need_id},
    ).mappings()
    required_skills = []
    preferred_skills = []
    for row in skill_rows:
        skill = {"slug": row["slug"], "name": row["name"]}
        (required_skills if row["preference"] == "required" else preferred_skills).append(skill)
    return {
        "id": need["id"],
        "team": need["team"],
        "role": need["role"],
        "specialization": {
            "slug": need["specialization_slug"],
            "name": need["specialization_name"],
        },
        "grade": {"slug": need["grade_slug"], "name": need["grade_name"]},
        "required_skills": required_skills,
        "preferred_skills": preferred_skills,
        "created_at": need["created_at"],
        "updated_at": need["updated_at"],
    }


def _payload_values(payload: dict[str, Any], current: dict[str, Any] | None = None) -> dict[str, Any]:
    values = {
        "team": current["team"] if current else None,
        "role": current["role"] if current else None,
        "specialization": current["specialization"]["slug"] if current else None,
        "grade": current["grade"]["slug"] if current else None,
        "required_skills": [skill["slug"] for skill in current["required_skills"]] if current else [],
        "preferred_skills": [skill["slug"] for skill in current["preferred_skills"]] if current else [],
    }
    for field, value in payload.items():
        if field in NEED_FIELDS:
            if field.endswith("skills"):
                values[field] = [] if value is None else [_clean_text(item) for item in value]
            else:
                values[field] = _clean_text(value)
    if not all(values[field] for field in ("team", "role", "specialization", "grade")):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="hiring_need_fields_required")
    return values


def _write_need(db: Session, company_id: str, values: dict[str, Any], need_id: str | None = None) -> dict[str, Any]:
    catalog = _validate_catalog(db, **{field: values[field] for field in ("specialization", "grade", "required_skills", "preferred_skills")})
    specialization_id = catalog["specialization"]["id"]
    grade_id = catalog["grade"]["id"]
    if need_id is None:
        need_id = str(uuid4())
        db.execute(
            text(
                "INSERT INTO hiring_need "
                "(id, company_id, team, role, specialization_id, grade_id) "
                "VALUES (:id, :company_id, :team, :role, :specialization_id, :grade_id)"
            ),
            {"id": need_id, "company_id": company_id, "specialization_id": specialization_id, "grade_id": grade_id, "team": values["team"], "role": values["role"]},
        )
    else:
        db.execute(
            text(
                "UPDATE hiring_need SET team = :team, role = :role, specialization_id = :specialization_id, "
                "grade_id = :grade_id, updated_at = CURRENT_TIMESTAMP WHERE id = :id AND company_id = :company_id"
            ),
            {"id": need_id, "company_id": company_id, "specialization_id": specialization_id, "grade_id": grade_id, "team": values["team"], "role": values["role"]},
        )
        db.execute(text("DELETE FROM hiring_need_skill WHERE hiring_need_id = :id"), {"id": need_id})
    db.execute(
        text(
            "INSERT INTO hiring_need_skill (hiring_need_id, skill_id, preference) "
            "SELECT :need_id, sk.id, :preference FROM skill sk WHERE sk.slug IN :slugs"
        ).bindparams(bindparam("slugs", expanding=True)),
        {
            "need_id": need_id,
            "preference": "required",
            "slugs": tuple(values["required_skills"]),
        },
    )
    db.execute(
        text(
            "INSERT INTO hiring_need_skill (hiring_need_id, skill_id, preference) "
            "SELECT :need_id, sk.id, :preference FROM skill sk WHERE sk.slug IN :slugs"
        ).bindparams(bindparam("slugs", expanding=True)),
        {
            "need_id": need_id,
            "preference": "preferred",
            "slugs": tuple(values["preferred_skills"]),
        },
    )
    db.commit()
    return _need_response(db, need_id)


def get_hiring_need(db: Session, principal: Principal) -> dict[str, Any] | None:
    _, company_id = _ensure_company(db, principal)
    need_id = db.execute(
        text("SELECT id FROM hiring_need WHERE company_id = :company_id"),
        {"company_id": company_id},
    ).scalar_one_or_none()
    return _need_response(db, need_id) if need_id else None


def create_hiring_need(db: Session, principal: Principal, payload: dict[str, Any]) -> dict[str, Any]:
    _, company_id = _ensure_company(db, principal)
    if db.execute(text("SELECT 1 FROM hiring_need WHERE company_id = :company_id"), {"company_id": company_id}).scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="hiring_need_already_exists")
    return _write_need(db, company_id, _payload_values(payload))


def update_hiring_need(db: Session, principal: Principal, payload: dict[str, Any]) -> dict[str, Any]:
    _, company_id = _ensure_company(db, principal)
    need_id = db.execute(
        text("SELECT id FROM hiring_need WHERE company_id = :company_id"),
        {"company_id": company_id},
    ).scalar_one_or_none()
    if need_id is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="hiring_need_not_found")
    current = _need_response(db, need_id)
    return _write_need(db, company_id, _payload_values(payload, current), need_id)
