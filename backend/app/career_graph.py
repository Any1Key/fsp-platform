"""Candidate-owned Career Graph projection.

The graph is deliberately derived at read time from the existing assessment,
taxonomy, FSP, and profile boundaries. It is a navigation aid, not a second
grade or a hiring decision: declared and unconfirmed evidence never becomes
verified merely because it appears in the graph.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from .assessments import AssessmentService
from .auth import Principal
from .candidates import get_profile
from .fsp import get_fsp
from .taxonomy import list_taxonomy

GRAPH_VERSION = "career-graph-2026-10"
_MAX_ADJACENT_PATHS = 4


def _fold(value: str | None) -> str:
    return " ".join(value.casefold().replace("/", " ").replace("-", " ").split()) if value else ""


def _skill_catalog(catalog: dict[str, Any]) -> dict[str, dict[str, Any]]:
    skills: dict[str, dict[str, Any]] = {}
    for specialization in catalog["specializations"]:
        for skill in specialization["skills"]:
            skills.setdefault(
                skill["slug"],
                {"slug": skill["slug"], "name": skill["name"]},
            )
    return skills


def _skill_slug(value: str, skills: dict[str, dict[str, Any]]) -> str | None:
    folded = _fold(value)
    for slug, skill in skills.items():
        if folded in {_fold(slug), _fold(skill["name"])}:
            return slug
    return None


def _freshness(measured_at: datetime | None) -> str:
    if measured_at is None:
        return "not_available"
    age_days = max(0, (datetime.now(measured_at.tzinfo) - measured_at).days)
    if age_days <= 365:
        return "fresh"
    if age_days <= 730:
        return "aging"
    return "stale"


def _specialization_for_assessment(
    catalog: dict[str, Any], specialization_name: str,
) -> dict[str, Any] | None:
    folded = _fold(specialization_name)
    return next(
        (item for item in catalog["specializations"] if _fold(item["name"]) == folded),
        None,
    )


def _grade_for_name(catalog: dict[str, Any], grade_name: str | None) -> dict[str, Any] | None:
    folded = _fold(grade_name)
    return next((item for item in catalog["grades"] if _fold(item["name"]) == folded), None)


def _grade_for_rank(catalog: dict[str, Any], rank: int) -> dict[str, Any] | None:
    return next((item for item in catalog["grades"] if item["rank"] == rank), None)


def _path(
    specialization: dict[str, Any],
    grade: dict[str, Any],
    *,
    evidence_slugs: set[str],
    verified_slugs: set[str],
    relation: str,
    current_specialization: str | None,
) -> dict[str, Any]:
    target_skills = {skill["slug"]: skill for skill in specialization["skills"]}
    matched_slugs = sorted(set(target_skills) & evidence_slugs)
    verified_matches = sorted(set(target_skills) & verified_slugs)
    gaps = [target_skills[slug]["name"] for slug in sorted(set(target_skills) - verified_slugs)]
    score = round(100 * len(matched_slugs) / len(target_skills)) if target_skills else 0

    if relation == "current":
        reasons = ["Current assessed category"]
    elif specialization["slug"] == current_specialization:
        reasons = ["Next grade in the current specialization"]
    else:
        reasons = ["Adjacent specialization shares evidence skills"]
    if gaps:
        reasons.append(f"Evidence gap: {', '.join(gaps)}")
    elif verified_matches:
        reasons.append("All mapped skills have verified evidence")

    return {
        "id": f"path:{specialization['slug']}:{grade['slug']}",
        "specialization": {
            "slug": specialization["slug"],
            "name": specialization["name"],
        },
        "grade": {
            "slug": grade["slug"],
            "name": grade["name"],
            "rank": grade["rank"],
        },
        "relation": relation,
        "readiness": "current" if relation == "current" else "explore",
        "match_score": score,
        "matched_skills": [target_skills[slug]["name"] for slug in matched_slugs],
        "gap_skills": gaps,
        "reasons": reasons,
        "evidence_basis": "verified_and_unconfirmed" if matched_slugs else "no_mapped_evidence",
    }


def get_career_graph(
    db: Session,
    principal: Principal,
    assessment_service: AssessmentService,
) -> dict[str, Any]:
    """Build a safe, self-scoped career graph from current evidence."""

    profile = get_profile(db, principal)
    fsp = get_fsp(db, principal)
    catalog = list_taxonomy(db)
    skills = _skill_catalog(catalog)
    attempts = assessment_service.history_for(principal.subject)
    submitted = [attempt for attempt in attempts if attempt.submitted]
    latest = submitted[-1] if submitted else None

    evidence_by_skill: dict[str, dict[str, Any]] = defaultdict(
        lambda: {
            "verified": 0,
            "unconfirmed": 0,
            "declared": 0,
            "freshness": "not_available",
            "sources": set(),
        }
    )

    current_specialization = _specialization_for_assessment(catalog, latest.specialization) if latest else None
    assessment_skill_slugs: set[str] = set()
    if current_specialization and latest:
        assessment_skill_slugs = {skill["slug"] for skill in current_specialization["skills"]}
        assessment_status = "verified" if latest.grade_state == "verified" else "unconfirmed"
        for slug in assessment_skill_slugs:
            evidence_by_skill[slug][assessment_status] += 1
            evidence_by_skill[slug]["sources"].add("platform_assessment")
            evidence_by_skill[slug]["freshness"] = _freshness(latest.created_at)

    for achievement in fsp["achievements"]:
        for raw_slug in achievement["mapped_skills"]:
            slug = _skill_slug(raw_slug, skills)
            if slug is None:
                continue
            evidence_by_skill[slug]["verified"] += 1
            evidence_by_skill[slug]["sources"].add("fsp")
            mapped_freshness = {
                "recent": "fresh",
                "aging": "aging",
                "old": "stale",
                "stale": "stale",
                "future": "future",
            }.get(achievement["recency_label"], "stale")
            if evidence_by_skill[slug]["freshness"] == "not_available" or mapped_freshness == "fresh":
                evidence_by_skill[slug]["freshness"] = mapped_freshness

    declared_custom: list[tuple[str, str]] = []
    declared_skill_slugs: set[str] = set()
    for index, raw_skill in enumerate(profile["skills"]):
        if not isinstance(raw_skill, str) or not raw_skill.strip():
            continue
        label = raw_skill.strip()
        slug = _skill_slug(label, skills)
        if slug is None:
            declared_custom.append((f"skill:declared:{index}", label))
            continue
        declared_skill_slugs.add(slug)
        evidence_by_skill[slug]["declared"] += 1
        evidence_by_skill[slug]["sources"].add("profile")

    evidence_slugs = set(evidence_by_skill)
    verified_slugs = {
        slug for slug, item in evidence_by_skill.items() if item["verified"] > 0
    }
    nodes: list[dict[str, Any]] = []
    if latest and current_specialization:
        current_grade = _grade_for_name(catalog, latest.declared_grade)
        nodes.append(
            {
                "id": f"position:{current_specialization['slug']}:{current_grade['slug'] if current_grade else 'unknown'}",
                "kind": "position",
                "label": current_specialization["name"],
                "status": "verified" if latest.grade_state == "verified" else "unconfirmed",
                "confidence": 1.0 if latest.grade_state == "verified" else 0.5,
                "evidence_count": 1,
                "freshness": _freshness(latest.created_at),
                "sources": ["platform_assessment"],
                "details": (
                    f"{latest.declared_grade} · grade verified"
                    if latest.grade_state == "verified"
                    else f"{latest.declared_grade} · grade not confirmed"
                ),
            }
        )

    for slug, item in sorted(evidence_by_skill.items(), key=lambda entry: skills.get(entry[0], {"name": entry[0]})["name"]):
        status = "verified" if item["verified"] else "unconfirmed" if item["unconfirmed"] else "declared"
        confidence = 1.0 if item["verified"] else 0.5 if item["unconfirmed"] else 0.25
        nodes.append(
            {
                "id": f"skill:{slug}",
                "kind": "skill",
                "label": skills.get(slug, {"name": slug})["name"],
                "status": status,
                "confidence": confidence,
                "evidence_count": item["verified"] + item["unconfirmed"] + item["declared"],
                "freshness": item["freshness"],
                "sources": sorted(item["sources"]),
                "details": "Verified evidence" if status == "verified" else "Declared skill; needs platform evidence",
            }
        )
    for node_id, label in declared_custom:
        nodes.append(
            {
                "id": node_id,
                "kind": "skill",
                "label": label,
                "status": "declared",
                "confidence": 0.25,
                "evidence_count": 1,
                "freshness": "not_available",
                "sources": ["profile"],
                "details": "Declared skill outside the active taxonomy",
            }
        )

    current_grade = _grade_for_name(catalog, latest.declared_grade) if latest else None
    current_slug = current_specialization["slug"] if current_specialization else None
    current_path: dict[str, Any] | None = None
    paths: list[dict[str, Any]] = []
    if current_specialization and current_grade:
        current_path = _path(
            current_specialization,
            current_grade,
            evidence_slugs=evidence_slugs,
            verified_slugs=verified_slugs,
            relation="current",
            current_specialization=current_slug,
        )
        paths.append(current_path)

        if latest.grade_state == "verified":
            next_grade = _grade_for_rank(catalog, current_grade["rank"] + 1)
            if next_grade:
                paths.append(
                    _path(
                        current_specialization,
                        next_grade,
                        evidence_slugs=evidence_slugs,
                        verified_slugs=verified_slugs,
                        relation="next",
                        current_specialization=current_slug,
                    )
                )

        adjacent: list[tuple[int, dict[str, Any], dict[str, Any]]] = []
        for specialization in catalog["specializations"]:
            if specialization["slug"] == current_slug:
                continue
            overlap = len({skill["slug"] for skill in specialization["skills"]} & evidence_slugs)
            if overlap == 0:
                continue
            target_grade = current_grade
            candidate_path = _path(
                specialization,
                target_grade,
                evidence_slugs=evidence_slugs,
                verified_slugs=verified_slugs,
                relation="adjacent",
                current_specialization=current_slug,
            )
            adjacent.append((candidate_path["match_score"], specialization, candidate_path))
        adjacent.sort(key=lambda item: (-item[0], item[1]["name"]))
        paths.extend(item[2] for item in adjacent[: _MAX_ADJACENT_PATHS - len(paths)])

    summary = {
        "verified_skills": len(verified_slugs),
        "unconfirmed_skills": len(
            [slug for slug, item in evidence_by_skill.items() if item["unconfirmed"] and not item["verified"]]
        ),
        "declared_skills": len(declared_skill_slugs) + len(declared_custom),
        "evidence_nodes": len(nodes),
        "path_count": len(paths),
        "gap_count": len({gap for path in paths for gap in path["gap_skills"]}),
    }
    return {
        "version": GRAPH_VERSION,
        "profile": {
            "display_name": profile["display_name"],
            "headline": profile["headline"],
        },
        "status": "not_started" if latest is None else "active" if latest.grade_state == "verified" else "unconfirmed",
        "current_position": (
            {
                "specialization": current_path["specialization"],
                "grade": current_path["grade"],
                "grade_state": latest.grade_state,
                "score": latest.score,
                "assessed_at": latest.created_at,
            }
            if latest and current_path
            else None
        ),
        "nodes": nodes,
        "paths": paths,
        "summary": summary,
        "next_step": (
            "Complete the base assessment to anchor your first career path."
            if latest is None
            else "Use the gaps as evidence targets; a path is not a hiring guarantee."
        ),
    }
