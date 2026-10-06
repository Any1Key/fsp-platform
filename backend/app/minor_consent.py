"""Private parent/legal-representative consent-document workflow."""

from __future__ import annotations

import hashlib
import os
from pathlib import Path
from typing import Any
from uuid import uuid4

from fastapi import HTTPException, UploadFile, status
from sqlalchemy import text
from sqlalchemy.orm import Session

from .auth import Principal, sync_identity
from .config import Settings
from .protected_candidate import MinorState, minor_state_for

ALLOWED_CONTENT_TYPE = "application/pdf"
DOCUMENT_STATUS_FOR_PUBLICATION = ("submitted", "approved")


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


def _minor_state(db: Session, profile_id: str, settings: Settings) -> MinorState:
    birth_date = db.execute(
        text("SELECT date_of_birth FROM candidate_profile WHERE id = :profile_id"),
        {"profile_id": profile_id},
    ).scalar_one()
    return minor_state_for(birth_date, adult_age_years=settings.adult_age_years)


def has_current_document(db: Session, profile_id: str) -> bool:
    return db.execute(
        text(
            "SELECT 1 FROM minor_consent_document "
            "WHERE candidate_profile_id = :profile_id "
            "AND status IN ('submitted', 'approved') "
            "ORDER BY uploaded_at DESC, id DESC LIMIT 1"
        ),
        {"profile_id": profile_id},
    ).scalar_one_or_none() is not None


def _current_document(db: Session, profile_id: str):
    return db.execute(
        text(
            "SELECT id, policy_version, original_filename, content_type, size_bytes, "
            "status, uploaded_at FROM minor_consent_document "
            "WHERE candidate_profile_id = :profile_id AND status != 'replaced' "
            "ORDER BY uploaded_at DESC, id DESC LIMIT 1"
        ),
        {"profile_id": profile_id},
    ).mappings().one_or_none()


def _public_document(row) -> dict[str, Any] | None:
    if row is None:
        return None
    return {
        "id": row["id"],
        "policy_version": row["policy_version"],
        "original_filename": row["original_filename"],
        "content_type": row["content_type"],
        "size_bytes": row["size_bytes"],
        "status": row["status"],
        "uploaded_at": row["uploaded_at"],
    }


def get_document_status(db: Session, principal: Principal, settings: Settings) -> dict[str, Any]:
    _, profile_id = _ensure_candidate_profile(db, principal)
    state = _minor_state(db, profile_id, settings)
    return {
        "minor_state": state,
        "required": state == "minor",
        "policy_version": settings.minor_consent_document_policy_version,
        "document": _public_document(_current_document(db, profile_id)),
    }


def _private_path(settings: Settings, storage_key: str) -> Path:
    root = Path(settings.private_storage_dir).resolve()
    root.mkdir(mode=0o700, parents=True, exist_ok=True)
    path = (root / storage_key).resolve()
    if path.parent != root:
        raise HTTPException(status_code=500, detail="private_storage_invalid")
    return path


def _read_pdf(upload: UploadFile, settings: Settings) -> tuple[str, bytes]:
    filename = (upload.filename or "").strip()
    safe_filename = Path(filename).name
    if not safe_filename or len(safe_filename) > 255 or not safe_filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=422, detail="minor_document_invalid_filename")
    if upload.content_type != ALLOWED_CONTENT_TYPE:
        raise HTTPException(status_code=422, detail="minor_document_invalid_type")
    content = upload.file.read(settings.minor_consent_document_max_bytes + 1)
    if len(content) > settings.minor_consent_document_max_bytes:
        raise HTTPException(status_code=422, detail="minor_document_too_large")
    if not content.startswith(b"%PDF-"):
        raise HTTPException(status_code=422, detail="minor_document_invalid_pdf")
    return safe_filename, content


