"""Replaceable, optional local-AI boundary for employer assistance."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal, Protocol

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


def context_from_hiring_need(need: dict[str, Any]) -> EmployerTaskDraftContext:
    """Convert the public hiring-need projection into adapter-safe context."""

    return EmployerTaskDraftContext(
        team=need["team"],
        role=need["role"],
        specialization=need["specialization"]["slug"],
        grade=need["grade"]["slug"],
        required_skills=tuple(skill["slug"] for skill in need["required_skills"]),
        preferred_skills=tuple(skill["slug"] for skill in need["preferred_skills"]),
    )
