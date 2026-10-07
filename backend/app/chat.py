"""Server-side authorization and persistence for post-match internal chat."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from fastapi import HTTPException, status
from sqlalchemy import text
from sqlalchemy.orm import Session

from .auth import Principal, sync_identity


def create_conversation_for_match(
    db: Session,
    *,
    match_id: str,
    employer_identity_id: str,
    candidate_profile_id: str,
) -> str:
    """Create the two-party conversation inside the match transaction.

    This function deliberately does not commit. The invitation acceptance
    transaction owns the match, domain events, and conversation atomically.
    """

    existing = db.execute(
        text("SELECT id FROM conversation WHERE match_id = :match_id"),
        {"match_id": match_id},
    ).scalar_one_or_none()
    if existing is not None:
        return existing

    candidate_identity_id = db.execute(
        text("SELECT identity_id FROM candidate_profile WHERE id = :candidate_profile_id"),
        {"candidate_profile_id": candidate_profile_id},
    ).scalar_one_or_none()
    if candidate_identity_id is None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="conversation_match_invalid")

    conversation_id = str(uuid4())
    db.execute(
        text("INSERT INTO conversation (id, match_id) VALUES (:id, :match_id)"),
        {"id": conversation_id, "match_id": match_id},
    )
    db.execute(
        text(
            "INSERT INTO conversation_member (conversation_id, identity_id) VALUES "
            "(:conversation_id, :employer_identity_id), (:conversation_id, :candidate_identity_id)"
        ),
        {
            "conversation_id": conversation_id,
            "employer_identity_id": employer_identity_id,
            "candidate_identity_id": candidate_identity_id,
        },
    )
    return conversation_id


def _conversation_context(
    db: Session,
    principal: Principal,
    conversation_id: str,
) -> dict[str, Any]:
    """Return a conversation only when the current identity is a member."""

    identity = sync_identity(db, principal)
    row = db.execute(
        text(
            "SELECT c.id, c.match_id, c.created_at, c.last_message_at, "
            "other.identity_id AS other_identity_id, "
            "CASE WHEN other_user.role = 'candidate' "
            "THEN COALESCE(candidate.display_name, 'Кандидат') "
            "ELSE COALESCE(company.name, 'Работодатель') END AS participant_label "
            "FROM conversation c "
            "JOIN conversation_member mine ON mine.conversation_id = c.id "
            "JOIN conversation_member other ON other.conversation_id = c.id "
            "AND other.identity_id <> mine.identity_id "
            "JOIN user_identity other_user ON other_user.id = other.identity_id "
            "LEFT JOIN candidate_profile candidate ON candidate.identity_id = other.identity_id "
            "LEFT JOIN company ON company.owner_identity_id = other.identity_id "
            "WHERE c.id = :conversation_id AND mine.identity_id = :identity_id"
        ),
        {"conversation_id": conversation_id, "identity_id": identity["id"]},
    ).mappings().one_or_none()
    if row is None:
        # Do not reveal whether a conversation exists for another match.
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="conversation_not_found")
    return {**row, "identity_id": identity["id"]}


def _unread_count(db: Session, conversation_id: str, identity_id: str) -> int:
    return int(
        db.execute(
            text(
                "SELECT COUNT(*) FROM message m "
                "LEFT JOIN message_read mr ON mr.message_id = m.id AND mr.identity_id = :identity_id "
                "WHERE m.conversation_id = :conversation_id "
                "AND m.sender_identity_id <> :identity_id AND mr.message_id IS NULL"
            ),
            {"conversation_id": conversation_id, "identity_id": identity_id},
        ).scalar_one()
    )


def _message_payload(row: Any, identity_id: str) -> dict[str, Any]:
    return {
        "id": row["id"],
        "sender_is_current": row["sender_identity_id"] == identity_id,
        "body": row["body"],
        "created_at": row["created_at"],
        "read_at": row["read_at"],
    }


def _contact_payload(row: Any, identity_id: str) -> dict[str, Any]:
    return {
        "id": row["id"],
        "is_current": row["identity_id"] == identity_id,
        "contact_type": row["contact_type"],
        "contact_value": row["contact_value"],
        "created_at": row["created_at"],
    }


def _conversation_summary(db: Session, row: Any, identity_id: str) -> dict[str, Any]:
    last_message = db.execute(
        text(
            "SELECT body FROM message WHERE conversation_id = :conversation_id "
            "ORDER BY created_at DESC, id DESC LIMIT 1"
        ),
        {"conversation_id": row["id"]},
    ).scalar_one_or_none()
    return {
        "id": row["id"],
        "match_id": row["match_id"],
        "participant_label": row["participant_label"],
        "created_at": row["created_at"],
        "last_message_at": row["last_message_at"],
        "last_message_preview": last_message[:120] if last_message else None,
        "unread_count": _unread_count(db, row["id"], identity_id),
    }


def list_conversations(db: Session, principal: Principal) -> list[dict[str, Any]]:
    identity = sync_identity(db, principal)
    rows = db.execute(
        text(
            "SELECT c.id, c.match_id, c.created_at, c.last_message_at, "
            "CASE WHEN other_user.role = 'candidate' "
            "THEN COALESCE(candidate.display_name, 'Кандидат') "
            "ELSE COALESCE(company.name, 'Работодатель') END AS participant_label "
            "FROM conversation c "
            "JOIN conversation_member mine ON mine.conversation_id = c.id "
            "JOIN conversation_member other ON other.conversation_id = c.id "
            "AND other.identity_id <> mine.identity_id "
            "JOIN user_identity other_user ON other_user.id = other.identity_id "
            "LEFT JOIN candidate_profile candidate ON candidate.identity_id = other.identity_id "
            "LEFT JOIN company ON company.owner_identity_id = other.identity_id "
            "WHERE mine.identity_id = :identity_id "
            "ORDER BY COALESCE(c.last_message_at, c.created_at) DESC, c.id DESC"
        ),
        {"identity_id": identity["id"]},
    ).mappings()
    return [_conversation_summary(db, row, identity["id"]) for row in rows]


def get_conversation(
    db: Session,
    principal: Principal,
    conversation_id: str,
    *,
    limit: int = 100,
) -> dict[str, Any]:
    context = _conversation_context(db, principal, conversation_id)
    messages = db.execute(
        text(
            "SELECT m.id, m.sender_identity_id, m.body, m.created_at, mr.read_at "
            "FROM message m "
            "LEFT JOIN message_read mr ON mr.message_id = m.id "
            "AND mr.identity_id = :identity_id "
            "WHERE m.conversation_id = :conversation_id "
            "ORDER BY m.created_at DESC, m.id DESC LIMIT :limit"
        ),
        {"conversation_id": conversation_id, "identity_id": context["identity_id"], "limit": limit},
    ).mappings().all()
    contacts = db.execute(
        text(
            "SELECT id, identity_id, contact_type, contact_value, created_at "
            "FROM conversation_contact_exchange WHERE conversation_id = :conversation_id "
            "ORDER BY created_at ASC, id ASC"
        ),
        {"conversation_id": conversation_id},
    ).mappings()
    return {
        "id": context["id"],
        "match_id": context["match_id"],
        "participant_label": context["participant_label"],
        "created_at": context["created_at"],
        "last_message_at": context["last_message_at"],
        "unread_count": _unread_count(db, conversation_id, context["identity_id"]),
        "messages": [_message_payload(row, context["identity_id"]) for row in reversed(messages)],
        "contacts": [_contact_payload(row, context["identity_id"]) for row in contacts],
    }


def send_message(
    db: Session,
    principal: Principal,
    conversation_id: str,
    body: str,
) -> dict[str, Any]:
    context = _conversation_context(db, principal, conversation_id)
    clean_body = body.strip()
    if not clean_body:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="message_body_required")

    message_id = str(uuid4())
    now = datetime.now(UTC)
    db.execute(
        text(
            "INSERT INTO message (id, conversation_id, sender_identity_id, body, created_at) "
            "VALUES (:id, :conversation_id, :sender_identity_id, :body, :created_at)"
        ),
        {
            "id": message_id,
            "conversation_id": conversation_id,
            "sender_identity_id": context["identity_id"],
            "body": clean_body,
            "created_at": now,
        },
    )
    db.execute(
        text("UPDATE conversation SET last_message_at = :last_message_at WHERE id = :conversation_id"),
        {"conversation_id": conversation_id, "last_message_at": now},
    )
    db.commit()
    return {
        "id": message_id,
        "sender_is_current": True,
        "body": clean_body,
        "created_at": now,
        "read_at": None,
    }


def mark_conversation_read(db: Session, principal: Principal, conversation_id: str) -> dict[str, Any]:
    context = _conversation_context(db, principal, conversation_id)
    message_ids = db.execute(
        text(
            "SELECT m.id FROM message m "
            "LEFT JOIN message_read mr ON mr.message_id = m.id AND mr.identity_id = :identity_id "
            "WHERE m.conversation_id = :conversation_id "
            "AND m.sender_identity_id <> :identity_id AND mr.message_id IS NULL"
        ),
        {"conversation_id": conversation_id, "identity_id": context["identity_id"]},
    ).scalars()
    now = datetime.now(UTC)
    marked_count = 0
    for message_id in message_ids:
        db.execute(
            text(
                "INSERT INTO message_read (message_id, identity_id, read_at) "
                "VALUES (:message_id, :identity_id, :read_at)"
            ),
            {"message_id": message_id, "identity_id": context["identity_id"], "read_at": now},
        )
        marked_count += 1
    db.commit()
    return {"conversation_id": conversation_id, "marked_count": marked_count, "unread_count": 0}


def exchange_contact(
    db: Session,
    principal: Principal,
    conversation_id: str,
    *,
    contact_type: str,
    contact_value: str,
) -> dict[str, Any]:
    context = _conversation_context(db, principal, conversation_id)
    clean_value = contact_value.strip()
    if not clean_value:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="contact_value_required")

    existing = db.execute(
        text(
            "SELECT id FROM conversation_contact_exchange "
            "WHERE conversation_id = :conversation_id AND identity_id = :identity_id"
        ),
        {"conversation_id": conversation_id, "identity_id": context["identity_id"]},
    ).scalar_one_or_none()
    now = datetime.now(UTC)
    if existing:
        db.execute(
            text(
                "UPDATE conversation_contact_exchange SET contact_type = :contact_type, "
                "contact_value = :contact_value, created_at = :created_at WHERE id = :id"
            ),
            {
                "id": existing,
                "contact_type": contact_type,
                "contact_value": clean_value,
                "created_at": now,
            },
        )
        contact_id = existing
    else:
        contact_id = str(uuid4())
        db.execute(
            text(
                "INSERT INTO conversation_contact_exchange "
                "(id, conversation_id, identity_id, contact_type, contact_value, created_at) "
                "VALUES (:id, :conversation_id, :identity_id, :contact_type, :contact_value, :created_at)"
            ),
            {
                "id": contact_id,
                "conversation_id": conversation_id,
                "identity_id": context["identity_id"],
                "contact_type": contact_type,
                "contact_value": clean_value,
                "created_at": now,
            },
        )
    db.commit()
    return {
        "id": contact_id,
        "is_current": True,
        "contact_type": contact_type,
        "contact_value": clean_value,
        "created_at": now,
    }


def report_conversation(
    db: Session,
    principal: Principal,
    conversation_id: str,
    *,
    reason: str,
    details: str | None,
) -> dict[str, Any]:
    context = _conversation_context(db, principal, conversation_id)
    report_id = str(uuid4())
    clean_details = details.strip() if details else None
    db.execute(
        text(
            "INSERT INTO conversation_report "
            "(id, conversation_id, reporter_identity_id, reason, details) "
            "VALUES (:id, :conversation_id, :reporter_identity_id, :reason, :details)"
        ),
        {
            "id": report_id,
            "conversation_id": conversation_id,
            "reporter_identity_id": context["identity_id"],
            "reason": reason,
            "details": clean_details,
        },
    )
    # Keep moderation audit useful without duplicating message bodies or contact values.
    db.execute(
        text(
            "INSERT INTO audit_event (id, actor_identity_id, event_type, details) "
            "VALUES (:id, :actor_identity_id, 'conversation_reported', :details)"
        ),
        {
            "id": str(uuid4()),
            "actor_identity_id": context["identity_id"],
            "details": json.dumps(
                {"conversation_id": conversation_id, "report_id": report_id, "reason": reason},
                separators=(",", ":"),
            ),
        },
    )
    db.commit()
    return {"id": report_id, "status": "open"}
