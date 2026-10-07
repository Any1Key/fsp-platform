"""Calibrated, session-specific base assessment domain.

This module intentionally has no FastAPI or database dependency.  The
process-local repository is a bootstrap adapter; M00 will replace it with a
PostgreSQL repository without changing the domain rules.
"""

from __future__ import annotations

import hmac
import secrets
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from typing import Any
from uuid import uuid4

GRADES = ("Junior", "Middle", "Senior")
RETEST_COOLDOWN_DAYS = 90
EXPOSURE_COOLDOWN = timedelta(minutes=30)


@dataclass(frozen=True)
class TemplateFamily:
    family_id: str
    domain: str
    difficulty: int
    prompt: str
    options: tuple[str, ...]
    correct_option: int
    progressive: bool = False
    anchor: bool = False
    hidden_check_terms: tuple[tuple[str, ...], ...] = ()


@dataclass(frozen=True)
class Blueprint:
    specialization: str
    grade: str
    family_ids: tuple[str, ...]


@dataclass(frozen=True)
class AssessmentItem:
    item_id: str
    family_id: str
    domain: str
    difficulty: int
    prompt: str
    options: tuple[str, ...]
    progressive: bool
    anchor: bool
    artifact: str


@dataclass(frozen=True)
class HiddenCheck:
    """Server-only deterministic concepts for a progressive response."""

    required_concepts: tuple[tuple[str, ...], ...]


@dataclass
class Attempt:
    attempt_id: str
    candidate_id: str
    specialization: str
    declared_grade: str
    seed: str
    created_at: datetime
    items: tuple[AssessmentItem, ...]
    answer_keys: dict[str, int]
    followup_keys: dict[str, str]
    hidden_checks: dict[str, HiddenCheck]
    submitted: bool = False
    score: float | None = None
    grade_state: str | None = None
    integrity_signals: list[str] = field(default_factory=list)


TEMPLATES: dict[str, TemplateFamily] = {
    "runtime-1": TemplateFamily("runtime-1", "language_runtime", 2, "Для функции {fn} какое свойство гарантирует корректный результат?", ("Идемпотентность", "Случайный порядок", "Общий mutable state"), 0),
    "runtime-2": TemplateFamily("runtime-2", "language_runtime", 3, "В варианте {value} какая оптимизация сохраняет семантику?", ("Мемоизация чистого вызова", "Удаление проверки ошибок", "Глобальный кэш без ключа"), 0),
    "api-1": TemplateFamily("api-1", "api_fundamentals", 2, "Для повторного {verb} запроса API должен быть безопасен благодаря чему?", ("Идемпотентности", "Случайному токену", "Непредсказуемому статусу"), 0),
    "api-2": TemplateFamily(
        "api-2", "api_fundamentals", 3,
        "При таймауте downstream для {route} правильная стратегия —",
        ("bounded retry с backoff и лимитом", "бесконечный retry", "скрыть ошибку и вернуть 200"),
        0, True,
        hidden_check_terms=(("retry", "повтор"), ("backoff", "задерж"), ("лимит", "limit", "bounded")),
    ),
    "sql-1": TemplateFamily("sql-1", "sql_data", 2, "Какой индекс подходит для фильтра по {column} и сортировки по {sort}?", ("составной индекс в порядке фильтра и сортировки", "индекс на случайный столбец", "индекс не влияет на план"), 0),
    "sql-2": TemplateFamily(
        "sql-2", "sql_data", 3,
        "После изменения схемы {schema} как сохранить атомарность миграции?",
        ("транзакция и обратимо проверяемый шаг", "изменить production вручную", "пропустить проверку"),
        0, True, True,
        hidden_check_terms=(("транзак", "transaction"), ("откат", "rollback", "обратим")),
    ),
    "test-1": TemplateFamily("test-1", "testing_debugging", 2, "Какой тест лучше ловит регрессию в {component}?", ("детерминированный тест поведения", "тест только внутреннего имени", "случайная задержка"), 0),
    "test-2": TemplateFamily(
        "test-2", "testing_debugging", 3,
        "В тесте {fixture} результат нестабилен. Первый шаг —",
        ("найти источник недетерминизма и зафиксировать seed", "увеличить timeout без анализа", "удалить тест"),
        0, True,
        hidden_check_terms=(("недетермин", "determin"), ("seed", "случайн", "воспроизвод")),
    ),
    "arch-1": TemplateFamily("arch-1", "architecture", 2, "Для границы {boundary} зависимость должна идти через", ("явный порт/интерфейс", "глобальную переменную", "циклический импорт"), 0),
    "arch-2": TemplateFamily(
        "arch-2", "architecture", 3,
        "При росте {load} первым контролем должен быть",
        ("измеримый budget и p95", "неограниченное масштабирование", "отключение логирования"),
        0, True,
        hidden_check_terms=(("budget", "бюджет", "лимит"), ("p95", "латент", "метрик")),
    ),
    "sec-1": TemplateFamily("sec-1", "security_operations", 2, "Для данных {data} минимально необходимый контроль —", ("RBAC и минимизация хранения", "писать секреты в лог", "открыть доступ всем"), 0),
    "sec-2": TemplateFamily("sec-2", "security_operations", 3, "При подозрении на {event} безопаснее всего —", ("аудитировать событие без утечки содержимого", "переслать PII в чат", "игнорировать"), 0, True, True),
}

