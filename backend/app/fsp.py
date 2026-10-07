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

_DISCIPLINE_MAPPINGS: dict[str, tuple[str, tuple[str, ...]]] = {
    "backend engineering": ("backend-engineering", ("python", "sql", "rest-apis", "git")),
    "frontend engineering": ("frontend-engineering", ("typescript", "automated-testing", "git")),
    "full-stack engineering": (
        "full-stack-engineering",
        ("python", "typescript", "sql", "rest-apis", "git"),
    ),
    "qa / test automation": ("qa-test-automation", ("automated-testing", "python", "sql", "git")),
    "devops / sre": ("devops-sre", ("docker", "kubernetes", "python", "git")),
    "data engineering": ("data-engineering", ("python", "sql", "data-modeling", "docker")),
    "data science / ml": ("data-science-ml", ("python", "sql", "machine-learning", "data-modeling")),
    "mobile engineering": ("mobile-engineering", ("swift", "automated-testing", "git")),
}

_RESULT_TYPE_SCORES = {
    "win": (100, "winner"),
    "prize": (90, "prize"),
    "finalist": (80, "finalist"),
    "participation": (40, "participant"),
}

_RECENCY_BANDS = ((365, 100, "recent"), (730, 70, "aging"), (1095, 40, "old"))


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


@dataclass(frozen=True)
class FspEvidenceMapping:
    specialization_slug: str | None
    skill_slugs: tuple[str, ...]
    result_score: int
    result_label: str


@dataclass(frozen=True)
class FspRecency:
    score: int
    label: str


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


def _placement_score(placement: str | None) -> tuple[int, str] | None:
    if not placement:
        return None
    try:
        position = int(placement.strip())
    except (TypeError, ValueError):
        return None
    if position <= 0:
        return None
    if position == 1:
        return 100, "winner"
    if position == 2:
        return 90, "prize"
    if position == 3:
        return 85, "prize"
    if position <= 10:
        return 75, "finalist"
    return 60, "placed"


def map_achievement(achievement: FspAchievement) -> FspEvidenceMapping:
    """Normalize registry fields without guessing unknown taxonomy mappings."""

    specialization, skills = _DISCIPLINE_MAPPINGS.get(
        achievement.discipline.strip().casefold(), (None, ())
    )
    type_score, type_label = _RESULT_TYPE_SCORES.get(
        achievement.achievement_type.strip().casefold(), (50, "recorded")
    )
    placement = _placement_score(achievement.placement)
    result_score, result_label = placement or (type_score, type_label)
    if placement and type_score > placement[0]:
        result_score, result_label = type_score, type_label
    return FspEvidenceMapping(
        specialization_slug=specialization,
        skill_slugs=skills,
        result_score=result_score,
        result_label=result_label,
    )


def map_recency(event_date: date | str, *, as_of: date | None = None) -> FspRecency:
    """Return a non-excluding freshness signal for a dated achievement."""

    if isinstance(event_date, str):
        event_date = date.fromisoformat(event_date)
    reference_date = as_of or datetime.now(UTC).date()
    age_days = (reference_date - event_date).days
    if age_days < 0:
        return FspRecency(score=0, label="future")
    for limit, score, label in _RECENCY_BANDS:
        if age_days <= limit:
            return FspRecency(score=score, label=label)
    return FspRecency(score=10, label="stale")


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


def _achievement_response(row, *, as_of: date | None = None) -> dict[str, object]:
    try:
        mapped_skills = json.loads(row["canonical_skill_slugs"] or "[]")
    except (TypeError, json.JSONDecodeError):
        mapped_skills = []
    if not isinstance(mapped_skills, list) or not all(isinstance(item, str) for item in mapped_skills):
        mapped_skills = []
    recency = map_recency(row["event_date"], as_of=as_of)
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
        "mapped_specialization": row["canonical_specialization_slug"],
        "mapped_skills": mapped_skills,
        "result_score": row["result_score"],
        "result_label": row["result_label"],
        "recency_score": recency.score,
        "recency_label": recency.label,
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
            "achievement_type, placement, result, verification, mapping_version, "
            "canonical_specialization_slug, canonical_skill_slugs, result_score, result_label "
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
        mapping = map_achievement(achievement)
        db.execute(
            text(
                "INSERT INTO fsp_achievement "
                "(id, fsp_link_id, external_achievement_id, event_name, event_date, discipline, "
                "level, achievement_type, placement, result, verification, mapping_version, "
                "canonical_specialization_slug, canonical_skill_slugs, result_score, result_label) "
                "VALUES (:id, :link_id, :external_id, :event_name, :event_date, :discipline, "
                ":level, :achievement_type, :placement, :result, :verification, :mapping_version, "
                ":canonical_specialization_slug, :canonical_skill_slugs, :result_score, :result_label)"
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
                "canonical_specialization_slug": mapping.specialization_slug,
                "canonical_skill_slugs": json.dumps(mapping.skill_slugs, separators=(",", ":")),
                "result_score": mapping.result_score,
                "result_label": mapping.result_label,
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
