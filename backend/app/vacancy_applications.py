"""Candidate-facing published vacancies and application history."""

from __future__ import annotations

from typing import Any
from uuid import uuid4

from fastapi import HTTPException, status
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .auth import Principal, sync_identity


def _candidate_profile_id(db: Session, principal: Principal) -> str:
    identity = sync_identity(db, principal)
    profile_id = db.execute(
        text("SELECT id FROM candidate_profile WHERE identity_id = :identity_id"),
        {"identity_id": identity["id"]},
    ).scalar_one_or_none()
    if profile_id is None:
        profile_id = str(uuid4())
        db.execute(
            text("INSERT INTO candidate_profile (id, identity_id) VALUES (:id, :identity_id)"),
            {"id": profile_id, "identity_id": identity["id"]},
        )
        db.commit()
    return profile_id


def _candidate_profile_for_application(db: Session, principal: Principal) -> str:
    profile_id = _candidate_profile_id(db, principal)
    processing_consent = db.execute(
        text(
            "SELECT processing_consent_version FROM candidate_profile "
            "WHERE id = :profile_id"
        ),
        {"profile_id": profile_id},
    ).scalar_one()
    if processing_consent is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="processing_consent_required",
        )
    return profile_id


def _taxonomy(row, prefix: str) -> dict[str, str] | None:
    slug = row[f"{prefix}_slug"]
    return {"slug": slug, "name": row[f"{prefix}_name"]} if slug else None


def _vacancy_summary(row) -> dict[str, Any]:
    return {
        "id": row["vacancy_id"],
        "title": row["title"],
        "description": row["description"],
        "company_name": row["company_name"] or "Работодатель",
        "location": row["location"],
        "work_mode": row["work_mode"],
        "employment_type": row["employment_type"],
        "salary_min_rub": row["salary_min_rub"],
        "salary_max_rub": row["salary_max_rub"],
        "specialization": _taxonomy(row, "specialization"),
        "grade": _taxonomy(row, "grade"),
        "vacancy_status": row["vacancy_status"],
        "published_at": row["published_at"],
    }


def _published_vacancy_rows(db: Session, profile_id: str):
    return db.execute(
        text(
            "SELECT v.id AS vacancy_id, v.title, v.description, c.name AS company_name, "
            "v.location, v.work_mode, v.employment_type, v.salary_min_rub, v.salary_max_rub, "
            "v.status AS vacancy_status, v.published_at, "
            "s.slug AS specialization_slug, s.name AS specialization_name, "
            "g.slug AS grade_slug, g.name AS grade_name, "
            "a.id AS application_id, a.status AS application_status, a.created_at AS applied_at "
            "FROM vacancy v JOIN company c ON c.id = v.company_id "
            "LEFT JOIN specialization s ON s.id = v.specialization_id "
            "LEFT JOIN grade g ON g.id = v.grade_id "
            "LEFT JOIN application a ON a.vacancy_id = v.id "
            "AND a.candidate_profile_id = :profile_id "
            "WHERE v.status = 'published' "
            "ORDER BY v.published_at DESC, v.created_at DESC"
        ),
        {"profile_id": profile_id},
    ).mappings().all()


def _application_row(db: Session, profile_id: str, application_id: str):
    return db.execute(
        text(
            "SELECT a.id AS application_id, a.status AS application_status, "
            "a.created_at AS applied_at, a.updated_at, v.id AS vacancy_id, v.title, "
            "v.description, c.name AS company_name, v.location, v.work_mode, "
            "v.employment_type, v.salary_min_rub, v.salary_max_rub, "
            "v.status AS vacancy_status, v.published_at, "
            "s.slug AS specialization_slug, s.name AS specialization_name, "
            "g.slug AS grade_slug, g.name AS grade_name "
            "FROM application a JOIN vacancy v ON v.id = a.vacancy_id "
            "JOIN company c ON c.id = v.company_id "
            "LEFT JOIN specialization s ON s.id = v.specialization_id "
            "LEFT JOIN grade g ON g.id = v.grade_id "
            "WHERE a.id = :application_id AND a.candidate_profile_id = :profile_id"
        ),
        {"application_id": application_id, "profile_id": profile_id},
    ).mappings().one_or_none()


