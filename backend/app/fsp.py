"""Replaceable FSP registry boundary and candidate-owned link use cases.

The synthetic adapter deliberately models only the internal evidence shape. It is
not a claim about a production FSP API or an external identity schema.
"""

from __future__ import annotations

import json
from collections.abc import Iterable
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

FSP_RANKING_WEIGHT = 10.0
FSP_RANKING_VERSION = "fsp-evidence-2026-10"
_FSP_RANKING_COMPONENT_WEIGHTS = {
    "result_strength": 0.40,
    "event_level": 0.20,
    "recency": 0.20,
    "verification": 0.20,
}
_FSP_ACHIEVEMENT_AGGREGATION_WEIGHTS = (0.70, 0.20, 0.10)


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


@dataclass(frozen=True)
class FspRankingNeed:
    """The employer-need evidence needed to evaluate an FSP bonus."""

    specialization_slug: str | None = None
    required_skill_slugs: tuple[str, ...] = ()
    preferred_skill_slugs: tuple[str, ...] = ()


@dataclass(frozen=True)
class FspRankingContribution:
    """Explainable, capped FSP contribution for a single candidate and need."""

    score: float
    max_score: float
    ranking_version: str
    history_status: str
    relevant_achievement_count: int
    contributing_achievement_ids: tuple[str, ...]
    matched_specialization: bool
    matched_skill_slugs: tuple[str, ...]
    component_scores: dict[str, float]
    reasons: tuple[str, ...]

    def as_dict(self) -> dict[str, object]:
        """Return the stable shape consumed by a future matching result."""

        return {
            "score": self.score,
            "max_score": self.max_score,
            "ranking_version": self.ranking_version,
            "history_status": self.history_status,
            "relevant_achievement_count": self.relevant_achievement_count,
            "contributing_achievement_ids": list(self.contributing_achievement_ids),
            "matched_specialization": self.matched_specialization,
            "matched_skill_slugs": list(self.matched_skill_slugs),
            "component_scores": self.component_scores.copy(),
            "reasons": list(self.reasons),
        }


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


def _normalize_slug(value: str | None) -> str:
    return value.strip().casefold() if value else ""


def _level_score(level: str) -> float:
    normalized = level.strip().casefold()
    if normalized in {"international", "national", "federal", "all-russian"}:
        return 1.0
    if normalized == "regional":
        return 0.75
    if normalized == "local":
        return 0.50
    return 0.25 if normalized else 0.0


def _verification_score(verification: str) -> float:
    """Translate provenance presence into a deliberately simple confidence signal."""

    normalized = verification.strip().casefold()
    if not normalized or "unverified" in normalized:
        return 0.0
    if any(marker in normalized for marker in ("verified", "registry", "synthetic")):
        return 1.0
    return 0.75


def _achievement_relevance(
    achievement: FspAchievement,
    need: FspRankingNeed,
) -> tuple[float, bool, tuple[str, ...]]:
    required = {_normalize_slug(skill) for skill in need.required_skill_slugs if _normalize_slug(skill)}
    preferred = {_normalize_slug(skill) for skill in need.preferred_skill_slugs if _normalize_slug(skill)}
    achievement_skills = {
        _normalize_slug(skill) for skill in map_achievement(achievement).skill_slugs if _normalize_slug(skill)
    }
    matched_required = required & achievement_skills
    matched_preferred = preferred & achievement_skills
    skill_relevance = max(
        (len(matched_required) / len(required)) if required else 0.0,
        (0.80 * len(matched_preferred) / len(preferred)) if preferred else 0.0,
    )
    mapped_specialization = _normalize_slug(map_achievement(achievement).specialization_slug)
    specialization_match = bool(
        need.specialization_slug
        and mapped_specialization == _normalize_slug(need.specialization_slug)
    )
    matched_skills = tuple(sorted(matched_required | matched_preferred))
    return max(1.0 if specialization_match else 0.0, skill_relevance), specialization_match, matched_skills


def _achievement_strength(
    achievement: FspAchievement,
    *,
    as_of: date | None,
) -> tuple[float, dict[str, float]]:
    mapping = map_achievement(achievement)
    component_scores = {
        "result_strength": max(0.0, min(mapping.result_score / 100.0, 1.0)),
        "event_level": _level_score(achievement.level),
        "recency": map_recency(achievement.event_date, as_of=as_of).score / 100.0,
        "verification": _verification_score(achievement.verification),
    }
    strength = sum(
        component_scores[name] * weight
        for name, weight in _FSP_RANKING_COMPONENT_WEIGHTS.items()
    )
    return strength, component_scores


