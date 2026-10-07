"""Reverse-recruitment invitations and the accepted-match boundary."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any, Literal
from uuid import uuid4

from fastapi import HTTPException, status
from sqlalchemy import text
from sqlalchemy.orm import Session

from .assessments import AssessmentService
from .auth import Principal, sync_identity

InvitationAction = Literal["accepted", "declined"]


def _invitation_row(db: Session, invitation_id: str):
    return db.execute(
        text(
            "SELECT i.id, i.employer_identity_id, i.company_id, i.candidate_profile_id, "
            "i.salary_min_rub, i.salary_max_rub, i.offer_description, "
            "i.company_name_snapshot, i.contact_method_snapshot, i.status, "
            "i.created_at, i.updated_at, i.responded_at, i.matched_at, i.contact_unlocked_at, "
            "cp.display_name AS candidate_display_name, tm.id AS match_id "
            "FROM invitation i "
            "JOIN candidate_profile cp ON cp.id = i.candidate_profile_id "
            "LEFT JOIN talent_match tm ON tm.invitation_id = i.id "
            "WHERE i.id = :invitation_id"
        ),
        {"invitation_id": invitation_id},
    ).mappings().one_or_none()


def _public_invitation(row) -> dict[str, Any]:
    return {
        "id": row["id"],
        "status": row["status"],
        "salary_min_rub": row["salary_min_rub"],
        "salary_max_rub": row["salary_max_rub"],
        "offer_description": row["offer_description"],
        "company": {
            "id": row["company_id"],
            "name": row["company_name_snapshot"],
            "contact_method": row["contact_method_snapshot"],
        },
        "candidate": {
            "id": row["candidate_profile_id"],
            "display_name": row["candidate_display_name"] or "Unnamed candidate",
        },
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
        "responded_at": row["responded_at"],
        "matched_at": row["matched_at"],
        "contact_unlocked_at": row["contact_unlocked_at"],
        "match_id": row["match_id"],
    }


def _require_salary(salary_min_rub: int, salary_max_rub: int) -> None:
    if salary_min_rub <= 0 or salary_max_rub <= 0 or salary_min_rub > salary_max_rub:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="invitation_salary_invalid",
        )


def _employer_company(db: Session, principal: Principal) -> tuple[dict[str, Any], dict[str, Any]]:
    identity = sync_identity(db, principal)
    company = db.execute(
        text(
            "SELECT id, name, public_contact_method FROM company "
            "WHERE owner_identity_id = :identity_id"
        ),
        {"identity_id": identity["id"]},
    ).mappings().one_or_none()
    if company is None or not company["name"] or not company["public_contact_method"]:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="invitation_company_contact_required",
        )
    return identity, company


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


def create_invitation(
    db: Session,
    principal: Principal,
    *,
    candidate_profile_id: str,
    salary_min_rub: int,
    salary_max_rub: int,
    offer_description: str,
    assessment_service: AssessmentService,
) -> dict[str, Any]:
    """Create a salary-bearing offer addressed to a discoverable candidate."""

    _require_salary(salary_min_rub, salary_max_rub)
    if not offer_description.strip():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="invitation_offer_required",
        )
    identity, company = _employer_company(db, principal)
    candidate = db.execute(
        text(
            "SELECT cp.id, ui.keycloak_sub FROM candidate_profile cp "
            "JOIN user_identity ui ON ui.id = cp.identity_id "
            "WHERE cp.id = :candidate_profile_id AND ui.role = 'candidate' "
            "AND cp.is_discoverable = :discoverable "
            "AND cp.publication_consent_version IS NOT NULL"
        ),
        {"candidate_profile_id": candidate_profile_id, "discoverable": True},
    ).mappings().one_or_none()
    if candidate is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="invitation_candidate_not_available")
    if not any(
        attempt.submitted and attempt.grade_state == "verified"
        for attempt in assessment_service.history_for(candidate["keycloak_sub"])
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="invitation_candidate_grade_not_confirmed",
        )

    duplicate = db.execute(
        text(
            "SELECT id FROM invitation WHERE employer_identity_id = :employer_identity_id "
            "AND candidate_profile_id = :candidate_profile_id AND status = 'pending'"
        ),
        {
            "employer_identity_id": identity["id"],
            "candidate_profile_id": candidate_profile_id,
        },
    ).scalar_one_or_none()
    if duplicate is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="invitation_already_pending")

    invitation_id = str(uuid4())
    db.execute(
        text(
            "INSERT INTO invitation ("
            "id, employer_identity_id, company_id, candidate_profile_id, salary_min_rub, "
            "salary_max_rub, offer_description, company_name_snapshot, contact_method_snapshot"
            ") VALUES ("
            ":id, :employer_identity_id, :company_id, :candidate_profile_id, :salary_min_rub, "
            ":salary_max_rub, :offer_description, :company_name_snapshot, :contact_method_snapshot"
            ")"
        ),
        {
            "id": invitation_id,
            "employer_identity_id": identity["id"],
            "company_id": company["id"],
            "candidate_profile_id": candidate_profile_id,
            "salary_min_rub": salary_min_rub,
            "salary_max_rub": salary_max_rub,
            "offer_description": offer_description.strip(),
            "company_name_snapshot": company["name"],
            "contact_method_snapshot": company["public_contact_method"],
        },
    )
    db.commit()
    return _public_invitation(_invitation_row(db, invitation_id))


def list_employer_invitations(db: Session, principal: Principal) -> list[dict[str, Any]]:
    identity = sync_identity(db, principal)
    rows = db.execute(
        text(
            "SELECT i.id FROM invitation i WHERE i.employer_identity_id = :identity_id "
            "ORDER BY i.created_at DESC, i.id DESC"
        ),
        {"identity_id": identity["id"]},
    ).scalars()
    return [_public_invitation(_invitation_row(db, invitation_id)) for invitation_id in rows]


def list_candidate_invitations(db: Session, principal: Principal) -> list[dict[str, Any]]:
    profile_id = _candidate_profile_id(db, principal)
    rows = db.execute(
        text(
            "SELECT i.id FROM invitation i WHERE i.candidate_profile_id = :profile_id "
            "ORDER BY i.created_at DESC, i.id DESC"
        ),
        {"profile_id": profile_id},
    ).scalars()
    return [_public_invitation(_invitation_row(db, invitation_id)) for invitation_id in rows]


def respond_to_invitation(
    db: Session,
    principal: Principal,
    invitation_id: str,
    action: InvitationAction,
) -> dict[str, Any]:
    profile_id = _candidate_profile_id(db, principal)
    row = db.execute(
        text(
            "SELECT i.id, i.employer_identity_id, i.candidate_profile_id, i.status, "
            "cp.identity_id AS candidate_identity_id "
            "FROM invitation i JOIN candidate_profile cp ON cp.id = i.candidate_profile_id "
            "WHERE i.id = :invitation_id AND i.candidate_profile_id = :profile_id"
        ),
        {"invitation_id": invitation_id, "profile_id": profile_id},
    ).mappings().one_or_none()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="invitation_not_found")

    if row["status"] == action:
        return _public_invitation(_invitation_row(db, invitation_id))
    if row["status"] != "pending":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="invitation_not_pending")

    now = datetime.now(UTC)
    if action == "declined":
        db.execute(
            text(
                "UPDATE invitation SET status = 'declined', responded_at = :now, "
                "updated_at = CURRENT_TIMESTAMP WHERE id = :invitation_id"
            ),
            {"now": now, "invitation_id": invitation_id},
        )
        db.commit()
        return _public_invitation(_invitation_row(db, invitation_id))

    match_id = str(uuid4())
    db.execute(
        text(
            "UPDATE invitation SET status = 'accepted', responded_at = :now, matched_at = :now, "
            "contact_unlocked_at = :now, updated_at = CURRENT_TIMESTAMP WHERE id = :invitation_id"
        ),
        {"now": now, "invitation_id": invitation_id},
    )
    db.execute(
        text(
            "INSERT INTO talent_match (id, invitation_id, employer_identity_id, candidate_profile_id, "
            "created_at, contact_unlocked_at) VALUES "
            "(:id, :invitation_id, :employer_identity_id, :candidate_profile_id, :now, :now)"
        ),
        {
            "id": match_id,
            "invitation_id": invitation_id,
            "employer_identity_id": row["employer_identity_id"],
            "candidate_profile_id": profile_id,
            "now": now,
        },
    )
    event_payload = {"invitation_id": invitation_id, "match_id": match_id}
    for event_type in ("MATCH_CREATED", "CONTACT_UNLOCKED"):
        db.execute(
            text(
                "INSERT INTO domain_event "
                "(id, event_type, aggregate_type, aggregate_id, payload) "
                "VALUES (:id, :event_type, 'talent_match', :aggregate_id, :payload)"
            ),
            {
                "id": str(uuid4()),
                "event_type": event_type,
                "aggregate_id": match_id,
                "payload": json.dumps(event_payload, separators=(",", ":")),
            },
        )
        db.execute(
            text(
                "INSERT INTO audit_event (id, actor_identity_id, event_type, details) "
                "VALUES (:id, :actor_identity_id, :event_type, :details)"
            ),
            {
                "id": str(uuid4()),
                "actor_identity_id": row["candidate_identity_id"],
                "event_type": event_type.lower(),
                "details": json.dumps(event_payload, separators=(",", ":")),
            },
        )
    db.commit()
    return _public_invitation(_invitation_row(db, invitation_id))


def get_invitation_for_employer(db: Session, principal: Principal, invitation_id: str) -> dict[str, Any]:
    identity = sync_identity(db, principal)
    row = db.execute(
        text(
            "SELECT id FROM invitation WHERE id = :invitation_id "
            "AND employer_identity_id = :identity_id"
        ),
        {"invitation_id": invitation_id, "identity_id": identity["id"]},
    ).scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="invitation_not_found")
    return _public_invitation(_invitation_row(db, invitation_id))
