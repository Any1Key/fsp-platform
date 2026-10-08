"""Employer-owned vacancy lifecycle and salary validation."""

from __future__ import annotations

from typing import Any
from uuid import uuid4

from fastapi import HTTPException, status
from sqlalchemy import text
from sqlalchemy.orm import Session

from .auth import Principal
from .companies import _ensure_company

VACANCY_FIELDS = (
    "title",
    "description",
    "location",
    "work_mode",
    "employment_type",
    "salary_min_rub",
    "salary_max_rub",
    "specialization",
    "grade",
)


def _clean_text(value: Any) -> Any:
    return value.strip() if isinstance(value, str) else value


def _validate_salary(salary_min_rub: Any, salary_max_rub: Any) -> None:
    if (
        not isinstance(salary_min_rub, int)
        or not isinstance(salary_max_rub, int)
        or salary_min_rub <= 0
        or salary_max_rub <= 0
        or salary_min_rub > salary_max_rub
    ):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="vacancy_salary_invalid",
        )


def _taxonomy_ids(
    db: Session,
    *,
    specialization: str | None,
    grade: str | None,
) -> tuple[str | None, str | None]:
    specialization_id = None
    grade_id = None
    if specialization is not None:
        row = db.execute(
            text(
                "SELECT id FROM specialization "
                "WHERE slug = :slug AND active = :active"
            ),
            {"slug": specialization, "active": True},
        ).scalar_one_or_none()
        if row is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="vacancy_taxonomy_invalid",
            )
        specialization_id = row
    if grade is not None:
        row = db.execute(
            text("SELECT id FROM grade WHERE slug = :slug"),
            {"slug": grade},
        ).scalar_one_or_none()
        if row is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="vacancy_taxonomy_invalid",
            )
        grade_id = row
    return specialization_id, grade_id


def _vacancy_row(db: Session, vacancy_id: str, company_id: str):
    return db.execute(
        text(
            "SELECT v.id, v.company_id, v.title, v.description, v.location, "
            "v.work_mode, v.employment_type, v.salary_min_rub, v.salary_max_rub, "
            "v.status, v.published_at, v.created_at, v.updated_at, "
            "s.slug AS specialization_slug, s.name AS specialization_name, "
            "g.slug AS grade_slug, g.name AS grade_name "
            "FROM vacancy v "
            "LEFT JOIN specialization s ON s.id = v.specialization_id "
            "LEFT JOIN grade g ON g.id = v.grade_id "
            "WHERE v.id = :vacancy_id AND v.company_id = :company_id"
        ),
        {"vacancy_id": vacancy_id, "company_id": company_id},
    ).mappings().one_or_none()


def _public_vacancy(row) -> dict[str, Any]:
    return {
        "id": row["id"],
        "title": row["title"],
        "description": row["description"],
        "location": row["location"],
        "work_mode": row["work_mode"],
        "employment_type": row["employment_type"],
        "salary_min_rub": row["salary_min_rub"],
        "salary_max_rub": row["salary_max_rub"],
        "status": row["status"],
        "published_at": row["published_at"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
        "specialization": (
            {"slug": row["specialization_slug"], "name": row["specialization_name"]}
            if row["specialization_slug"] is not None
            else None
        ),
        "grade": (
            {"slug": row["grade_slug"], "name": row["grade_name"]}
            if row["grade_slug"] is not None
            else None
        ),
    }


def _company_id(db: Session, principal: Principal) -> str:
    _, company_id = _ensure_company(db, principal)
    return company_id


def _values(
    payload: dict[str, Any],
    *,
    current: dict[str, Any] | None = None,
) -> dict[str, Any]:
    values = {
        "title": current["title"] if current else None,
        "description": current["description"] if current else None,
        "location": current["location"] if current else None,
        "work_mode": current["work_mode"] if current else None,
        "employment_type": current["employment_type"] if current else None,
        "salary_min_rub": current["salary_min_rub"] if current else None,
        "salary_max_rub": current["salary_max_rub"] if current else None,
        "specialization": current["specialization"]["slug"] if current and current["specialization"] else None,
        "grade": current["grade"]["slug"] if current and current["grade"] else None,
    }
    for field, value in payload.items():
        if field in VACANCY_FIELDS:
            values[field] = _clean_text(value)
    if not values["title"] or not values["description"]:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="vacancy_fields_required",
        )
    _validate_salary(values["salary_min_rub"], values["salary_max_rub"])
    return values