def calculate_fsp_contribution(
    achievements: Iterable[FspAchievement],
    need: FspRankingNeed,
    *,
    as_of: date | None = None,
    max_bonus: float = FSP_RANKING_WEIGHT,
) -> FspRankingContribution:
    """Calculate a positive, need-specific FSP bonus without creating an eligibility gate.

    The strongest three relevant achievements are aggregated with diminishing weights
    (70/20/10 percent), then multiplied by ``max_bonus``. This makes the configured
    FSP weight a hard upper bound while preserving useful evidence plurality.
    """

    if max_bonus <= 0:
        raise ValueError("max_bonus must be positive")

    scored: list[
        tuple[float, float, FspAchievement, bool, tuple[str, ...], dict[str, float]]
    ] = []
    has_history = False
    for achievement in achievements:
        has_history = True
        relevance, specialization_match, matched_skills = _achievement_relevance(achievement, need)
        if relevance <= 0:
            continue
        strength, components = _achievement_strength(achievement, as_of=as_of)
        scored.append(
            (
                relevance * strength,
                relevance,
                achievement,
                specialization_match,
                matched_skills,
                components,
            )
        )

    scored.sort(key=lambda item: (-item[0], item[2].achievement_id))
    selected = scored[: len(_FSP_ACHIEVEMENT_AGGREGATION_WEIGHTS)]
    normalized_score = sum(item[0] * weight for item, weight in zip(selected, _FSP_ACHIEVEMENT_AGGREGATION_WEIGHTS))
    normalized_score = max(0.0, min(normalized_score, 1.0))
    score = round(max_bonus * normalized_score, 2)

    matched_specialization = any(item[3] for item in selected)
    matched_skills = tuple(sorted({skill for item in selected for skill in item[4]}))
    component_scores: dict[str, float] = {
        "relevance": round(max((item[1] for item in selected), default=0.0), 4),
        "result_strength": round(
            max((item[5]["result_strength"] for item in selected), default=0.0), 4
        ),
        "event_level": round(max((item[5]["event_level"] for item in selected), default=0.0), 4),
        "recency": round(max((item[5]["recency"] for item in selected), default=0.0), 4),
        "verification": round(max((item[5]["verification"] for item in selected), default=0.0), 4),
        "uncapped_normalized": round(normalized_score, 4),
    }

    if not has_history:
        reasons = ("No FSP history; no bonus or penalty.",)
        history_status = "no_history"
    elif not scored:
        reasons = ("FSP history is present but has no evidence relevant to this need.",)
        history_status = "has_history"
    else:
        reason_parts = [f"{len(scored)} relevant FSP achievement(s) contribute to this bonus."]
        if matched_specialization:
            reason_parts.append("At least one achievement matches the requested specialization.")
        if matched_skills:
            reason_parts.append(f"Matched FSP skills: {', '.join(matched_skills)}.")
        history_status = "has_history"
        reasons = tuple(reason_parts)

    return FspRankingContribution(
        score=score,
        max_score=round(max_bonus, 2),
        ranking_version=FSP_RANKING_VERSION,
        history_status=history_status,
        relevant_achievement_count=len(scored),
        contributing_achievement_ids=tuple(item[2].achievement_id for item in selected),
        matched_specialization=matched_specialization,
        matched_skill_slugs=matched_skills,
        component_scores=component_scores,
        reasons=reasons,
    )


def _snapshot_achievement(row) -> FspAchievement:
    event_date = row["event_date"]
    if isinstance(event_date, datetime):
        event_date = event_date.date()
    elif isinstance(event_date, str):
        event_date = date.fromisoformat(event_date)
    return FspAchievement(
        achievement_id=row["external_achievement_id"],
        event_name=row["event_name"],
        event_date=event_date,
        discipline=row["discipline"],
        level=row["level"],
        achievement_type=row["achievement_type"],
        placement=row["placement"],
        result=row["result"],
        verification=row["verification"],
        mapping_version=row["mapping_version"],
    )


def calculate_fsp_contribution_for_candidate(
    db: Session,
    candidate_profile_id: str,
    need: FspRankingNeed,
    *,
    as_of: date | None = None,
    max_bonus: float = FSP_RANKING_WEIGHT,
) -> FspRankingContribution:
    """Load one candidate's persisted FSP snapshot and calculate its contribution."""

    rows = db.execute(
        text(
            "SELECT a.external_achievement_id, a.event_name, a.event_date, a.discipline, "
            "a.level, a.achievement_type, a.placement, a.result, a.verification, "
            "a.mapping_version FROM fsp_achievement a "
            "JOIN fsp_link l ON l.id = a.fsp_link_id "
            "WHERE l.candidate_profile_id = :candidate_profile_id "
            "ORDER BY a.event_date DESC, a.id"
        ),
        {"candidate_profile_id": candidate_profile_id},
    ).mappings().all()
    return calculate_fsp_contribution(
        (_snapshot_achievement(row) for row in rows),
        need,
        as_of=as_of,
        max_bonus=max_bonus,
    )


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
