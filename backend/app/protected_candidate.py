"""Candidate-owned protected identity attributes.

Date of birth is stored separately from professional profile fields. Minor state
is derived on the server and is never accepted as client input or used as a
matching feature.
"""

from __future__ import annotations

import json
from datetime import date
from typing import Any, Literal
from uuid import uuid4

from fastapi import HTTPException, status
from sqlalchemy import text
from sqlalchemy.orm import Session

from .auth import Principal, sync_identity
from .config import Settings

MinorState = Literal["not_set", "minor", "adult"]


def _ensure_candidate_profile(db: Session, principal: Principal) -> str:
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


def _as_date(value: date | str | None) -> date | None:
    if value is None:
        return None
    if isinstance(value, date):
        return value
    return date.fromisoformat(value)


def minor_state_for(
    date_of_birth: date | str | None,
    *,
    adult_age_years: int,
    today: date | None = None,
) -> MinorState:
    """Derive age state without storing or exposing a computed age."""

    birth_date = _as_date(date_of_birth)
    if birth_date is None:
        return "not_set"
    current_date = today or date.today()
    try:
        adult_on = birth_date.replace(year=birth_date.year + adult_age_years)
    except ValueError:
        # A 29 February birthday reaches the threshold on 28 February in a
        # non-leap year, keeping the comparison deterministic across databases.
        adult_on = birth_date.replace(year=birth_date.year + adult_age_years, day=28)
    return "adult" if current_date >= adult_on else "minor"


def _response(date_of_birth: date | str | None, settings: Settings) -> dict[str, Any]:
    birth_date = _as_date(date_of_birth)
    return {
        "date_of_birth": birth_date,
        "minor_state": minor_state_for(birth_date, adult_age_years=settings.adult_age_years),
        "adult_age_years": settings.adult_age_years,
    }


def get_protected_profile(db: Session, principal: Principal, settings: Settings) -> dict[str, Any]:
    profile_id = _ensure_candidate_profile(db, principal)
    date_of_birth = db.execute(
        text("SELECT date_of_birth FROM candidate_profile WHERE id = :profile_id"),
        {"profile_id": profile_id},
    ).scalar_one()
    return _response(date_of_birth, settings)


def update_protected_profile(
    db: Session,
    principal: Principal,
    settings: Settings,
    *,
    date_of_birth: date | None,
) -> dict[str, Any]:
    profile_id = _ensure_candidate_profile(db, principal)
    current = db.execute(
        text(
            "SELECT date_of_birth, processing_consent_version "
            "FROM candidate_profile WHERE id = :profile_id"
        ),
        {"profile_id": profile_id},
    ).mappings().one()
    if current["processing_consent_version"] is None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="processing_consent_required")
    if date_of_birth is not None and date_of_birth > date.today():
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="date_of_birth_in_future")

    previous_state = minor_state_for(current["date_of_birth"], adult_age_years=settings.adult_age_years)
    next_state = minor_state_for(date_of_birth, adult_age_years=settings.adult_age_years)
    db.execute(
        text(
            "UPDATE candidate_profile SET date_of_birth = :date_of_birth, "
            "updated_at = CURRENT_TIMESTAMP WHERE id = :profile_id"
        ),
        {"date_of_birth": date_of_birth, "profile_id": profile_id},
    )
    if previous_state != next_state:
        identity_id = db.execute(
            text("SELECT identity_id FROM candidate_profile WHERE id = :profile_id"),
            {"profile_id": profile_id},
        ).scalar_one()
        db.execute(
            text(
                "INSERT INTO audit_event "
                "(id, actor_identity_id, event_type, details) "
                "VALUES (:id, :actor_identity_id, :event_type, :details)"
            ),
            {
                "id": str(uuid4()),
                "actor_identity_id": identity_id,
                "event_type": "protected_age_state_changed",
                "details": json.dumps(
                    {"from": previous_state, "to": next_state},
                    separators=(",", ":"),
                ),
            },
        )
    db.commit()
    return _response(date_of_birth, settings)
