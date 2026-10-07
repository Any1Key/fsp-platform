"""Employer-owned company profile use cases."""

from __future__ import annotations

from typing import Any
from uuid import uuid4

from fastapi import HTTPException, status
from sqlalchemy import text
from sqlalchemy.orm import Session

from .auth import Principal, sync_identity

COMPANY_FIELDS = (
    "name",
    "description",
    "industry",
    "website",
    "location",
    "public_contact_method",
)


def _ensure_company(db: Session, principal: Principal) -> tuple[str, str]:
    identity = sync_identity(db, principal)
    company_id = db.execute(
        text("SELECT id FROM company WHERE owner_identity_id = :identity_id"),
        {"identity_id": identity["id"]},
    ).scalar_one_or_none()
    if company_id is None:
        company_id = str(uuid4())
        db.execute(
            text("INSERT INTO company (id, owner_identity_id) VALUES (:id, :identity_id)"),
            {"id": company_id, "identity_id": identity["id"]},
        )
        db.commit()
    return identity["id"], company_id


def _company_row(db: Session, company_id: str):
    return db.execute(
        text(
            "SELECT id, name, description, industry, website, location, "
            "public_contact_method, created_at, updated_at FROM company WHERE id = :company_id"
        ),
        {"company_id": company_id},
    ).mappings().one()


def _public_company(row) -> dict[str, Any]:
    return {
        "id": row["id"],
        "name": row["name"],
        "description": row["description"],
        "industry": row["industry"],
        "website": row["website"],
        "location": row["location"],
        "public_contact_method": row["public_contact_method"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def get_company(db: Session, principal: Principal) -> dict[str, Any]:
    _, company_id = _ensure_company(db, principal)
    return _public_company(_company_row(db, company_id))


def update_company(
    db: Session,
    principal: Principal,
    changes: dict[str, Any],
) -> dict[str, Any]:
    _, company_id = _ensure_company(db, principal)
    current = _company_row(db, company_id)

    next_values = {field: current[field] for field in COMPANY_FIELDS}
    for field, value in changes.items():
        if field in next_values:
            if isinstance(value, str):
                value = value.strip() or None
            next_values[field] = value

    if not next_values["name"]:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="company_name_required")

    db.execute(
        text(
            "UPDATE company SET name = :name, description = :description, industry = :industry, "
            "website = :website, location = :location, public_contact_method = :public_contact_method, "
            "updated_at = CURRENT_TIMESTAMP WHERE id = :company_id"
        ),
        {**next_values, "company_id": company_id},
    )
    db.commit()
    return _public_company(_company_row(db, company_id))
