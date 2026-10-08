"""Replaceable, optional local-AI boundary for employer assistance."""

from __future__ import annotations

import asyncio
import json
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Literal, Protocol
from uuid import uuid4

import httpx
from pydantic import BaseModel, ConfigDict, Field, ValidationError
from sqlalchemy import text
from sqlalchemy.orm import Session, sessionmaker

from .auth import Principal
from .companies import _ensure_company

LocalAiStatus = Literal["disabled", "completed", "failed"]
DraftFeedbackDecision = Literal["approved", "edited", "rejected"]
LocalAiJobStatus = Literal["queued", "running", "completed", "failed"]


class LocalAiRateLimitError(RuntimeError):
    """Raised when one employer has too many optional AI jobs."""

    def __init__(self, retry_after_seconds: int) -> None:
        super().__init__("local_ai_rate_limited")
        self.retry_after_seconds = retry_after_seconds


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


_LOCAL_AI_EXECUTOR = ThreadPoolExecutor(max_workers=1, thread_name_prefix="fsp-local-ai")


def _example_snapshot(example: ApprovedEmployerTaskExample) -> dict[str, Any]:
    return {
        "example_id": example.example_id,
        "task_version_id": example.task_version_id,
        "title": example.title,
        "instructions": example.instructions,
        "specialization": example.specialization,
        "grade": example.grade,
        "target_skills": list(example.target_skills),
        "estimated_minutes": example.estimated_minutes,
        "deadline_hours": example.deadline_hours,
        "rubric": list(example.rubric),
        "approved_at": example.approved_at.isoformat(),
        "relevance_score": example.relevance_score,
        "matched_required_skills": list(example.matched_required_skills),
        "matched_preferred_skills": list(example.matched_preferred_skills),
    }


def _context_snapshot(context: EmployerTaskDraftContext) -> dict[str, Any]:
    """Serialize only sanitized employer-need data into the durable job row."""

    return {
        "team": context.team,
        "role": context.role,
        "specialization": context.specialization,
        "grade": context.grade,
        "required_skills": list(context.required_skills),
        "preferred_skills": list(context.preferred_skills),
        "approved_examples": [_example_snapshot(example) for example in context.approved_examples],
    }


def _context_from_snapshot(snapshot: dict[str, Any]) -> EmployerTaskDraftContext:
    examples = tuple(
        ApprovedEmployerTaskExample(
            example_id=example["example_id"],
            task_version_id=example["task_version_id"],
            title=example["title"],
            instructions=example["instructions"],
            specialization=example["specialization"],
            grade=example["grade"],
            target_skills=tuple(example["target_skills"]),
            estimated_minutes=example["estimated_minutes"],
            deadline_hours=example["deadline_hours"],
            rubric=tuple(example["rubric"]),
            approved_at=datetime.fromisoformat(example["approved_at"]),
            relevance_score=example["relevance_score"],
            matched_required_skills=tuple(example["matched_required_skills"]),
            matched_preferred_skills=tuple(example["matched_preferred_skills"]),
        )
        for example in snapshot.get("approved_examples", [])
    )
    return EmployerTaskDraftContext(
        team=snapshot["team"],
        role=snapshot["role"],
        specialization=snapshot["specialization"],
        grade=snapshot["grade"],
        required_skills=tuple(snapshot["required_skills"]),
        preferred_skills=tuple(snapshot["preferred_skills"]),
        approved_examples=examples,
    )


def _result_payload(result: LocalAiDraftResult) -> dict[str, Any]:
    return {
        "status": result.status,
        "source": result.source,
        "reason": result.reason,
        "draft": result.draft,
    }


def _decode_json(value: Any) -> Any:
    return json.loads(value) if isinstance(value, str) else value


