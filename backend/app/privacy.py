"""Candidate privacy and consent use cases.

This module owns consent state transitions and persistence details. It stores
policy provenance and non-PII audit metadata, while protected profile data
remains outside employer-facing APIs.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from uuid import uuid4

from fastapi import HTTPException, status
from sqlalchemy import text
from sqlalchemy.orm import Session

from .auth import Principal, sync_identity
from .config import Settings

CONSENT_SOURCE = "web"


@dataclass(frozen=True)
class PrivacyState:
    processing_consent: bool
    processing_consent_version: str | None
    processing_consent_at: datetime | None
    publication_consent: bool
    publication_consent_version: str | None
    publication_consent_at: datetime | None
    discoverable: bool


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


def _row_state(row) -> PrivacyState:
    return PrivacyState(
        processing_consent=row["processing_consent_version"] is not None,
        processing_consent_version=row["processing_consent_version"],
        processing_consent_at=row["processing_consent_at"],
        publication_consent=row["publication_consent_version"] is not None,
        publication_consent_version=row["publication_consent_version"],
        publication_consent_at=row["publication_consent_at"],
        discoverable=bool(row["is_discoverable"]),
    )


def get_privacy(db: Session, principal: Principal) -> PrivacyState:
    _, profile_id = _ensure_candidate_profile(db, principal)
    row = db.execute(
        text(
            "SELECT is_discoverable, processing_consent_version, processing_consent_at, "
            "publication_consent_version, publication_consent_at "
            "FROM candidate_profile WHERE id = :profile_id"
        ),
        {"profile_id": profile_id},
    ).mappings().one()
    return _row_state(row)


def _audit(db: Session, identity_id: str, event_type: str, details: dict[str, str | bool]) -> None:
    db.execute(
        text(
            "INSERT INTO audit_event (id, actor_identity_id, event_type, details) "
            "VALUES (:id, :actor_identity_id, :event_type, :details)"
        ),
        {
            "id": str(uuid4()),
            "actor_identity_id": identity_id,
            "event_type": event_type,
            "details": json.dumps(details, separators=(",", ":"), sort_keys=True),
        },
    )


def update_privacy(
    db: Session,
    principal: Principal,
    settings: Settings,
    *,
    processing_consent: bool | None,
    publication_consent: bool | None,
    discoverable: bool | None,
) -> PrivacyState:
    identity_id, profile_id = _ensure_candidate_profile(db, principal)
    row = db.execute(
        text(
            "SELECT is_discoverable, processing_consent_version, processing_consent_at, "
            "processing_consent_source, publication_consent_version, publication_consent_at, "
            "publication_consent_source FROM candidate_profile WHERE id = :profile_id"
        ),
        {"profile_id": profile_id},
    ).mappings().one()
    current = _row_state(row)
    next_processing = current.processing_consent if processing_consent is None else processing_consent
    next_publication = current.publication_consent if publication_consent is None else publication_consent
    next_discoverable = current.discoverable if discoverable is None else discoverable

    # A withdrawal cascades to dependent permissions when the caller omits
    # them; this makes the safe action a single checkbox change in the UI.
    if processing_consent is False and publication_consent is None:
        next_publication = False
        next_discoverable = False
    if publication_consent is False and discoverable is None:
        next_discoverable = False

    if next_publication and not next_processing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="processing_consent_required")
    if next_discoverable and not next_publication:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="publication_consent_required")
    if not next_processing:
        next_publication = False
        next_discoverable = False
    elif not next_publication:
        next_discoverable = False

    processing_changed = current.processing_consent != next_processing
    publication_changed = current.publication_consent != next_publication
    processing_version = (
        settings.privacy_policy_version if processing_changed else row["processing_consent_version"]
    ) if next_processing else None
    processing_at = (
        "CURRENT_TIMESTAMP" if processing_changed else "processing_consent_at"
    ) if next_processing else "NULL"
    processing_source = (
        CONSENT_SOURCE if processing_changed else row["processing_consent_source"]
    ) if next_processing else None
    publication_version = (
        settings.privacy_policy_version if publication_changed else row["publication_consent_version"]
    ) if next_publication else None
    publication_at = (
        "CURRENT_TIMESTAMP" if publication_changed else "publication_consent_at"
    ) if next_publication else "NULL"
    publication_source = (
        CONSENT_SOURCE if publication_changed else row["publication_consent_source"]
    ) if next_publication else None

    db.execute(
        text(
            "UPDATE candidate_profile SET is_discoverable = :discoverable, "
            "processing_consent_version = :processing_version, "
            "processing_consent_at = "
            + processing_at
            + ", processing_consent_source = :processing_source, "
            "publication_consent_version = :publication_version, publication_consent_at = "
            + publication_at
            + ", publication_consent_source = :publication_source, "
            "updated_at = CURRENT_TIMESTAMP WHERE id = :profile_id"
        ),
        {
            "discoverable": next_discoverable,
            "processing_version": processing_version,
            "processing_source": processing_source,
            "publication_version": publication_version,
            "publication_source": publication_source,
            "profile_id": profile_id,
        },
    )
    if current.processing_consent != next_processing:
        _audit(
            db,
            identity_id,
            "processing_consent_granted" if next_processing else "processing_consent_withdrawn",
            {"version": settings.privacy_policy_version, "source": CONSENT_SOURCE},
        )
    if current.publication_consent != next_publication:
        _audit(
            db,
            identity_id,
            "publication_consent_granted" if next_publication else "publication_consent_withdrawn",
            {"version": settings.privacy_policy_version, "source": CONSENT_SOURCE},
        )
    if current.discoverable != next_discoverable:
        _audit(db, identity_id, "discoverability_changed", {"enabled": next_discoverable})
    db.commit()
    return get_privacy(db, principal)


def request_export(db: Session, principal: Principal) -> tuple[str, str]:
    identity_id, _ = _ensure_candidate_profile(db, principal)
    request_id = str(uuid4())
    db.execute(
        text(
            "INSERT INTO privacy_request (id, identity_id, request_type, status) "
            "VALUES (:id, :identity_id, 'export', 'requested')"
        ),
        {"id": request_id, "identity_id": identity_id},
    )
    _audit(db, identity_id, "privacy_export_requested", {"request_type": "export"})
    db.commit()
    return request_id, "requested"
