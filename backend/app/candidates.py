"""Candidate-owned profile use cases.

The profile boundary intentionally contains professional self-description only. Identity
email, contact details, DOB/minor state, consent metadata, assessment results and resume
documents are owned by separate boundaries and are not returned from these use cases.
"""

from __future__ import annotations

import json
from typing import Any
from uuid import uuid4

from fastapi import HTTPException, status
from sqlalchemy import text
from sqlalchemy.orm import Session

from .auth import Principal, sync_identity


def _ensure_candidate_profile(db: Session, principal: Principal) -> tuple[str, str]:
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
    return identity["id"], profile_id


def _json_value(value: Any, default: Any) -> Any:
    if value is None:
        return default
    if isinstance(value, str):
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return default
    return value


def _profile_row(db: Session, profile_id: str):
    return db.execute(
        text(
            "SELECT id, display_name, headline, location, summary, experience, preferences, "
            "processing_consent_version, updated_at FROM candidate_profile "
            "WHERE id = :profile_id"
        ),
        {"profile_id": profile_id},
    ).mappings().one()


def _public_profile(row) -> dict[str, Any]:
    preferences = _json_value(row["preferences"], {})
    if not isinstance(preferences, dict):
        preferences = {}
    skills = preferences.get("skills", [])
    work_preferences = {key: value for key, value in preferences.items() if key != "skills"}
    return {
        "id": row["id"],
        "display_name": row["display_name"],
        "headline": row["headline"],
        "location": row["location"],
        "summary": row["summary"],
        "experience": _json_value(row["experience"], []),
        "skills": skills if isinstance(skills, list) else [],
        "work_preferences": work_preferences,
        "updated_at": row["updated_at"],
    }


def get_profile(db: Session, principal: Principal) -> dict[str, Any]:
    _, profile_id = _ensure_candidate_profile(db, principal)
    return _public_profile(_profile_row(db, profile_id))


def update_profile(
    db: Session,
    principal: Principal,
    changes: dict[str, Any],
) -> dict[str, Any]:
    _, profile_id = _ensure_candidate_profile(db, principal)
    current = _profile_row(db, profile_id)
    if current["processing_consent_version"] is None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="processing_consent_required")

    current_preferences = _json_value(current["preferences"], {})
    if not isinstance(current_preferences, dict):
        current_preferences = {}
    next_preferences = dict(current_preferences)
    if "skills" in changes:
        next_preferences["skills"] = changes.pop("skills")
    if "work_preferences" in changes:
        work_preferences = changes.pop("work_preferences")
        if work_preferences is None:
            next_preferences = {"skills": next_preferences.get("skills", [])}
        else:
            next_preferences.update(work_preferences)

    update_values = {
        "display_name": changes.get("display_name", current["display_name"]),
        "headline": changes.get("headline", current["headline"]),
        "location": changes.get("location", current["location"]),
        "summary": changes.get("summary", current["summary"]),
        "experience": json.dumps(
            changes.get("experience", _json_value(current["experience"], [])),
            ensure_ascii=False,
            separators=(",", ":"),
        ),
        "preferences": json.dumps(next_preferences, ensure_ascii=False, separators=(",", ":")),
        "profile_id": profile_id,
    }
    db.execute(
        text(
            "UPDATE candidate_profile SET display_name = :display_name, headline = :headline, "
            "location = :location, summary = :summary, experience = :experience, "
            "preferences = :preferences, updated_at = CURRENT_TIMESTAMP WHERE id = :profile_id"
        ),
        update_values,
    )
    db.commit()
    return _public_profile(_profile_row(db, profile_id))
