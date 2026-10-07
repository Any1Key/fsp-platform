"""Employer Talent Radar and explainable ProofMatch projection.

This module is deliberately read-only. It composes the employer-owned hiring
need with consent-gated candidate profile data, the existing assessment
projection, and the bounded FSP contribution. Contact and protected identity
data never cross this boundary.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Literal

from fastapi import HTTPException, status
from sqlalchemy import text
from sqlalchemy.orm import Session

from .assessments import AssessmentService, Attempt
from .auth import Principal
from .fsp import FspRankingNeed, calculate_fsp_contribution_for_candidate
from .hiring_needs import get_hiring_need

MAX_LIMIT = 100
DEFAULT_LIMIT = 30

_SKILL_ALIASES = {
    "fastapi": "rest-apis",
    "rest api": "rest-apis",
    "rest apis": "rest-apis",
    "restful api": "rest-apis",
    "postgres": "sql",
    "postgresql": "sql",
    "test automation": "automated-testing",
    "automated test": "automated-testing",
    "k8s": "kubernetes",
    "ml": "machine-learning",
}


@dataclass(frozen=True)
class RadarFilters:
    query: str = ""
    specialization: str | None = None
    grade: str | None = None
    skill: str | None = None
    fsp: Literal["all", "with_history", "without_history"] = "all"
    include_unconfirmed: bool = True
    limit: int = DEFAULT_LIMIT


def _normalize(value: str | None) -> str:
    return " ".join((value or "").strip().casefold().replace("/", " / ").split())


def _slug(value: str | None) -> str:
    normalized = _normalize(value)
    return _SKILL_ALIASES.get(normalized, normalized.replace(" ", "-"))


def _json_value(value: Any, default: Any) -> Any:
    if value is None:
        return default
    if isinstance(value, str):
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return default
    return value


def _catalog(db: Session) -> tuple[dict[str, str], dict[str, str], dict[str, str]]:
    specialization_slugs: dict[str, str] = {}
    specialization_names: dict[str, str] = {}
    for row in db.execute(text("SELECT slug, name FROM specialization WHERE active = :active"), {"active": True}).mappings():
        specialization_slugs[_normalize(row["slug"])] = row["slug"]
        specialization_slugs[_normalize(row["name"])] = row["slug"]
        specialization_names[row["slug"]] = row["name"]

    grade_slugs: dict[str, str] = {}
    for row in db.execute(text("SELECT slug, name FROM grade ORDER BY rank"), {}).mappings():
        grade_slugs[_normalize(row["slug"])] = row["slug"]
        grade_slugs[_normalize(row["name"])] = row["slug"]
    return specialization_slugs, specialization_names, grade_slugs


def _skill_catalog(db: Session) -> dict[str, str]:
    result: dict[str, str] = {}
    for row in db.execute(text("SELECT slug, name FROM skill WHERE active = :active"), {"active": True}).mappings():
        result[_normalize(row["slug"])] = row["slug"]
        result[_normalize(row["name"])] = row["slug"]
    return result


def _grade_name(db: Session, grade_slug: str | None) -> str | None:
    if not grade_slug:
        return None
    return db.execute(text("SELECT name FROM grade WHERE slug = :slug"), {"slug": grade_slug}).scalar_one_or_none()


def _specialization_name(db: Session, specialization_slug: str | None) -> str | None:
    if not specialization_slug:
        return None
    return db.execute(
        text("SELECT name FROM specialization WHERE slug = :slug"),
        {"slug": specialization_slug},
    ).scalar_one_or_none()


def _latest_assessment(service: AssessmentService, subject: str) -> tuple[Attempt | None, Attempt | None]:
    attempts = service.history_for(subject)
    latest = attempts[-1] if attempts else None
    submitted = [attempt for attempt in attempts if attempt.submitted]
    return latest, (submitted[-1] if submitted else None)


def _candidate_skills(row: Any, skill_catalog: dict[str, str]) -> dict[str, list[dict[str, Any]]]:
    preferences = _json_value(row["preferences"], {})
    if not isinstance(preferences, dict):
        preferences = {}
    values: list[str] = []
    if isinstance(preferences.get("skills"), list):
        values.extend(item for item in preferences["skills"] if isinstance(item, str))
    experiences = _json_value(row["experience"], [])
    if isinstance(experiences, list):
        for experience in experiences:
            if isinstance(experience, dict) and isinstance(experience.get("technologies"), list):
                values.extend(item for item in experience["technologies"] if isinstance(item, str))

    evidence: dict[str, list[dict[str, Any]]] = {}
    for value in values:
        normalized = _normalize(value)
        skill_slug = skill_catalog.get(normalized) or _SKILL_ALIASES.get(normalized)
        if skill_slug:
            evidence.setdefault(skill_slug, []).append(
                {
                    "source": "profile_declaration",
                    "provenance": "candidate profile",
                    "confidence": 0.45,
                    "freshness": "profile_updated",
                }
            )
    return evidence


def _coverage(skills: set[str], required: tuple[str, ...]) -> float:
    return len(skills & set(required)) / len(required) if required else 1.0


def _freshness(attempt: Attempt | None, updated_at: datetime | None) -> float:
    source_date = attempt.created_at if attempt else updated_at
    if source_date is None:
        return 0.0
    if source_date.tzinfo is None:
        source_date = source_date.replace(tzinfo=UTC)
    age_days = max(0, (datetime.now(UTC) - source_date.astimezone(UTC)).days)
    if age_days <= 365:
        return 1.0
    if age_days <= 730:
        return 0.7
    if age_days <= 1095:
        return 0.4
    return 0.1


def _grade_fit(candidate_grade: str | None, target_grade: str) -> float:
    if not candidate_grade:
        return 0.0
    ranks = {"junior": 1, "middle": 2, "senior": 3}
    difference = abs(ranks.get(candidate_grade, 0) - ranks.get(target_grade, 0))
    return {0: 1.0, 1: 0.55}.get(difference, 0.0)


def _candidate_card(
    db: Session,
    row: Any,
    service: AssessmentService,
    *,
    need: dict[str, Any],
    specialization_names: dict[str, str],
    grade_names: dict[str, str],
    skill_catalog: dict[str, str],
) -> dict[str, Any]:
    latest, submitted = _latest_assessment(service, row["keycloak_sub"])
    assessed = submitted or latest
    assessed_specialization = None
    if assessed:
        specialization_key = _normalize(assessed.specialization)
        assessed_specialization = next(
            (slug for slug, name in specialization_names.items() if _normalize(name) == specialization_key),
            specialization_key.replace(" ", "-"),
        )
    declared_grade = _slug(assessed.declared_grade) if assessed else None
    verified = bool(submitted and submitted.grade_state == "verified")
    grade_state = "verified" if verified else ("not_confirmed" if assessed else "not_assessed")
    candidate_grade = declared_grade
    need_specialization = need["specialization"]["slug"]
    target_grade = need["grade"]["slug"]

    evidence = _candidate_skills(row, skill_catalog)
    fsp_need = FspRankingNeed(
        specialization_slug=need_specialization,
        required_skill_slugs=tuple(skill["slug"] for skill in need["required_skills"]),
        preferred_skill_slugs=tuple(skill["slug"] for skill in need["preferred_skills"]),
    )
    fsp = calculate_fsp_contribution_for_candidate(db, row["id"], fsp_need)
    for skill_slug in fsp.matched_skill_slugs:
        evidence.setdefault(skill_slug, []).append(
            {
                "source": "fsp_achievement",
                "provenance": "FSP registry snapshot",
                "confidence": 0.9,
                "freshness": "achievement_recency_scored",
                "contribution": fsp.score,
            }
        )

    evidence_skills = set(evidence)
    required = tuple(skill["slug"] for skill in need["required_skills"])
    preferred = tuple(skill["slug"] for skill in need["preferred_skills"])
    required_coverage = _coverage(evidence_skills, required)
    preferred_coverage = _coverage(evidence_skills, preferred)
    specialization_fit = 1.0 if assessed_specialization == need_specialization else 0.0
    grade_fit = _grade_fit(candidate_grade, target_grade)
    assessment_strength = (submitted.score / 100.0) if submitted and submitted.score is not None else 0.0
    grade_confidence = 1.0 if verified else (0.45 if assessed else 0.0)
    evidence_confidence = min(1.0, (0.9 if fsp.relevant_achievement_count else 0.45) if evidence_skills else 0.0)
    freshness = _freshness(submitted, row["updated_at"])
    confidence_freshness = (grade_confidence * 0.5) + (evidence_confidence * 0.3) + (freshness * 0.2)

    components = {
        "specialization_fit": round(20.0 * specialization_fit, 2),
        "grade_fit": round(15.0 * grade_fit, 2),
        "required_skill_coverage": round(25.0 * required_coverage, 2),
        "preferred_skill_coverage": round(10.0 * preferred_coverage, 2),
        "assessment_strength": round(15.0 * assessment_strength, 2),
        "evidence_confidence_freshness": round(5.0 * confidence_freshness, 2),
        "fsp_bonus": round(fsp.score, 2),
    }
    score = round(sum(components.values()), 2)

    matched_required = sorted(set(required) & evidence_skills)
    missing_required = sorted(set(required) - evidence_skills)
    reasons: list[str] = []
    if specialization_fit:
        reasons.append(f"Category matches {specialization_names.get(need_specialization, need_specialization)}.")
    if verified:
        reasons.append(f"Platform-verified {grade_names.get(candidate_grade, candidate_grade)} grade.")
    elif assessed:
        reasons.append(f"Declared {grade_names.get(candidate_grade, candidate_grade)} grade is not confirmed.")
    else:
        reasons.append("No submitted platform assessment yet.")
    if required:
        reasons.append(f"Evidence covers {len(matched_required)}/{len(required)} required skills.")
    if fsp.score:
        reasons.extend(fsp.reasons)
    elif fsp.history_status == "no_history":
        reasons.append("No FSP history; no bonus or penalty.")

    gaps = [f"Required skill not evidenced: {skill}" for skill in missing_required]
    if not specialization_fit:
        gaps.append("Assessment category does not match this hiring need.")
    if not verified:
        gaps.append("Platform grade confirmation is still missing.")
    if not gaps:
        gaps.append("No blocking evidence gaps for this need.")

    category_label = None
    if assessed_specialization and candidate_grade:
        category_label = f"{specialization_names.get(assessed_specialization, assessed_specialization)} · {grade_names.get(candidate_grade, candidate_grade)}"
    display_name = row["display_name"] or "Unnamed candidate"
    return {
        "candidate_id": row["id"],
        "display_name": display_name,
        "headline": row["headline"],
        "location": row["location"],
        "category": {
            "specialization": assessed_specialization,
            "specialization_name": specialization_names.get(assessed_specialization) if assessed_specialization else None,
            "grade": candidate_grade,
            "grade_name": grade_names.get(candidate_grade) if candidate_grade else None,
            "label": category_label,
            "state": grade_state,
        },
        "eligibility": "verified" if verified else "unconfirmed",
        "match_score": score,
        "score_breakdown": components,
        "confidence": {
            "overall": round(confidence_freshness, 2),
            "grade": round(grade_confidence, 2),
            "evidence": round(evidence_confidence, 2),
            "freshness": round(freshness, 2),
        },
        "assessment": {
            "status": "verified" if verified else ("not_confirmed" if submitted else "not_assessed"),
            "score": submitted.score if submitted else None,
            "assessed_at": submitted.created_at if submitted else None,
        },
        "evidence": {
            "required": [
                {"skill": skill, "present": skill in evidence_skills, "edges": evidence.get(skill, [])}
                for skill in required
            ],
            "preferred": [
                {"skill": skill, "present": skill in evidence_skills, "edges": evidence.get(skill, [])}
                for skill in preferred
            ],
            "assessment": (
                [{"source": "platform_assessment", "confidence": grade_confidence, "provenance": "FSP Talent assessment"}]
                if submitted
                else []
            ),
        },
        "fsp": fsp.as_dict(),
        "reasons": reasons,
        "gaps": gaps,
        "updated_at": row["updated_at"],
    }


def get_talent_radar(
    db: Session,
    principal: Principal,
    service: AssessmentService,
    filters: RadarFilters,
) -> dict[str, Any]:
    need = get_hiring_need(db, principal)
    if need is None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="hiring_need_required_for_talent_radar")
    if filters.limit < 1 or filters.limit > MAX_LIMIT:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="talent_radar_limit_invalid")

    specialization_slugs, specialization_names, grade_slugs = _catalog(db)
    skill_catalog = _skill_catalog(db)
    requested_specialization = specialization_slugs.get(_normalize(filters.specialization)) if filters.specialization else None
    requested_grade = grade_slugs.get(_normalize(filters.grade)) if filters.grade else None
    requested_skill = skill_catalog.get(_normalize(filters.skill)) or (_SKILL_ALIASES.get(_normalize(filters.skill)) if filters.skill else None)
    if filters.specialization and requested_specialization is None:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="talent_radar_specialization_invalid")
    if filters.grade and requested_grade is None:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="talent_radar_grade_invalid")
    if filters.skill and requested_skill is None:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="talent_radar_skill_invalid")
    if filters.fsp not in {"all", "with_history", "without_history"}:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="talent_radar_fsp_invalid")

    rows = db.execute(
        text(
            "SELECT cp.id, cp.display_name, cp.headline, cp.location, cp.summary, cp.experience, "
            "cp.preferences, cp.updated_at, ui.keycloak_sub "
            "FROM candidate_profile cp JOIN user_identity ui ON ui.id = cp.identity_id "
            "WHERE ui.role = 'candidate' AND cp.is_discoverable = :discoverable "
            "AND cp.publication_consent_version IS NOT NULL ORDER BY cp.updated_at DESC, cp.id"
        ),
        {"discoverable": True},
    ).mappings()

    candidates: list[dict[str, Any]] = []
    for row in rows:
        card = _candidate_card(
            db,
            row,
            service,
            need=need,
            specialization_names=specialization_names,
            grade_names={slug: _grade_name(db, slug) for slug in set(grade_slugs.values())},
            skill_catalog=skill_catalog,
        )
        state = card["category"]["state"]
        if not filters.include_unconfirmed and state != "verified":
            continue
        if requested_specialization and card["category"]["specialization"] != requested_specialization:
            continue
        if requested_grade and card["category"]["grade"] != requested_grade:
            continue
        if requested_skill and not any(item["skill"] == requested_skill and item["present"] for group in (card["evidence"]["required"], card["evidence"]["preferred"]) for item in group):
            continue
        if filters.fsp == "with_history" and card["fsp"]["history_status"] != "has_history":
            continue
        if filters.fsp == "without_history" and card["fsp"]["history_status"] != "no_history":
            continue
        if filters.query:
            haystack = " ".join(
                str(card.get(field) or "") for field in ("display_name", "headline", "location")
            ) + " " + str(card["category"].get("label") or "")
            if _normalize(filters.query) not in _normalize(haystack):
                continue
        candidates.append(card)

    candidates.sort(key=lambda card: (-card["match_score"], card["eligibility"] != "verified", card["candidate_id"]))
    selected = candidates[: filters.limit]
    categories: dict[str, dict[str, Any]] = {}
    for card in candidates:
        category = card["category"]
        key = category["label"] or "Not assessed"
        item = categories.setdefault(
            key,
            {
                "key": key,
                "specialization": category["specialization"],
                "specialization_name": category["specialization_name"],
                "grade": category["grade"],
                "grade_name": category["grade_name"],
                "candidate_count": 0,
                "verified_count": 0,
                "unconfirmed_count": 0,
            },
        )
        item["candidate_count"] += 1
        if card["eligibility"] == "verified":
            item["verified_count"] += 1
        else:
            item["unconfirmed_count"] += 1

    filter_snapshot = {
        "query": filters.query or None,
        "specialization": requested_specialization,
        "grade": requested_grade,
        "skill": requested_skill,
        "fsp": filters.fsp,
        "include_unconfirmed": filters.include_unconfirmed,
        "limit": filters.limit,
    }
    snapshot_seed = json.dumps(
        {"need": need["id"], "filters": filter_snapshot, "candidates": [item["candidate_id"] for item in selected]},
        sort_keys=True,
    ).encode()
    snapshot_id = hashlib.sha256(snapshot_seed).hexdigest()[:16]
    return {
        "need": need,
        "snapshot": {
            "id": snapshot_id,
            "created_at": datetime.now(UTC),
            "candidate_ids": [item["candidate_id"] for item in selected],
            "scoring_version": "proofmatch-2026-10",
            "evidence_version": "candidate-evidence-2026-10",
            "need_version": str(need["updated_at"]),
            "filters": filter_snapshot,
        },
        "categories": sorted(categories.values(), key=lambda item: (-item["candidate_count"], item["key"])),
        "candidates": selected,
        "total_candidates": len(candidates),
    }
