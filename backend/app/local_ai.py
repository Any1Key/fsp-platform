"""Replaceable, optional local-AI boundary for employer assistance."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Literal, Protocol

from sqlalchemy import text
from sqlalchemy.orm import Session

from .auth import Principal
from .companies import _ensure_company

LocalAiStatus = Literal["disabled", "completed", "failed"]


@dataclass(frozen=True)
class EmployerTaskDraftContext:
    """Sanitized employer-need context passed to a future adapter."""

    team: str
    role: str
    specialization: str
    grade: str
    required_skills: tuple[str, ...]
    preferred_skills: tuple[str, ...]
    approved_examples: tuple[ApprovedEmployerTaskExample, ...] = ()


@dataclass(frozen=True)
class ApprovedEmployerTaskExample:
    """Sanitized employer-owned task content supplied to an optional adapter."""

    example_id: str
    task_version_id: str
    title: str
    instructions: str
    specialization: str
    grade: str
    target_skills: tuple[str, ...]
    estimated_minutes: int
    deadline_hours: int
    rubric: tuple[dict[str, Any], ...]
    approved_at: datetime
    relevance_score: int
    matched_required_skills: tuple[str, ...]
    matched_preferred_skills: tuple[str, ...]


@dataclass(frozen=True)
class LocalAiDraftResult:
    """Adapter result safe to expose to the employer authoring UI."""

    status: LocalAiStatus
    source: Literal["disabled", "local"]
    reason: str | None = None
    draft: dict[str, Any] | None = None


class LocalAiPort(Protocol):
    """Async boundary for optional employer task assistance."""

    async def propose_task_draft(self, context: EmployerTaskDraftContext) -> LocalAiDraftResult:
        """Return a draft proposal without changing employer task state."""


class DisabledLocalAiAdapter:
    """Deterministic no-op adapter used when local AI is unavailable or off."""

    async def propose_task_draft(self, context: EmployerTaskDraftContext) -> LocalAiDraftResult:
        # Keep the argument in the method signature for adapter compatibility,
        # but do not inspect or retain employer data in the disabled path.
        del context
        return LocalAiDraftResult(
            status="disabled",
            source="disabled",
            reason="local_ai_disabled",
            draft=None,
        )


def build_local_ai_port() -> LocalAiPort:
    """Build the configured adapter boundary.

    Only the disabled adapter is available until an explicitly reviewed local
    runtime is added. Keeping construction here prevents routes from knowing
    which implementation is active.
    """

    return DisabledLocalAiAdapter()


def context_from_hiring_need(
    need: dict[str, Any],
    approved_examples: tuple[ApprovedEmployerTaskExample, ...] = (),
) -> EmployerTaskDraftContext:
    """Convert the public hiring-need projection into adapter-safe context."""

    return EmployerTaskDraftContext(
        team=need["team"],
        role=need["role"],
        specialization=need["specialization"]["slug"],
        grade=need["grade"]["slug"],
        required_skills=tuple(skill["slug"] for skill in need["required_skills"]),
        preferred_skills=tuple(skill["slug"] for skill in need["preferred_skills"]),
        approved_examples=approved_examples,
    )


def retrieve_approved_task_examples(
    db: Session,
    principal: Principal,
    context: EmployerTaskDraftContext,
    *,
    limit: int = 5,
) -> list[ApprovedEmployerTaskExample]:
    """Retrieve a bounded, deterministic memory for the current employer need.

    The query is scoped to the employer's company before any ranking occurs.
    Ranking is intentionally transparent and CPU-only: specialization and grade
    matches are stronger signals than required/preferred skill overlap, with
    publication recency as a stable tie-breaker.
    """

    _, company_id = _ensure_company(db, principal)
    rows = db.execute(
        text(
            "SELECT ete.id AS example_id, ete.task_version_id, etv.title, "
            "etv.instructions, ete.specialization_slug, ete.grade_slug, "
            "ete.target_skills, ete.estimated_minutes, ete.deadline_hours, "
            "etv.rubric, ete.approved_at "
            "FROM employer_task_example ete "
            "JOIN employer_task_version etv ON etv.id = ete.task_version_id "
            "WHERE ete.company_id = :company_id "
            "AND ete.approval_status = 'approved'"
        ),
        {"company_id": company_id},
    ).mappings()

    required = set(context.required_skills)
    preferred = set(context.preferred_skills)
    examples: list[ApprovedEmployerTaskExample] = []
    for row in rows:
        target_skills = row["target_skills"]
        rubric = row["rubric"]
        approved_at = row["approved_at"]
        if isinstance(approved_at, str):
            approved_at = datetime.fromisoformat(approved_at)
        if isinstance(target_skills, str):
            target_skills = json.loads(target_skills)
        if isinstance(rubric, str):
            rubric = json.loads(rubric)
        target_set = set(target_skills)
        matched_required = tuple(sorted(required & target_set))
        matched_preferred = tuple(sorted(preferred & target_set))
        relevance_score = (
            (100 if row["specialization_slug"] == context.specialization else 0)
            + (60 if row["grade_slug"] == context.grade else 0)
            + (20 * len(matched_required))
            + (8 * len(matched_preferred))
        )
        examples.append(
            ApprovedEmployerTaskExample(
                example_id=row["example_id"],
                task_version_id=row["task_version_id"],
                title=row["title"],
                instructions=row["instructions"],
                specialization=row["specialization_slug"],
                grade=row["grade_slug"],
                target_skills=tuple(target_skills),
                estimated_minutes=row["estimated_minutes"],
                deadline_hours=row["deadline_hours"],
                rubric=tuple(rubric),
                approved_at=approved_at,
                relevance_score=relevance_score,
                matched_required_skills=matched_required,
                matched_preferred_skills=matched_preferred,
            )
        )

    examples.sort(
        key=lambda example: (
            -example.relevance_score,
            -example.approved_at.timestamp(),
            example.example_id,
        )
    )
    return examples[: max(0, min(limit, 10))]