def _write_vacancy(
    db: Session,
    company_id: str,
    values: dict[str, Any],
    *,
    vacancy_id: str | None = None,
) -> dict[str, Any]:
    specialization_id, grade_id = _taxonomy_ids(
        db,
        specialization=values["specialization"],
        grade=values["grade"],
    )
    if vacancy_id is None:
        vacancy_id = str(uuid4())
        db.execute(
            text(
                "INSERT INTO vacancy "
                "(id, company_id, title, description, location, work_mode, employment_type, "
                "salary_min_rub, salary_max_rub, specialization_id, grade_id) "
                "VALUES (:id, :company_id, :title, :description, :location, :work_mode, "
                ":employment_type, :salary_min_rub, :salary_max_rub, :specialization_id, :grade_id)"
            ),
            {**values, "id": vacancy_id, "company_id": company_id, "specialization_id": specialization_id, "grade_id": grade_id},
        )
    else:
        db.execute(
            text(
                "UPDATE vacancy SET title = :title, description = :description, location = :location, "
                "work_mode = :work_mode, employment_type = :employment_type, salary_min_rub = :salary_min_rub, "
                "salary_max_rub = :salary_max_rub, specialization_id = :specialization_id, grade_id = :grade_id, "
                "updated_at = CURRENT_TIMESTAMP WHERE id = :id AND company_id = :company_id"
            ),
            {**values, "id": vacancy_id, "company_id": company_id, "specialization_id": specialization_id, "grade_id": grade_id},
        )
    db.commit()
    row = _vacancy_row(db, vacancy_id, company_id)
    assert row is not None
    return _public_vacancy(row)


def list_vacancies(db: Session, principal: Principal) -> list[dict[str, Any]]:
    company_id = _company_id(db, principal)
    rows = db.execute(
        text(
            "SELECT v.id FROM vacancy v WHERE v.company_id = :company_id "
            "ORDER BY CASE v.status WHEN 'published' THEN 0 WHEN 'draft' THEN 1 ELSE 2 END, v.updated_at DESC"
        ),
        {"company_id": company_id},
    ).scalars()
    return [_public_vacancy(_vacancy_row(db, vacancy_id, company_id)) for vacancy_id in rows]


def get_vacancy(db: Session, principal: Principal, vacancy_id: str) -> dict[str, Any]:
    company_id = _company_id(db, principal)
    row = _vacancy_row(db, vacancy_id, company_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="vacancy_not_found")
    return _public_vacancy(row)


def create_vacancy(db: Session, principal: Principal, payload: dict[str, Any]) -> dict[str, Any]:
    return _write_vacancy(db, _company_id(db, principal), _values(payload))


def update_vacancy(
    db: Session,
    principal: Principal,
    vacancy_id: str,
    payload: dict[str, Any],
) -> dict[str, Any]:
    company_id = _company_id(db, principal)
    current = _vacancy_row(db, vacancy_id, company_id)
    if current is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="vacancy_not_found")
    current_public = _public_vacancy(current)
    return _write_vacancy(db, company_id, _values(payload, current=current_public), vacancy_id=vacancy_id)


def publish_vacancy(db: Session, principal: Principal, vacancy_id: str) -> dict[str, Any]:
    company_id = _company_id(db, principal)
    current = _vacancy_row(db, vacancy_id, company_id)
    if current is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="vacancy_not_found")
    if current["status"] == "closed":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="vacancy_closed")
    db.execute(
        text(
            "UPDATE vacancy SET status = 'published', published_at = COALESCE(published_at, CURRENT_TIMESTAMP), "
            "updated_at = CURRENT_TIMESTAMP WHERE id = :id AND company_id = :company_id"
        ),
        {"id": vacancy_id, "company_id": company_id},
    )
    db.commit()
    return get_vacancy(db, principal, vacancy_id)


def close_vacancy(db: Session, principal: Principal, vacancy_id: str) -> dict[str, Any]:
    company_id = _company_id(db, principal)
    current = _vacancy_row(db, vacancy_id, company_id)
    if current is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="vacancy_not_found")
    db.execute(
        text(
            "UPDATE vacancy SET status = 'closed', updated_at = CURRENT_TIMESTAMP "
            "WHERE id = :id AND company_id = :company_id"
        ),
        {"id": vacancy_id, "company_id": company_id},
    )
    db.commit()
    return get_vacancy(db, principal, vacancy_id)