def _application_public(db: Session, row) -> dict[str, Any]:
    history = db.execute(
        text(
            "SELECT status, changed_at FROM application_status_history "
            "WHERE application_id = :application_id ORDER BY changed_at ASC, id ASC"
        ),
        {"application_id": row["application_id"]},
    ).mappings().all()
    return {
        "id": row["application_id"],
        "status": row["application_status"],
        "applied_at": row["applied_at"],
        "updated_at": row["updated_at"],
        "vacancy": _vacancy_summary(row),
        "status_history": [
            {"status": item["status"], "changed_at": item["changed_at"]}
            for item in history
        ],
    }


def list_published_vacancies(db: Session, principal: Principal) -> list[dict[str, Any]]:
    profile_id = _candidate_profile_id(db, principal)
    return [
        {
            **_vacancy_summary(row),
            "application_id": row["application_id"],
            "application_status": row["application_status"],
            "applied_at": row["applied_at"],
        }
        for row in _published_vacancy_rows(db, profile_id)
    ]


def apply_to_vacancy(
    db: Session,
    principal: Principal,
    vacancy_id: str,
) -> dict[str, Any]:
    profile_id = _candidate_profile_for_application(db, principal)
    vacancy = db.execute(
        text("SELECT id, status FROM vacancy WHERE id = :vacancy_id"),
        {"vacancy_id": vacancy_id},
    ).mappings().one_or_none()
    if vacancy is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="vacancy_not_found")
    if vacancy["status"] != "published":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="vacancy_not_published",
        )
    existing = db.execute(
        text(
            "SELECT id FROM application WHERE vacancy_id = :vacancy_id "
            "AND candidate_profile_id = :profile_id"
        ),
        {"vacancy_id": vacancy_id, "profile_id": profile_id},
    ).scalar_one_or_none()
    if existing is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="application_exists")

    application_id = str(uuid4())
    try:
        db.execute(
            text(
                "INSERT INTO application (id, vacancy_id, candidate_profile_id, status) "
                "VALUES (:id, :vacancy_id, :profile_id, 'submitted')"
            ),
            {"id": application_id, "vacancy_id": vacancy_id, "profile_id": profile_id},
        )
        db.execute(
            text(
                "INSERT INTO application_status_history (id, application_id, status) "
                "VALUES (:id, :application_id, 'submitted')"
            ),
            {"id": str(uuid4()), "application_id": application_id},
        )
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="application_exists") from exc
    row = _application_row(db, profile_id, application_id)
    assert row is not None
    return _application_public(db, row)


def list_candidate_applications(db: Session, principal: Principal) -> list[dict[str, Any]]:
    profile_id = _candidate_profile_id(db, principal)
    rows = db.execute(
        text(
            "SELECT a.id AS application_id, a.status AS application_status, "
            "a.created_at AS applied_at, a.updated_at, v.id AS vacancy_id, v.title, "
            "v.description, c.name AS company_name, v.location, v.work_mode, "
            "v.employment_type, v.salary_min_rub, v.salary_max_rub, "
            "v.status AS vacancy_status, v.published_at, "
            "s.slug AS specialization_slug, s.name AS specialization_name, "
            "g.slug AS grade_slug, g.name AS grade_name "
            "FROM application a JOIN vacancy v ON v.id = a.vacancy_id "
            "JOIN company c ON c.id = v.company_id "
            "LEFT JOIN specialization s ON s.id = v.specialization_id "
            "LEFT JOIN grade g ON g.id = v.grade_id "
            "WHERE a.candidate_profile_id = :profile_id "
            "ORDER BY a.updated_at DESC, a.created_at DESC"
        ),
        {"profile_id": profile_id},
    ).mappings().all()
    return [_application_public(db, row) for row in rows]