BLUEPRINTS = {
    ("Backend Engineering", grade): Blueprint(
        "Backend Engineering", grade,
        ("runtime-1", "runtime-2", "api-1", "api-2", "sql-1", "sql-2", "test-1", "test-2", "arch-1", "arch-2", "sec-1", "sec-2"),
    )
    for grade in GRADES
}


def _variant(seed: str, family: TemplateFamily, index: int) -> tuple[str, str]:
    digest = hmac.new(seed.encode(), f"{family.family_id}:{index}".encode(), sha256).hexdigest()
    tokens = ("alpha", "beta", "gamma", "delta", "omega", "sigma")
    token = tokens[int(digest[:2], 16) % len(tokens)]
    values = {
        "fn": f"normalize_{token}", "value": f"payload-{digest[2:8]}",
        "verb": "PUT", "route": f"/v1/items/{digest[8:14]}",
        "column": f"tenant_{token}", "sort": "created_at DESC",
        "schema": f"v{int(digest[14:16], 16) % 9 + 1}", "fixture": digest[16:22],
        "component": f"worker-{token}", "boundary": f"adapter-{token}",
        "load": f"{int(digest[22:24], 16) + 20} req/s", "data": "minor-consent metadata",
        "event": f"anomaly-{digest[24:30]}",
    }
    return family.prompt.format(**values), f"session-artifact:{digest[30:46]}"


def _select_families(blueprint: Blueprint, seed: str) -> list[TemplateFamily]:
    families = [TEMPLATES[item] for item in blueprint.family_ids]
    # Deterministic rotation yields equivalent domain coverage but different
    # family order; the seed also controls the concrete session artifact.
    offset = int(seed[:8], 16) % len(families)
    rotated = families[offset:] + families[:offset]
    return rotated


class AssessmentError(ValueError):
    pass