def enqueue_task_draft_job(
    db: Session,
    principal: Principal,
    *,
    hiring_need_id: str,
    context: EmployerTaskDraftContext,
    rate_limit_per_minute: int,
    max_active_jobs: int,
) -> str:
    """Create a durable, company-scoped local-AI job after limit checks."""

    identity_id, company_id = _ensure_company(db, principal)
    now = datetime.now(UTC)
    window_start = now.timestamp() - 60
    recent_count = int(
        db.execute(
            text(
                "SELECT COUNT(*) FROM employer_task_draft_job "
                "WHERE company_id = :company_id AND created_at >= :window_start"
            ),
            {"company_id": company_id, "window_start": datetime.fromtimestamp(window_start, UTC)},
        ).scalar_one()
    )
    if recent_count >= max(1, rate_limit_per_minute):
        raise LocalAiRateLimitError(60)

    active_count = int(
        db.execute(
            text(
                "SELECT COUNT(*) FROM employer_task_draft_job "
                "WHERE company_id = :company_id AND status IN ('queued', 'running')"
            ),
            {"company_id": company_id},
        ).scalar_one()
    )
    if active_count >= max(1, max_active_jobs):
        raise LocalAiRateLimitError(5)

    job_id = str(uuid4())
    db.execute(
        text(
            "INSERT INTO employer_task_draft_job "
            "(id, company_id, hiring_need_id, created_by_identity_id, status, "
            "context_snapshot, attempts, created_at) "
            "VALUES (:id, :company_id, :need_id, :identity_id, 'queued', "
            ":context_snapshot, 0, :created_at)"
        ),
        {
            "id": job_id,
            "company_id": company_id,
            "need_id": hiring_need_id,
            "identity_id": identity_id,
            "context_snapshot": json.dumps(_context_snapshot(context), ensure_ascii=False),
            "created_at": now,
        },
    )
    db.commit()
    return job_id


def get_task_draft_job(db: Session, principal: Principal, job_id: str) -> dict[str, Any] | None:
    """Return a job only when it belongs to the employer's company."""

    _, company_id = _ensure_company(db, principal)
    row = db.execute(
        text(
            "SELECT id, status, context_snapshot, result, created_at, started_at, completed_at, attempts "
            "FROM employer_task_draft_job WHERE id = :job_id AND company_id = :company_id"
        ),
        {"job_id": job_id, "company_id": company_id},
    ).mappings().one_or_none()
    if row is None:
        return None
    return {
        **dict(row),
        "context_snapshot": _decode_json(row["context_snapshot"]),
        "result": _decode_json(row["result"]) if row["result"] is not None else None,
    }


def run_task_draft_job(
    job_id: str,
    adapter: LocalAiPort,
    bind: Any,
    timeout_seconds: float,
) -> None:
    """Claim and execute one job outside the request thread."""

    factory = sessionmaker(bind=bind, autoflush=False, expire_on_commit=False)
    with factory() as db:
        row = db.execute(
            text(
                "SELECT context_snapshot FROM employer_task_draft_job "
                "WHERE id = :job_id AND status = 'queued'"
            ),
            {"job_id": job_id},
        ).mappings().one_or_none()
        if row is None:
            return
        claimed = db.execute(
            text(
                "UPDATE employer_task_draft_job SET status = 'running', "
                "started_at = :started_at, attempts = attempts + 1 "
                "WHERE id = :job_id AND status = 'queued'"
            ),
            {"job_id": job_id, "started_at": datetime.now(UTC)},
        )
        if claimed.rowcount != 1:
            return
        db.commit()

        try:
            context = _context_from_snapshot(_decode_json(row["context_snapshot"]))
            result = asyncio.run(
                asyncio.wait_for(adapter.propose_task_draft(context), timeout=timeout_seconds)
            )
            if result.status == "completed":
                try:
                    draft = validate_task_draft(result.draft, context)
                except DraftValidationError:
                    result = LocalAiDraftResult(
                        status="failed", source=result.source, reason="local_ai_invalid_draft"
                    )
                else:
                    result = LocalAiDraftResult(
                        status="completed", source=result.source, reason=result.reason, draft=draft
                    )
        except TimeoutError:
            result = LocalAiDraftResult(
                status="failed", source="local", reason="local_ai_timeout"
            )
        except Exception:  # noqa: BLE001  # Optional AI failures stay out of request logs.
            result = LocalAiDraftResult(
                status="failed", source="local", reason="local_ai_job_failed"
            )

        db.execute(
            text(
                "UPDATE employer_task_draft_job SET status = :status, result = :result, "
                "completed_at = :completed_at WHERE id = :job_id AND status = 'running'"
            ),
            {
                "job_id": job_id,
                "status": "completed" if result.status == "completed" else "failed",
                "result": json.dumps(_result_payload(result), ensure_ascii=False),
                "completed_at": datetime.now(UTC),
            },
        )
        db.commit()


def schedule_task_draft_job(
    job_id: str,
    adapter: LocalAiPort,
    bind: Any,
    timeout_seconds: float,
) -> None:
    """Submit optional work to the single CPU-local inference worker."""

    _LOCAL_AI_EXECUTOR.submit(run_task_draft_job, job_id, adapter, bind, timeout_seconds)


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


