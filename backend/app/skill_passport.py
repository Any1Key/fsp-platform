"""Candidate-owned Verified Skill Passport projection.

The passport is a read-time composition of already-owned evidence boundaries.
It deliberately does not persist a second copy of assessment or FSP evidence,
and it never includes protected profile or assessment scoring internals.
"""

from __future__ import annotations

from datetime import UTC, date, datetime, time, timedelta
from typing import Any

from sqlalchemy.orm import Session

from .assessments import RETEST_COOLDOWN_DAYS, AssessmentService
from .auth import Principal
from .candidates import get_profile
from .fsp import get_fsp
from .taxonomy import list_taxonomy

ASSESSMENT_FRESH_DAYS = 365
ASSESSMENT_AGING_DAYS = 730


def _assessment_freshness(measured_at: datetime, *, now: datetime) -> str:
    age = now - measured_at
    if age < timedelta(0):
        return "fresh"
    if age <= timedelta(days=ASSESSMENT_FRESH_DAYS):
        return "fresh"
    if age <= timedelta(days=ASSESSMENT_AGING_DAYS):
        return "aging"
    return "stale"


def _date_as_utc(value) -> datetime:
    if isinstance(value, str):
        value = date.fromisoformat(value)
    return datetime.combine(value, time.min, tzinfo=UTC)


def _passport_freshness(value: str) -> str:
    return {
        "recent": "fresh",
        "aging": "aging",
        "old": "stale",
        "stale": "stale",
        "future": "future",
    }.get(value, "stale")


def _taxonomy_skill_names(catalog: dict[str, Any]) -> dict[str, str]:
    return {
        skill["slug"]: skill["name"]
        for specialization in catalog["specializations"]
        for skill in specialization["skills"]
    }


def _current_assessment(assessment_service: AssessmentService, subject: str) -> tuple[Any | None, list[Any]]:
    attempts = assessment_service.history_for(subject)
    submitted = [attempt for attempt in attempts if attempt.submitted]
    latest = submitted[-1] if submitted else None
    return latest, attempts


def get_skill_passport(
    db: Session,
    principal: Principal,
    assessment_service: AssessmentService,
) -> dict[str, Any]:
    """Build a safe, self-scoped evidence graph for the candidate passport."""

    profile = get_profile(db, principal)
    latest, attempts = _current_assessment(assessment_service, principal.subject)
    fsp = get_fsp(db, principal)
    catalog = list_taxonomy(db)
    skill_names = _taxonomy_skill_names(catalog)
    now = datetime.now(UTC)
    evidence: list[dict[str, Any]] = []

    category: dict[str, Any] | None = None
    if latest is not None and latest.score is not None and latest.grade_state:
        category = {
            "specialization": latest.specialization,
            "grade": latest.declared_grade if latest.grade_state == "verified" else None,
            "declared_grade": latest.declared_grade,
            "grade_state": latest.grade_state,
            "score": latest.score,
            "assessed_at": latest.created_at,
            "freshness": _assessment_freshness(latest.created_at, now=now),
        }
        specialization_slug = next(
            (
                item["slug"]
                for item in catalog["specializations"]
                if item["name"] == latest.specialization
            ),
            None,
        )
        assessment_skills = [
            skill["name"]
            for item in catalog["specializations"]
            if item["slug"] == specialization_slug
            for skill in item["skills"]
        ]
        evidence.append(
            {
                "id": f"assessment:{latest.attempt_id}",
                "source": "platform_assessment",
                "status": "verified" if latest.grade_state == "verified" else "unconfirmed",
                "title": f"{latest.specialization} · {latest.declared_grade}",
                "skills": assessment_skills,
                "score": latest.score,
                "confidence": 1.0 if latest.grade_state == "verified" else 0.5,
                "measured_at": latest.created_at,
                "freshness": category["freshness"],
                "provenance": "Platform system-scored base assessment",
                "details": (
                    "Grade confirmed by the platform rubric."
                    if latest.grade_state == "verified"
                    else "Declared grade remains visible; this assessment did not confirm it."
                ),
            }
        )

    for achievement in fsp["achievements"]:
        mapped_skills = [skill_names.get(slug, slug) for slug in achievement["mapped_skills"]]
        if not mapped_skills and achievement["mapped_specialization"]:
            mapped_skills = [achievement["mapped_specialization"]]
        evidence.append(
            {
                "id": f"fsp:{achievement['id']}",
                "source": "fsp",
                "status": "verified",
                "title": achievement["event_name"],
                "skills": mapped_skills,
                "score": achievement["result_score"],
                "confidence": 1.0 if achievement["verification"] else 0.0,
                "measured_at": _date_as_utc(achievement["event_date"]),
                "freshness": _passport_freshness(achievement["recency_label"]),
                "provenance": achievement["verification"],
                "details": achievement["result"] or achievement["result_label"],
            }
        )

    declared_skills = profile["skills"]
    for index, skill in enumerate(declared_skills):
        if not isinstance(skill, str) or not skill.strip():
            continue
        evidence.append(
            {
                "id": f"profile:{index}",
                "source": "profile",
                "status": "declared",
                "title": skill.strip(),
                "skills": [skill.strip()],
                "score": None,
                "confidence": 0.25,
                "measured_at": None,
                "freshness": "not_available",
                "provenance": "Candidate-entered profile",
                "details": "Declared skill; it is not platform verification.",
            }
        )

    freshness_counts = {
        state: sum(1 for item in evidence if item["freshness"] == state)
        for state in ("fresh", "aging", "stale", "future", "not_available")
    }
    passport_status = (
        "not_started"
        if latest is None
        else "verified"
        if latest.grade_state == "verified"
        else "unconfirmed"
    )
    latest_attempt = attempts[-1] if attempts else None
    return {
        "profile": {
            "display_name": profile["display_name"],
            "headline": profile["headline"],
        },
        "status": passport_status,
        "category": category,
        "fsp": {
            "status": fsp["status"],
            "history_status": fsp["history_status"],
            "achievement_count": len(fsp["achievements"]),
        },
        "freshness": freshness_counts,
        "retest_available_at": (
            latest_attempt.created_at + timedelta(days=RETEST_COOLDOWN_DAYS)
            if latest_attempt is not None
            else None
        ),
        "evidence": evidence,
    }