class AssessmentService:
    def __init__(self, *, now: datetime | None = None) -> None:
        self.attempts: dict[str, Attempt] = {}
        self.history: dict[str, list[str]] = {}
        self.family_exposure: dict[str, list[datetime]] = {}
        self.now = now or datetime.now(UTC)

    def create_attempt(self, candidate_id: str, specialization: str, declared_grade: str) -> Attempt:
        blueprint = BLUEPRINTS.get((specialization, declared_grade))
        if not blueprint:
            raise AssessmentError("unsupported specialization or grade")
        recent = [self.attempts[item] for item in self.history.get(candidate_id, [])]
        if recent and self.now - recent[-1].created_at < timedelta(days=RETEST_COOLDOWN_DAYS):
            raise AssessmentError("retest_locked_until_90_days")
        seed = secrets.token_hex(16)
        families = _select_families(blueprint, seed)
        if recent:
            previous = {item.family_id for item in recent[-1].items}
            families = sorted(families, key=lambda family: family.family_id in previous)
        # Keep the competency shape calibrated: one family per domain plus two
        # hidden anchors. The seed changes order/parameters, not the measured
        # domains, so equivalent forms remain comparable.
        selected: list[TemplateFamily] = []
        for family in families:
            if family.domain not in {item.domain for item in selected}:
                selected.append(family)
        for family in families:
            if family.anchor and family not in selected:
                selected.append(family)
        selected = selected[:8]
        items: list[AssessmentItem] = []
        answer_keys: dict[str, int] = {}
        followup_keys: dict[str, str] = {}
        hidden_checks: dict[str, HiddenCheck] = {}
        for index, family in enumerate(selected):
            prompt, artifact = _variant(seed, family, index)
            item_id = f"item-{uuid4().hex}"
            item = AssessmentItem(item_id, family.family_id, family.domain, family.difficulty, prompt, family.options, family.progressive, family.anchor, artifact)
            items.append(item)
            answer_keys[item_id] = family.correct_option
            followup_keys[item_id] = artifact
            if family.hidden_check_terms:
                hidden_checks[item_id] = HiddenCheck(family.hidden_check_terms)
            exposed = self.family_exposure.setdefault(family.family_id, [])
            exposed[:] = [stamp for stamp in exposed if self.now - stamp < EXPOSURE_COOLDOWN]
            if len(exposed) >= 3:
                raise AssessmentError("template_family_exposure_budget_reached")
            exposed.append(self.now)
        attempt = Attempt(
            uuid4().hex,
            candidate_id,
            specialization,
            declared_grade,
            seed,
            self.now,
            tuple(items),
            answer_keys,
            followup_keys,
            hidden_checks,
        )
        self.attempts[attempt.attempt_id] = attempt
        self.history.setdefault(candidate_id, []).append(attempt.attempt_id)
        return attempt

    def get(self, attempt_id: str) -> Attempt:
        try:
            return self.attempts[attempt_id]
        except KeyError as exc:
            raise AssessmentError("attempt_not_found") from exc

    def history_for(self, candidate_id: str) -> tuple[Attempt, ...]:
        """Return this candidate's attempts in creation order.

        The bootstrap repository is process-local, but the projection keeps
        the ownership boundary explicit so callers cannot accidentally list a
        different candidate's assessment history.
        """

        return tuple(
            self.attempts[attempt_id]
            for attempt_id in self.history.get(candidate_id, [])
            if attempt_id in self.attempts
        )

    def submit(self, attempt_id: str, answers: dict[str, int], followups: dict[str, str] | None = None, telemetry: dict[str, Any] | None = None) -> Attempt:
        attempt = self.get(attempt_id)
        if attempt.submitted:
            raise AssessmentError("attempt_already_submitted")
        if set(answers) != set(attempt.answer_keys):
            raise AssessmentError("all_items_are_required")
        base_points = sum(answers[item_id] == expected for item_id, expected in attempt.answer_keys.items())
        progressive_ids = [item.item_id for item in attempt.items if item.progressive]
        followup_points = 0
        hidden_check_failed = False
        for item_id in progressive_ids:
            response = (followups or {}).get(item_id, "")
            if not response.strip():
                continue
            if answers[item_id] != attempt.answer_keys[item_id]:
                continue
            hidden_check = attempt.hidden_checks.get(item_id)
            if hidden_check is None or _passes_hidden_check(response, hidden_check):
                followup_points += 1
            else:
                hidden_check_failed = True
        max_points = len(attempt.items) + len(progressive_ids)
        attempt.score = round((base_points + followup_points * 0.5) / (max_points + len(progressive_ids) * 0.5) * 100, 2)
        attempt.grade_state = "verified" if attempt.score >= 70 else "not_confirmed"
        signals: list[str] = []
        if telemetry and telemetry.get("focus_loss_count", 0) >= 3:
            signals.append("repeated_focus_loss_review")
        if telemetry and telemetry.get("paste_chars", 0) >= 1500:
            signals.append("large_paste_review")
        if followups and any(item_id in followups and not followups[item_id].strip() for item_id in progressive_ids):
            signals.append("missing_progressive_explanation_review")
        if hidden_check_failed:
            signals.append("hidden_check_review")
        attempt.integrity_signals = signals
        attempt.submitted = True
        return attempt


def _passes_hidden_check(response: str, check: HiddenCheck) -> bool:
    normalized = " ".join(response.casefold().split())
    return all(
        any(term.casefold() in normalized for term in concept_group)
        for concept_group in check.required_concepts
    )


def public_attempt(attempt: Attempt) -> dict[str, Any]:
    """Serialize an attempt without answer keys or scoring internals."""
    return {
        "attempt_id": attempt.attempt_id,
        "specialization": attempt.specialization,
        "declared_grade": attempt.declared_grade,
        "status": "submitted" if attempt.submitted else "in_progress",
        "items": [
            {"item_id": item.item_id, "family_id": item.family_id, "domain": item.domain, "difficulty": item.difficulty, "prompt": item.prompt, "options": item.options, "progressive": item.progressive, "artifact": item.artifact}
            for item in attempt.items
        ],
        **({"score": attempt.score, "grade_state": attempt.grade_state, "integrity_signals": attempt.integrity_signals} if attempt.submitted else {}),
    }


def public_history_item(attempt: Attempt) -> dict[str, Any]:
    """Serialize the dashboard-safe part of an attempt."""

    return {
        "attempt_id": attempt.attempt_id,
        "specialization": attempt.specialization,
        "declared_grade": attempt.declared_grade,
        "status": "submitted" if attempt.submitted else "in_progress",
        "score": attempt.score,
        "grade_state": attempt.grade_state,
        "created_at": attempt.created_at,
    }
