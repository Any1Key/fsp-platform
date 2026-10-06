"""Candidate-owned private resume upload and review boundary."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any
from uuid import uuid4

from fastapi import HTTPException, UploadFile, status
from sqlalchemy import text
from sqlalchemy.orm import Session

from .auth import Principal, sync_identity
from .candidates import update_profile
from .config import Settings
from .resume_parser import ResumeParseError, parse_resume_pdf, unsupported_extraction

ALLOWED_CONTENT_TYPE = "application/pdf"


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


def _current_resume(db: Session, profile_id: str):
    return db.execute(
        text(
            "SELECT id, original_filename, content_type, size_bytes, status, uploaded_at "
            "FROM resume_document WHERE candidate_profile_id = :profile_id "
            "AND status = 'uploaded' ORDER BY uploaded_at DESC, id DESC LIMIT 1"
        ),
        {"profile_id": profile_id},
    ).mappings().one_or_none()


def _extraction(db: Session, document_id: str):
    return db.execute(
        text(
            "SELECT id, status, parser_version, fields, reviewed_fields, extracted_at, reviewed_at "
            "FROM resume_extraction WHERE resume_document_id = :document_id"
        ),
        {"document_id": document_id},
    ).mappings().one_or_none()


def _public_resume(row) -> dict[str, Any] | None:
    if row is None:
        return None
    return {
        "id": row["id"],
        "original_filename": row["original_filename"],
        "content_type": row["content_type"],
        "size_bytes": row["size_bytes"],
        "status": row["status"],
        "uploaded_at": row["uploaded_at"],
    }


def _public_extraction(row) -> dict[str, Any] | None:
    if row is None:
        return None
    fields = json.loads(row["fields"])
    return {
        "id": row["id"],
        "status": row["status"],
        "parser_version": row["parser_version"],
        "fields": fields.get("fields", {}),
        "text_available": fields.get("text_available", False),
        "extracted_at": row["extracted_at"],
        "reviewed_at": row["reviewed_at"],
    }


def get_resume(db: Session, principal: Principal) -> dict[str, Any]:
    _, profile_id = _ensure_candidate_profile(db, principal)
    document = _current_resume(db, profile_id)
    return {
        "document": _public_resume(document),
        "extraction": _public_extraction(_extraction(db, document["id"])) if document else None,
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
        raise HTTPException(status_code=422, detail="resume_invalid_filename")
    if upload.content_type != ALLOWED_CONTENT_TYPE:
        raise HTTPException(status_code=422, detail="resume_invalid_type")
    content = upload.file.read(settings.resume_max_bytes + 1)
    if len(content) > settings.resume_max_bytes:
        raise HTTPException(status_code=422, detail="resume_too_large")
    if not content.startswith(b"%PDF-"):
        raise HTTPException(status_code=422, detail="resume_invalid_pdf")
    return safe_filename, content


def _audit(db: Session, identity_id: str, event_type: str, document_id: str, status_value: str) -> None:
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


def upload_resume(
    db: Session,
    principal: Principal,
    settings: Settings,
    upload: UploadFile,
) -> dict[str, Any]:
    identity_id, profile_id = _ensure_candidate_profile(db, principal)
    consent = db.execute(
        text("SELECT processing_consent_version FROM candidate_profile WHERE id = :profile_id"),
        {"profile_id": profile_id},
    ).scalar_one()
    if consent is None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="processing_consent_required")

    safe_filename, content = _read_pdf(upload, settings)
    try:
        parsed = parse_resume_pdf(content)
        extraction_status = "needs_review"
    except ResumeParseError:
        parsed = unsupported_extraction()
        extraction_status = "unsupported"
    document_id = str(uuid4())
    storage_key = f"{document_id}.pdf"
    destination = _private_path(settings, storage_key)
    try:
        with destination.open("xb") as stored:
            stored.write(content)
        os.chmod(destination, 0o600)
        previous = db.execute(
            text(
                "SELECT id FROM resume_document "
                "WHERE candidate_profile_id = :profile_id AND status = 'uploaded'"
            ),
            {"profile_id": profile_id},
        ).scalars().all()
        for previous_id in previous:
            db.execute(
                text("UPDATE resume_document SET status = 'replaced' WHERE id = :id"),
                {"id": previous_id},
            )
            _audit(db, identity_id, "resume_document_replaced", previous_id, "replaced")
        db.execute(
            text(
                "INSERT INTO resume_document "
                "(id, candidate_profile_id, original_filename, content_type, size_bytes, "
                "sha256, storage_key, status) VALUES "
                "(:id, :profile_id, :original_filename, :content_type, :size_bytes, "
                ":sha256, :storage_key, 'uploaded')"
            ),
            {
                "id": document_id,
                "profile_id": profile_id,
                "original_filename": safe_filename,
                "content_type": ALLOWED_CONTENT_TYPE,
                "size_bytes": len(content),
                "sha256": hashlib.sha256(content).hexdigest(),
                "storage_key": storage_key,
            },
        )
        db.execute(
            text(
                "INSERT INTO resume_extraction "
                "(id, resume_document_id, status, parser_version, fields) VALUES "
                "(:id, :resume_document_id, :status, :parser_version, :fields)"
            ),
            {
                "id": str(uuid4()),
                "resume_document_id": document_id,
                "status": extraction_status,
                "parser_version": parsed["parser_version"],
                "fields": json.dumps(parsed, ensure_ascii=False, separators=(",", ":")),
            },
        )
        _audit(db, identity_id, "resume_document_uploaded", document_id, "uploaded")
        db.commit()
    except Exception:
        db.rollback()
        destination.unlink(missing_ok=True)
        raise
    return get_resume(db, principal)


def review_resume(
    db: Session,
    principal: Principal,
    document_id: str,
    *,
    accepted: bool,
    fields: dict[str, Any],
) -> dict[str, Any]:
    identity_id, profile_id = _ensure_candidate_profile(db, principal)
    document = db.execute(
        text(
            "SELECT id FROM resume_document WHERE id = :document_id "
            "AND candidate_profile_id = :profile_id AND status = 'uploaded'"
        ),
        {"document_id": document_id, "profile_id": profile_id},
    ).mappings().one_or_none()
    if document is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="resume_not_found")
    extraction = _extraction(db, document_id)
    if extraction is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="resume_extraction_not_found")
    if extraction["status"] in {"accepted", "rejected"}:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="resume_already_reviewed")
    if accepted and extraction["status"] == "unsupported":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="resume_extraction_unavailable")

    reviewed_fields = {
        key: fields[key]
        for key in ("display_name", "headline", "summary", "skills", "experience")
        if key in fields
    }
    if accepted and reviewed_fields:
        update_profile(db, principal, reviewed_fields, commit=False)
    db.execute(
        text(
            "UPDATE resume_extraction SET status = :status, reviewed_fields = :reviewed_fields, "
            "reviewed_at = CURRENT_TIMESTAMP WHERE resume_document_id = :document_id"
        ),
        {
            "status": "accepted" if accepted else "rejected",
            "reviewed_fields": json.dumps(reviewed_fields, ensure_ascii=False, separators=(",", ":"))
            if accepted else None,
            "document_id": document_id,
        },
    )
    _audit(db, identity_id, "resume_extraction_reviewed", document_id, "accepted" if accepted else "rejected")
    db.commit()
    return get_resume(db, principal)