def _audit(db: Session, identity_id: str, event_type: str, document_id: str, status_value: str) -> None:
    import json

    db.execute(
        text(
            "INSERT INTO audit_event (id, actor_identity_id, event_type, details) "
            "VALUES (:id, :actor_identity_id, :event_type, :details)"
        ),
        {
            "id": str(uuid4()),
            "actor_identity_id": identity_id,
            "event_type": event_type,
            "details": json.dumps(
                {"document_id": document_id, "status": status_value},
                separators=(",", ":"),
                sort_keys=True,
            ),
        },
    )


def upload_document(
    db: Session,
    principal: Principal,
    settings: Settings,
    upload: UploadFile,
) -> dict[str, Any]:
    identity_id, profile_id = _ensure_candidate_profile(db, principal)
    current_state = _minor_state(db, profile_id, settings)
    if current_state != "minor":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="minor_document_only_for_minor")
    consent = db.execute(
        text("SELECT processing_consent_version FROM candidate_profile WHERE id = :profile_id"),
        {"profile_id": profile_id},
    ).scalar_one()
    if consent is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="minor_document_processing_consent_required",
        )

    safe_filename, content = _read_pdf(upload, settings)
    document_id = str(uuid4())
    storage_key = f"{document_id}.pdf"
    destination = _private_path(settings, storage_key)
    try:
        with destination.open("xb") as stored:
            stored.write(content)
        os.chmod(destination, 0o600)
        previous = db.execute(
            text(
                "SELECT id FROM minor_consent_document "
                "WHERE candidate_profile_id = :profile_id AND status != 'replaced'"
            ),
            {"profile_id": profile_id},
        ).scalars().all()
        for previous_id in previous:
            db.execute(
                text("UPDATE minor_consent_document SET status = 'replaced' WHERE id = :id"),
                {"id": previous_id},
            )
            _audit(db, identity_id, "minor_consent_document_replaced", previous_id, "replaced")
        db.execute(
            text(
                "INSERT INTO minor_consent_document "
                "(id, candidate_profile_id, policy_version, original_filename, content_type, "
                "size_bytes, sha256, storage_key, status) VALUES "
                "(:id, :profile_id, :policy_version, :original_filename, :content_type, "
                ":size_bytes, :sha256, :storage_key, 'submitted')"
            ),
            {
                "id": document_id,
                "profile_id": profile_id,
                "policy_version": settings.minor_consent_document_policy_version,
                "original_filename": safe_filename,
                "content_type": ALLOWED_CONTENT_TYPE,
                "size_bytes": len(content),
                "sha256": hashlib.sha256(content).hexdigest(),
                "storage_key": storage_key,
            },
        )
        _audit(db, identity_id, "minor_consent_document_uploaded", document_id, "submitted")
        db.commit()
    except Exception:
        db.rollback()
        destination.unlink(missing_ok=True)
        raise
    return get_document_status(db, principal, settings)


def revoke_publication_if_minor_document_missing(
    db: Session,
    *,
    identity_id: str,
    profile_id: str,
    state: MinorState,
) -> None:
    """Keep discoverability safe when a saved DOB changes to minor."""

    if state != "minor" or has_current_document(db, profile_id):
        return
    row = db.execute(
        text(
            "SELECT is_discoverable, publication_consent_version "
            "FROM candidate_profile WHERE id = :profile_id"
        ),
        {"profile_id": profile_id},
    ).mappings().one()
    if row["publication_consent_version"] is not None:
        db.execute(
            text(
                "UPDATE candidate_profile SET is_discoverable = FALSE, "
                "publication_consent_version = NULL, publication_consent_at = NULL, "
                "publication_consent_source = NULL, updated_at = CURRENT_TIMESTAMP "
                "WHERE id = :profile_id"
            ),
            {"profile_id": profile_id},
        )
        _audit(db, identity_id, "publication_consent_withdrawn", "minor-document-required", "withdrawn")
    elif row["is_discoverable"]:
        db.execute(
            text("UPDATE candidate_profile SET is_discoverable = FALSE WHERE id = :profile_id"),
            {"profile_id": profile_id},
        )
    if row["is_discoverable"]:
        _audit(db, identity_id, "discoverability_changed", "minor-document-required", "withdrawn")
