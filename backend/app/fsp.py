"""Replaceable FSP registry boundary and candidate-owned link use cases.

The synthetic adapter deliberately models only the internal evidence shape. It is
not a claim about a production FSP API or an external identity schema.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, date, datetime
from typing import ClassVar, Protocol
from uuid import uuid4

from fastapi import HTTPException, status
from sqlalchemy import text
from sqlalchemy.orm import Session

from .auth import Principal, sync_identity

SYNTHETIC_PROVIDER = "synthetic"


@dataclass(frozen=True)
class FspParticipant:
    participant_id: str


@dataclass(frozen=True)
class FspAchievement:
    achievement_id: str
    event_name: str
    event_date: date
    discipline: str
    level: str
    achievement_type: str
    placement: str | None
    result: str | None
    verification: str
    mapping_version: str


class FspRegistryPort(Protocol):
    provider: str

    def get_participant(self, fsp_id: str) -> FspParticipant | None: ...

    def list_achievements(self, fsp_id: str) -> tuple[FspAchievement, ...]: ...

    def verify_link(self, fsp_id: str) -> FspParticipant | None: ...


class SyntheticFspRegistryAdapter:
    """Deterministic adapter used by demo and tests until a real port exists."""

    provider: ClassVar[str] = SYNTHETIC_PROVIDER

    _participants: ClassVar[frozenset[str]] = frozenset({"FSP-DEMO-001", "FSP-DEMO-NONE"})
    _achievements: ClassVar[dict[str, tuple[FspAchievement, ...]]] = {
        "FSP-DEMO-001": (
            FspAchievement(
                achievement_id="synthetic-achievement-001",
                event_name="FSP Demo Backend Challenge",
                event_date=date(2025, 11, 16),
                discipline="Backend Engineering",
                level="national",
                achievement_type="prize",
                placement="2",
                result="Finalist in API reliability track",
                verification="synthetic registry fixture",
                mapping_version="synthetic-2026-01",
            ),
            FspAchievement(
                achievement_id="synthetic-achievement-002",
                event_name="FSP Demo Systems Sprint",
                event_date=date(2024, 6, 8),
                discipline="Backend Engineering",
                level="regional",
                achievement_type="win",
                placement="1",
                result="Won the data services round",
                verification="synthetic registry fixture",
                mapping_version="synthetic-2026-01",
            ),
        ),
        "FSP-DEMO-NONE": (),
    }

    def _normalize(self, fsp_id: str) -> str:
        return fsp_id.strip().upper()

    def get_participant(self, fsp_id: str) -> FspParticipant | None:
        normalized = self._normalize(fsp_id)
        return FspParticipant(normalized) if normalized in self._participants else None

    def list_achievements(self, fsp_id: str) -> tuple[FspAchievement, ...]:
        return self._achievements.get(self._normalize(fsp_id), ())

    def verify_link(self, fsp_id: str) -> FspParticipant | None:
        participant = self.get_participant(fsp_id)
        if participant is None:
            return None
        return participant


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


def _require_processing_consent(db: Session, profile_id: str) -> None:
    allowed = db.execute(
        text("SELECT processing_consent_version FROM candidate_profile WHERE id = :profile_id"),
        {"profile_id": profile_id},
    ).scalar_one_or_none()
    if allowed is None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="processing_consent_required")


def _achievement_response(row) -> dict[str, object]:
    return {
        "id": row["external_achievement_id"],
        "event_name": row["event_name"],
        "event_date": row["event_date"],
        "discipline": row["discipline"],
        "level": row["level"],
        "achievement_type": row["achievement_type"],
        "placement": row["placement"],
        "result": row["result"],
        "verification": row["verification"],
        "mapping_version": row["mapping_version"],
    }


def get_fsp(db: Session, principal: Principal) -> dict[str, object]:
    _, profile_id = _ensure_candidate_profile(db, principal)
    link = db.execute(
        text(
            "SELECT id, provider, participant_id, linked_at, updated_at "
            "FROM fsp_link WHERE candidate_profile_id = :profile_id"
        ),
        {"profile_id": profile_id},
    ).mappings().one_or_none()
    if link is None:
        return {
            "status": "not_linked",
            "provider": None,
            "participant_id": None,
            "linked_at": None,
            "updated_at": None,
            "history_status": "no_history",
            "achievements": [],
        }

    rows = db.execute(
        text(
            "SELECT external_achievement_id, event_name, event_date, discipline, level, "
            "achievement_type, placement, result, verification, mapping_version "
            "FROM fsp_achievement WHERE fsp_link_id = :link_id ORDER BY event_date DESC, id"
        ),
        {"link_id": link["id"]},
    ).mappings().all()
    return {
        "status": "linked",
        "provider": link["provider"],
        "participant_id": link["participant_id"],
        "linked_at": link["linked_at"],
        "updated_at": link["updated_at"],
        "history_status": "has_history" if rows else "no_history",
        "achievements": [_achievement_response(row) for row in rows],
    }


def link_fsp(db: Session, principal: Principal, fsp_id: str, registry: FspRegistryPort) -> dict[str, object]:
    identity_id, profile_id = _ensure_candidate_profile(db, principal)
    _require_processing_consent(db, profile_id)
    participant = registry.verify_link(fsp_id)
    if participant is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="fsp_participant_not_found")

    now = datetime.now(UTC)
    existing = db.execute(
        text("SELECT id FROM fsp_link WHERE candidate_profile_id = :profile_id"),
        {"profile_id": profile_id},
    ).scalar_one_or_none()
    if existing is None:
        link_id = str(uuid4())
        db.execute(
            text(
                "INSERT INTO fsp_link "
                "(id, candidate_profile_id, provider, participant_id, linked_at, updated_at) "
                "VALUES (:id, :profile_id, :provider, :participant_id, :linked_at, :updated_at)"
            ),
            {
                "id": link_id,
                "profile_id": profile_id,
                "provider": registry.provider,
                "participant_id": participant.participant_id,
                "linked_at": now,
                "updated_at": now,
            },
        )
    else:
        link_id = existing
        db.execute(text("DELETE FROM fsp_achievement WHERE fsp_link_id = :link_id"), {"link_id": link_id})
        db.execute(
            text(
                "UPDATE fsp_link SET provider = :provider, participant_id = :participant_id, "
                "updated_at = :updated_at WHERE id = :link_id"
            ),
            {
                "link_id": link_id,
                "provider": registry.provider,
                "participant_id": participant.participant_id,
                "updated_at": now,
            },
        )

    for achievement in registry.list_achievements(participant.participant_id):
        db.execute(
            text(
                "INSERT INTO fsp_achievement "
                "(id, fsp_link_id, external_achievement_id, event_name, event_date, discipline, "
                "level, achievement_type, placement, result, verification, mapping_version) "
                "VALUES (:id, :link_id, :external_id, :event_name, :event_date, :discipline, "
                ":level, :achievement_type, :placement, :result, :verification, :mapping_version)"
            ),
            {
                "id": str(uuid4()),
                "link_id": link_id,
                "external_id": achievement.achievement_id,
                "event_name": achievement.event_name,
                "event_date": achievement.event_date,
                "discipline": achievement.discipline,
                "level": achievement.level,
                "achievement_type": achievement.achievement_type,
                "placement": achievement.placement,
                "result": achievement.result,
                "verification": achievement.verification,
                "mapping_version": achievement.mapping_version,
            },
        )
    db.execute(
        text(
            "INSERT INTO audit_event (id, actor_identity_id, event_type, details) "
            "VALUES (:id, :identity_id, :event_type, :details)"
        ),
        {
            "id": str(uuid4()),
            "identity_id": identity_id,
            "event_type": "fsp_linked",
            "details": json.dumps(
                {"provider": registry.provider, "participant_id": participant.participant_id},
                separators=(",", ":"),
                sort_keys=True,
            ),
        },
    )
    db.commit()
    return get_fsp(db, principal)


def unlink_fsp(db: Session, principal: Principal) -> None:
    identity_id, profile_id = _ensure_candidate_profile(db, principal)
    link_id = db.execute(
        text("SELECT id FROM fsp_link WHERE candidate_profile_id = :profile_id"),
        {"profile_id": profile_id},
    ).scalar_one_or_none()
    if link_id is None:
        return
    db.execute(text("DELETE FROM fsp_achievement WHERE fsp_link_id = :link_id"), {"link_id": link_id})
    db.execute(text("DELETE FROM fsp_link WHERE id = :link_id"), {"link_id": link_id})
    db.execute(
        text(
            "INSERT INTO audit_event (id, actor_identity_id, event_type, details) "
            "VALUES (:id, :identity_id, :event_type, :details)"
        ),
        {
            "id": str(uuid4()),
            "identity_id": identity_id,
            "event_type": "fsp_unlinked",
            "details": json.dumps({"provider": SYNTHETIC_PROVIDER}, separators=(",", ":")),
        },
    )
    db.commit()