def _feedback_response(row: Any) -> dict[str, Any]:
    reviewed_draft = row["reviewed_draft"]
    need_snapshot = row["need_snapshot"]
    if isinstance(reviewed_draft, str):
        reviewed_draft = json.loads(reviewed_draft)
    if isinstance(need_snapshot, str):
        need_snapshot = json.loads(need_snapshot)
    return {
        "id": row["id"],
        "decision": row["decision"],
        "reviewed_draft": reviewed_draft,
        "feedback_note": row["feedback_note"],
        "need_snapshot": need_snapshot,
        "created_at": row["created_at"],
    }


def _need_snapshot(context: EmployerTaskDraftContext) -> dict[str, Any]:
    return {
        "team": context.team,
        "role": context.role,
        "specialization": context.specialization,
        "grade": context.grade,
        "required_skills": list(context.required_skills),
        "preferred_skills": list(context.preferred_skills),
    }


def record_draft_feedback(
    db: Session,
    principal: Principal,
    *,
    hiring_need_id: str,
    context: EmployerTaskDraftContext,
    decision: DraftFeedbackDecision,
    draft: dict[str, Any] | None,
    feedback_note: str | None,
) -> dict[str, Any]:
    """Persist an employer review without publishing or indexing a task.

    Only the employer's current need is accepted. Rejected feedback deliberately
    stores no generated content; approved and edited feedback stores the
    need-validated draft so the employer can audit what was reviewed.
    """

    if decision == "rejected":
        if draft is not None:
            raise DraftValidationError("feedback_rejected_draft_forbidden")
        reviewed_draft = None
    else:
        if draft is None:
            raise DraftValidationError("feedback_draft_required")
        reviewed_draft = validate_task_draft(draft, context)

    identity_id, company_id = _ensure_company(db, principal)
    owned_need = db.execute(
        text(
            "SELECT id FROM hiring_need WHERE id = :need_id AND company_id = :company_id"
        ),
        {"need_id": hiring_need_id, "company_id": company_id},
    ).scalar_one_or_none()
    if owned_need is None:
        raise DraftValidationError("feedback_need_not_owned")

    note = feedback_note.strip() if feedback_note else None
    feedback_id = str(uuid4())
    db.execute(
        text(
            "INSERT INTO employer_task_draft_feedback "
            "(id, company_id, hiring_need_id, decision, reviewed_draft, feedback_note, "
            "need_snapshot, created_by_identity_id, created_at) "
            "VALUES (:id, :company_id, :need_id, :decision, :reviewed_draft, :feedback_note, "
            ":need_snapshot, :identity_id, :created_at)"
        ),
        {
            "id": feedback_id,
            "company_id": company_id,
            "need_id": hiring_need_id,
            "decision": decision,
            "reviewed_draft": (
                json.dumps(reviewed_draft, ensure_ascii=False, separators=(",", ":"))
                if reviewed_draft is not None
                else None
            ),
            "feedback_note": note or None,
            "need_snapshot": json.dumps(_need_snapshot(context), ensure_ascii=False, separators=(",", ":")),
            "identity_id": identity_id,
            "created_at": datetime.now(UTC),
        },
    )
    db.commit()
    return _feedback_response(
        db.execute(
            text(
                "SELECT id, decision, reviewed_draft, feedback_note, need_snapshot, created_at "
                "FROM employer_task_draft_feedback WHERE id = :feedback_id"
            ),
            {"feedback_id": feedback_id},
        ).mappings().one()
    )


def list_draft_feedback(
    db: Session,
    principal: Principal,
    *,
    hiring_need_id: str,
    limit: int = 10,
) -> list[dict[str, Any]]:
    """Return recent feedback scoped to the current employer and need."""

    _, company_id = _ensure_company(db, principal)
    rows = db.execute(
        text(
            "SELECT id, decision, reviewed_draft, feedback_note, need_snapshot, created_at "
            "FROM employer_task_draft_feedback WHERE company_id = :company_id "
            "AND hiring_need_id = :need_id ORDER BY created_at DESC, id DESC LIMIT :limit"
        ),
        {
            "company_id": company_id,
            "need_id": hiring_need_id,
            "limit": max(0, min(limit, 20)),
        },
    ).mappings()
    return [_feedback_response(row) for row in rows]
