"""Replaceable, optional local-AI boundary for employer assistance."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Literal, Protocol

import httpx
from pydantic import BaseModel, ConfigDict, Field, ValidationError
from sqlalchemy import text
from sqlalchemy.orm import Session

from .auth import Principal
from .companies import _ensure_company

LocalAiStatus = Literal["disabled", "completed", "failed"]


@dataclass(frozen=True)
class EmployerTaskDraftContext:
    """Sanitized employer-need context passed to a local adapter."""

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


class DraftRubricDimension(BaseModel):
    """The only rubric shape accepted from a local model."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=120)
    points: int = Field(gt=0, le=1000)
    description: str | None = Field(default=None, max_length=500)


class GeneratedEmployerTaskDraft(BaseModel):
    """Strict JSON contract for a proposed employer task.

    ``difficulty_rationale`` is advisory context for the employer and is not
    part of the persisted employer-task version.
    """

    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1, max_length=160)
    instructions: str = Field(min_length=1, max_length=12000)
    target_skills: list[str] = Field(min_length=1, max_length=20)
    expected_grade: Literal["junior", "middle", "senior"]
    estimated_minutes: int = Field(ge=5, le=480)
    deadline_hours: int = Field(ge=1, le=720)
    rubric: list[DraftRubricDimension] = Field(min_length=1, max_length=12)
    difficulty_rationale: str = Field(min_length=1, max_length=1000)


class DraftValidationError(ValueError):
    """Raised when a model response is valid JSON but unsafe for authoring."""


def validate_task_draft(
    draft: dict[str, Any] | None,
    context: EmployerTaskDraftContext,
) -> dict[str, Any]:
    """Validate a proposed draft against the current employer need.

    Schema validation alone is insufficient: a model could return a valid task
    for a different grade or introduce skills outside the current taxonomy
    context. Those cases are rejected before the response reaches the UI.
    """

    if not isinstance(draft, dict):
        raise DraftValidationError("draft_object_required")
    try:
        parsed = GeneratedEmployerTaskDraft.model_validate(draft)
    except ValidationError as exc:
        raise DraftValidationError("draft_schema_invalid") from exc

    title = parsed.title.strip()
    instructions = parsed.instructions.strip()
    rationale = parsed.difficulty_rationale.strip()
    if not title or not instructions or not rationale:
        raise DraftValidationError("draft_text_required")

    target_skills = [skill.strip() for skill in parsed.target_skills]
    if any(not skill for skill in target_skills) or len(set(target_skills)) != len(target_skills):
        raise DraftValidationError("draft_target_skills_invalid")
    available_skills = set(context.required_skills) | set(context.preferred_skills)
    if not set(target_skills).issubset(available_skills):
        raise DraftValidationError("draft_skill_outside_need")
    if not set(context.required_skills).issubset(target_skills):
        raise DraftValidationError("draft_required_skill_missing")
    if parsed.expected_grade != context.grade:
        raise DraftValidationError("draft_grade_mismatch")

    rubric = [
        {
            "name": item.name.strip(),
            "points": item.points,
            "description": item.description.strip() if item.description else None,
        }
        for item in parsed.rubric
    ]
    rubric_names = [item["name"] for item in rubric]
    if any(not name for name in rubric_names) or len(set(rubric_names)) != len(rubric_names):
        raise DraftValidationError("draft_rubric_invalid")
    if sum(item["points"] for item in rubric) <= 0:
        raise DraftValidationError("draft_rubric_points_required")

    return {
        "title": title,
        "instructions": instructions,
        "target_skills": target_skills,
        "expected_grade": parsed.expected_grade,
        "estimated_minutes": parsed.estimated_minutes,
        "deadline_hours": parsed.deadline_hours,
        "rubric": rubric,
        "difficulty_rationale": rationale,
    }


def build_task_draft_prompt(context: EmployerTaskDraftContext) -> str:
    """Build a bounded JSON-only prompt from sanitized employer data."""

    examples = [
        {
            "title": example.title,
            "instructions": example.instructions,
            "specialization": example.specialization,
            "grade": example.grade,
            "target_skills": list(example.target_skills),
            "estimated_minutes": example.estimated_minutes,
            "deadline_hours": example.deadline_hours,
            "rubric": list(example.rubric),
        }
        for example in context.approved_examples
    ]
    schema = json.dumps(GeneratedEmployerTaskDraft.model_json_schema(), ensure_ascii=False)
    return (
        "Create one employer-owned hiring task draft. Return only one JSON object "
        "matching this schema; do not use markdown or add fields. Include every "
        "required skill in target_skills, use only the current need skills, keep "
        "the current grade, and make rubric points positive. The draft is advisory "
        "and will be reviewed by a human.\n\n"
        f"JSON schema: {schema}\n"
        f"Current need: {json.dumps({'team': context.team, 'role': context.role, 'specialization': context.specialization, 'grade': context.grade, 'required_skills': list(context.required_skills), 'preferred_skills': list(context.preferred_skills)}, ensure_ascii=False)}\n"
        f"Approved employer examples: {json.dumps(examples, ensure_ascii=False)}"
    )


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


class LocalHttpAiAdapter:
    """Optional OpenAI-compatible local-runtime adapter.

    The adapter is deliberately small and stateless. It sends only the
    sanitized task context, requests JSON mode, and validates the response
    against the same domain contract used by the API boundary.
    """

    def __init__(self, base_url: str, model: str, timeout_seconds: float) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout_seconds = timeout_seconds

    async def propose_task_draft(self, context: EmployerTaskDraftContext) -> LocalAiDraftResult:
        if not self.model:
            return LocalAiDraftResult(
                status="failed",
                source="local",
                reason="local_ai_not_configured",
            )
        payload = {
            "model": self.model,
            "temperature": 0.2,
            "response_format": {"type": "json_object"},
            "messages": [
                {
                    "role": "system",
                    "content": "You are a constrained hiring-task drafting assistant.",
                },
                {"role": "user", "content": build_task_draft_prompt(context)},
            ],
        }
        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                response = await client.post(f"{self.base_url}/v1/chat/completions", json=payload)
                response.raise_for_status()
                body = response.json()
                content = body["choices"][0]["message"]["content"]
                if not isinstance(content, str):
                    raise TypeError("model_content_not_text")
                draft = validate_task_draft(json.loads(content), context)
        except (DraftValidationError, KeyError, TypeError, ValueError, json.JSONDecodeError, httpx.HTTPError):
            return LocalAiDraftResult(
                status="failed",
                source="local",
                reason="local_ai_invalid_or_unavailable",
            )
        return LocalAiDraftResult(status="completed", source="local", draft=draft)


def build_local_ai_port() -> LocalAiPort:
    """Build the configured adapter boundary.

    The local runtime is opt-in. Keeping construction here prevents routes
    from knowing which implementation is active and preserves the AI-off path.
    """

    from .config import get_settings

    settings = get_settings()
    if not settings.local_ai_enabled:
        return DisabledLocalAiAdapter()
    return LocalHttpAiAdapter(
        base_url=settings.local_ai_base_url,
        model=settings.local_ai_model,
        timeout_seconds=settings.local_ai_timeout_seconds,
    )


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
