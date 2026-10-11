"""Calibrated, session-specific base assessment domain.

This module intentionally has no FastAPI or database dependency.  The
process-local repository is a bootstrap adapter; M00 will replace it with a
PostgreSQL repository without changing the domain rules.
"""

from __future__ import annotations

import hmac
import re
import secrets
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from difflib import SequenceMatcher
from hashlib import sha256
from typing import Any
from uuid import uuid4

GRADES = ("Junior", "Middle", "Senior")
INDUSTRIES = (
    "IT / Software Development",
    "FinTech / Financial Services",
    "E-commerce / Retail",
    "Healthcare / MedTech",
    "Education / EdTech",
    "Telecom / Communications",
    "Logistics / Transport",
    "Public Sector / GovTech",
)
GRADE_RANK = {grade: index for index, grade in enumerate(GRADES)}
RETEST_COOLDOWN_DAYS = 90
EXPOSURE_COOLDOWN = timedelta(minutes=30)
CANONICAL_EXPOSURE_WINDOW = timedelta(days=90)
ASSESSMENT_FAMILY_VERSION = "2026-10-06"
ASSESSMENT_PROFILE_VERSION = "2026-10-11-context-v1"
SIMILARITY_MIN_TOKENS = 6
SIMILARITY_REVIEW_THRESHOLD = 0.86

_TEXT_TOKEN_PATTERN = re.compile(r"[^\W_]+", re.UNICODE)
_CODE_TOKEN_PATTERN = re.compile(
    r"[A-Za-z_][A-Za-z0-9_]*|\d+(?:\.\d+)?|===|!==|==|!=|<=|>=|=>|&&|\|\||[{}()[\];,.=:+*/%<>!-]"
)
_CODE_COMMENT_PATTERN = re.compile(r"/\*.*?\*/|//[^\n]*|#[^\n]*", re.DOTALL)
_CODE_KEYWORDS = frozenset(
    {
        "and",
        "async",
        "await",
        "class",
        "const",
        "def",
        "else",
        "for",
        "from",
        "function",
        "if",
        "import",
        "in",
        "let",
        "new",
        "not",
        "or",
        "return",
        "while",
        "with",
        "yield",
    }
)
_TEXT_BOILERPLATE = frozenset(
    {
        "a",
        "an",
        "and",
        "answer",
        "because",
        "choice",
        "i",
        "my",
        "option",
        "selected",
        "the",
        "this",
        "выбрал",
        "выбрала",
        "выбор",
        "потому",
        "что",
    }
)

_CANONICAL_EXPLANATIONS = {
    "runtime-1": "Idempotency keeps repeated evaluation of the same operation safe and predictable.",
    "runtime-2": "Memoization is safe here because a pure call returns the same value for the same input.",
    "api-1": "Idempotency makes repeating the request produce the same intended resource effect.",
    "api-2": "A bounded retry with backoff limits load amplification while allowing transient recovery.",
    "sql-1": "The composite index follows the filter and sort columns so the database can narrow and order efficiently.",
    "sql-2": "A transaction makes the schema change atomic, and a reversible step provides a safe rollback path.",
    "test-1": "A deterministic behavior test protects the observable contract instead of an implementation detail.",
    "test-2": "The source of nondeterminism must be isolated and the seed fixed so the failure is reproducible.",
    "arch-1": "An explicit port or interface keeps the boundary replaceable and prevents hidden coupling.",
    "arch-2": "A measurable budget and p95 latency establish whether the system is within its operating target.",
    "sec-1": "RBAC limits access and data minimization reduces the impact of any storage or access failure.",
    "sec-2": "Auditing the event without copying sensitive contents preserves evidence while limiting leakage.",
}


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
    canonical_explanation: str = ""
    version: str = ASSESSMENT_FAMILY_VERSION

    def __post_init__(self) -> None:
        if not self.canonical_explanation:
            object.__setattr__(
                self,
                "canonical_explanation",
                _CANONICAL_EXPLANATIONS[self.family_id],
            )


@dataclass(frozen=True)
class Blueprint:
    specialization: str
    grade: str
    family_ids: tuple[str, ...]


@dataclass(frozen=True)
class AssessmentFormation:
    """Deterministic explanation of how several hiring descriptions shape a form."""

    specialization: str
    grade: str
    source_count: int
    source_domains: tuple[str, ...]
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
    family_version: str


@dataclass(frozen=True)
class HiddenCheck:
    """Server-only deterministic concepts for a progressive response."""

    required_concepts: tuple[tuple[str, ...], ...]


@dataclass(frozen=True)
class SimilarityMatch:
    modality: str
    similarity: float

    def public(self, item_id: str) -> dict[str, Any]:
        return {
            "signal": "cross_submission_similarity_review",
            "modality": self.modality,
            "scope": "progressive_response",
            "item_id": item_id,
            "similarity": round(self.similarity, 2),
        }


@dataclass
class Attempt:
    attempt_id: str
    candidate_id: str
    industry: str
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
    integrity_evidence: list[dict[str, Any]] = field(default_factory=list)
    submitted_followups: dict[str, str] = field(default_factory=dict)
    canonical_available_at: dict[str, datetime] = field(default_factory=dict)


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

SPECIALIZATION_NAMES = (
    "Backend Engineering",
    "Frontend Engineering",
    "Full-stack Engineering",
    "QA / Test Automation",
    "DevOps / SRE",
    "Data Engineering",
    "Data Science / ML",
    "Mobile Engineering",
)
SPECIALIZATION_CONTEXTS = {
    "Backend Engineering": {
        "runtime": "сервисного кода и серверного runtime",
        "api": "backend API и интеграций",
        "sql": "серверной базы данных",
        "testing": "backend-тестов",
        "architecture": "распределённого backend-сервиса",
        "security": "серверных данных и доступа",
    },
    "Frontend Engineering": {
        "runtime": "клиентского TypeScript-кода",
        "api": "браузерного API-клиента",
        "sql": "данных, получаемых frontend через API",
        "testing": "UI- и компонентных тестов",
        "architecture": "frontend-приложения",
        "security": "браузерной сессии и пользовательских данных",
    },
    "Full-stack Engineering": {
        "runtime": "сквозного client-server сценария",
        "api": "полного API-сценария от UI до backend",
        "sql": "данных на границе приложения и базы",
        "testing": "сквозных тестов продукта",
        "architecture": "полного web-продукта",
        "security": "данных между браузером и сервером",
    },
    "QA / Test Automation": {
        "runtime": "тестового раннера",
        "api": "контрактных API-тестов",
        "sql": "проверки данных после тестового сценария",
        "testing": "автоматизированного тестового набора",
        "architecture": "тестовой инфраструктуры",
        "security": "тестовых данных и доступов",
    },
    "DevOps / SRE": {
        "runtime": "production runtime и worker-процессов",
        "api": "эксплуатационного API-сервиса",
        "sql": "надёжности хранилища",
        "testing": "проверок доставки и восстановления",
        "architecture": "инфраструктуры и отказоустойчивости",
        "security": "секретов и инфраструктурного доступа",
    },
    "Data Engineering": {
        "runtime": "pipeline runtime",
        "api": "сервисов загрузки данных",
        "sql": "таблиц и витрин данных",
        "testing": "контролей качества данных",
        "architecture": "потока данных",
        "security": "доступа к данным",
    },
    "Data Science / ML": {
        "runtime": "кода обучения и inference",
        "api": "сервинга ML-модели",
        "sql": "признаков и датасетов",
        "testing": "валидации модели",
        "architecture": "ML-пайплайна",
        "security": "данных обучения и предсказаний",
    },
    "Mobile Engineering": {
        "runtime": "мобильного приложения",
        "api": "мобильного API-клиента",
        "sql": "локального и серверного хранения",
        "testing": "мобильных UI- и интеграционных тестов",
        "architecture": "мобильного приложения",
        "security": "мобильной сессии и данных пользователя",
    },
}
GRADE_CONTEXTS = {
    "Junior": "базового уровня с явными ограничениями",
    "Middle": "самостоятельного production-уровня",
    "Senior": "уровня проектирования и эксплуатационных компромиссов",
}
ASSESSMENT_FAMILY_IDS = (
    "runtime-1", "runtime-2", "api-1", "api-2", "sql-1", "sql-2",
    "test-1", "test-2", "arch-1", "arch-2", "sec-1", "sec-2",
)

# The first calibrated question family is shared until specialization-specific
# forms are administered. Every catalog specialization is still validated by
# the same deterministic assessment contract and can be matched by its slug.
BLUEPRINTS = {
    (specialization, grade): Blueprint(specialization, grade, ASSESSMENT_FAMILY_IDS)
    for specialization in SPECIALIZATION_NAMES
    for grade in GRADES
}


def _variant(
    seed: str,
    family: TemplateFamily,
    index: int,
    *,
    specialization: str = "Backend Engineering",
    grade: str = "Middle",
    industry: str = INDUSTRIES[0],
) -> tuple[str, str]:
    digest = hmac.new(seed.encode(), f"{family.family_id}:{index}".encode(), sha256).hexdigest()
    tokens = ("alpha", "beta", "gamma", "delta", "omega", "sigma")
    token = tokens[int(digest[:2], 16) % len(tokens)]
    context = SPECIALIZATION_CONTEXTS[specialization]
    values = {
        "fn": f"normalize_{token}", "value": f"payload-{digest[2:8]}",
        "verb": "PUT", "route": f"/v1/items/{digest[8:14]}",
        "column": f"tenant_{token}", "sort": "created_at DESC",
        "schema": f"v{int(digest[14:16], 16) % 9 + 1}", "fixture": digest[16:22],
        "component": f"worker-{token}", "boundary": f"adapter-{token}",
        "load": f"{int(digest[22:24], 16) + 20} req/s", "data": "minor-consent metadata",
        "event": f"anomaly-{digest[24:30]}",
    }
    prompt = family.prompt.format(**values)
    domain_context = {
        "language_runtime": context["runtime"],
        "api_fundamentals": context["api"],
        "sql_data": context["sql"],
        "testing_debugging": context["testing"],
        "architecture": context["architecture"],
        "security_operations": context["security"],
    }.get(family.domain, context["runtime"])
    prompt = (
        f"[{specialization} · {grade} · {industry} · вариант {digest[:8]}] "
        f"Контекст: {domain_context}, {GRADE_CONTEXTS[grade]}. {prompt}"
    )
    return prompt, f"session-artifact:{ASSESSMENT_PROFILE_VERSION}:{digest[30:46]}"


def _select_families(blueprint: Blueprint, seed: str) -> list[TemplateFamily]:
    families = [TEMPLATES[item] for item in blueprint.family_ids]
    # Deterministic rotation yields equivalent domain coverage but different
    # family order; the seed also controls the concrete session artifact.
    offset = int(seed[:8], 16) % len(families)
    rotated = families[offset:] + families[:offset]
    return rotated


def form_assessment_from_descriptions(
    descriptions: tuple[str, ...] | list[str],
    *,
    specialization: str = "Backend Engineering",
    grade: str = "Middle",
) -> AssessmentFormation:
    """Build a reproducible blueprint summary from multiple hiring descriptions.

    Descriptions influence competency coverage only through an explicit keyword
    map; question wording and scoring remain template/grade controlled.
    """

    blueprint = BLUEPRINTS.get((specialization, grade))
    if not blueprint or not descriptions:
        raise AssessmentError("assessment_descriptions_required")
    text = " ".join(descriptions).casefold()
    domain_terms = {
        "api_fundamentals": ("api", "rest", "endpoint", "интеграц"),
        "sql_data": ("sql", "database", "баз данных", "postgres"),
        "testing_debugging": ("test", "тест", "debug", "качества"),
        "architecture": ("architecture", "архитект", "design", "систем"),
        "security_operations": ("security", "secure", "безопас", "privacy", "доступ"),
        "language_runtime": ("python", "java", "runtime", "код"),
    }
    domains = tuple(domain for domain, terms in domain_terms.items() if any(term in text for term in terms))
    selected = tuple(
        family_id for family_id in blueprint.family_ids
        if not domains or TEMPLATES[family_id].domain in domains
    )
    return AssessmentFormation(specialization, grade, len(descriptions), domains, selected)


class AssessmentError(ValueError):
    pass


def _grade_offers(attempt: Attempt) -> list[dict[str, str]]:
    if not attempt.submitted or attempt.score is None:
        return []
    rank = GRADE_RANK[attempt.declared_grade]
    offers: list[dict[str, str]] = []
    if attempt.score < 70 and rank > 0:
        offers.append({"grade": GRADES[rank - 1], "reason": "lower_grade_after_unconfirmed_result"})
    if attempt.score >= 80 and rank < len(GRADES) - 1:
        offers.append({"grade": GRADES[rank + 1], "reason": "higher_grade_after_strong_result"})
    return offers


class AssessmentService:
    def __init__(
        self,
        *,
        now: datetime | None = None,
        canonical_exposure_window: timedelta = CANONICAL_EXPOSURE_WINDOW,
        seed_factory: Callable[[], str] | None = None,
    ) -> None:
        if canonical_exposure_window <= timedelta(0):
            raise ValueError("canonical exposure window must be positive")
        self.attempts: dict[str, Attempt] = {}
        self.history: dict[str, list[str]] = {}
        self.form_signatures: set[tuple[tuple[str, str], ...]] = set()
        # Exposure limits are candidate-scoped. A global limit would make the
        # fourth person in a demo fail simply because three other people chose
        # the same specialization at the same time.
        self.family_exposure: dict[tuple[str, str], list[datetime]] = {}
        self.family_exposure_started: dict[tuple[str, str], datetime] = {}
        self.retired_families: set[tuple[str, str]] = set()
        self.canonical_exposure_window = canonical_exposure_window
        self._now_override = now
        self._seed_factory = seed_factory or (lambda: secrets.token_hex(16))

    @property
    def now(self) -> datetime:
        """Use a live UTC clock in production and a frozen clock in tests."""

        return self._now_override or datetime.now(UTC)

    @now.setter
    def now(self, value: datetime) -> None:
        self._now_override = value

    def create_attempt(
        self,
        candidate_id: str,
        specialization: str,
        declared_grade: str,
        *,
        industry: str = INDUSTRIES[0],
    ) -> Attempt:
        blueprint = BLUEPRINTS.get((specialization, declared_grade))
        if not blueprint:
            raise AssessmentError("unsupported specialization or grade")
        if industry not in INDUSTRIES:
            raise AssessmentError("unsupported industry")
        recent = [self.attempts[item] for item in self.history.get(candidate_id, [])]
        if recent and self.now - recent[-1].created_at < timedelta(days=RETEST_COOLDOWN_DAYS):
            latest = recent[-1]
            eligible = self.grade_offers(latest)
            if not latest.submitted or declared_grade not in {item["grade"] for item in eligible}:
                raise AssessmentError("retest_locked_until_90_days")
        seed = self._seed_factory()
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
        canonical_available_at: dict[str, datetime] = {}
        for index, family in enumerate(selected):
            prompt, artifact = _variant(
                seed,
                family,
                index,
                specialization=specialization,
                grade=declared_grade,
                industry=industry,
            )
            item_id = f"item-{uuid4().hex}"
            option_order = sorted(
                range(len(family.options)),
                key=lambda option_index: hmac.new(
                    seed.encode(),
                    f"{family.family_id}:option:{option_index}".encode(),
                    sha256,
                ).digest(),
            )
            options = tuple(family.options[option_index] for option_index in option_order)
            correct_option = option_order.index(family.correct_option)
            item = AssessmentItem(
                item_id,
                family.family_id,
                family.domain,
                family.difficulty,
                prompt,
                options,
                family.progressive,
                family.anchor,
                artifact,
                family.version,
            )
            items.append(item)
            answer_keys[item_id] = correct_option
            followup_keys[item_id] = artifact
            if family.hidden_check_terms:
                hidden_checks[item_id] = HiddenCheck(family.hidden_check_terms)
            exposed = self.family_exposure.setdefault((candidate_id, family.family_id), [])
            exposed[:] = [stamp for stamp in exposed if self.now - stamp < EXPOSURE_COOLDOWN]
            if len(exposed) >= 3:
                raise AssessmentError("template_family_exposure_budget_reached")
            exposed.append(self.now)
            exposure_key = (family.family_id, family.version)
            exposure_started = self.family_exposure_started.setdefault(exposure_key, self.now)
            canonical_available_at[item_id] = exposure_started + self.canonical_exposure_window
        attempt = Attempt(
            uuid4().hex,
            candidate_id,
            industry,
            specialization,
            declared_grade,
            seed,
            self.now,
            tuple(items),
            answer_keys,
            followup_keys,
            hidden_checks,
            canonical_available_at=canonical_available_at,
        )
        form_signature = tuple((item.family_id, item.artifact) for item in attempt.items)
        if form_signature in self.form_signatures:
            # A collision should never make a candidate unable to start a
            # test. Keep the calibrated family selection and regenerate only
            # session wording/artifacts from a candidate-scoped fallback seed.
            # This preserves comparable scoring while making uniqueness an
            # invariant even when the entropy source repeats a value.
            collision_seed = hmac.new(
                seed.encode(),
                f"{candidate_id}:{len(recent)}:{len(self.form_signatures)}".encode(),
                sha256,
            ).hexdigest()
            for index, item in enumerate(items):
                family = TEMPLATES[item.family_id]
                prompt, artifact = _variant(
                    collision_seed,
                    family,
                    index,
                    specialization=specialization,
                    grade=declared_grade,
                    industry=industry,
                )
                items[index] = AssessmentItem(
                    item.item_id,
                    item.family_id,
                    item.domain,
                    item.difficulty,
                    prompt,
                    item.options,
                    item.progressive,
                    item.anchor,
                    artifact,
                    item.family_version,
                )
                followup_keys[item.item_id] = artifact
            attempt.seed = collision_seed
            attempt.items = tuple(items)
            attempt.followup_keys = followup_keys
            form_signature = tuple((item.family_id, item.artifact) for item in attempt.items)
            if form_signature in self.form_signatures:
                raise AssessmentError("assessment_form_collision")
        self.form_signatures.add(form_signature)
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

    def retire_family(self, family_id: str, version: str | None = None) -> None:
        """Release canonical review for an explicitly retired family version."""

        family = TEMPLATES.get(family_id)
        if family is None or (version is not None and version != family.version):
            raise AssessmentError("unknown_template_family_version")
        self.retired_families.add((family_id, family.version if version is None else version))

    def canonical_review(self, attempt: Attempt) -> dict[str, Any] | None:
        """Return delayed metadata or detailed solutions under the release policy."""

        if not attempt.submitted:
            return None
        release_at = max(attempt.canonical_available_at.values(), default=self.now)
        eligible = True
        for item in attempt.items:
            family_key = (item.family_id, item.family_version)
            item_release_at = attempt.canonical_available_at[item.item_id]
            if family_key not in self.retired_families and self.now < item_release_at:
                eligible = False
                release_at = max(release_at, item_release_at)
        if not eligible:
            return {"status": "delayed", "available_at": release_at}
        return {
            "status": "available",
            "available_at": release_at,
            "items": [
                {
                    "item_id": item.item_id,
                    "family_id": item.family_id,
                    "family_version": item.family_version,
                    "correct_option": attempt.answer_keys[item.item_id],
                    "explanation": TEMPLATES[item.family_id].canonical_explanation,
                }
                for item in attempt.items
            ],
        }

    def public_attempt(self, attempt: Attempt) -> dict[str, Any]:
        return public_attempt(attempt, canonical_review=self.canonical_review(attempt))

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
        # Progressive follow-ups add half an item of credit. Keep the
        # denominator aligned with that weight so rotated forms with more
        # progressive items remain comparable and a fully correct form can
        # still reach a verified grade.
        max_points = len(attempt.items) + len(progressive_ids) * 0.5
        attempt.score = round((base_points + followup_points * 0.5) / max_points * 100, 2)
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
        submitted_followups = {
            item.item_id: response.strip()
            for item in attempt.items
            if item.progressive and (response := (followups or {}).get(item.item_id, "")).strip()
        }
        similarity_evidence = self._find_similarity_evidence(attempt, submitted_followups)
        if similarity_evidence:
            signals.append("cross_submission_similarity_review")
        attempt.integrity_evidence = similarity_evidence
        attempt.submitted_followups = submitted_followups
        attempt.integrity_signals = signals
        attempt.submitted = True
        return attempt

    def grade_offers(self, attempt: Attempt) -> list[dict[str, str]]:
        """Return one-step grade choices without changing the declaration."""
        return _grade_offers(attempt)

    def _find_similarity_evidence(
        self, attempt: Attempt, submitted_followups: dict[str, str]
    ) -> list[dict[str, Any]]:
        evidence: list[dict[str, Any]] = []
        for item in attempt.items:
            response = submitted_followups.get(item.item_id)
            if not response:
                continue
            for previous in self.attempts.values():
                if previous.attempt_id == attempt.attempt_id or not previous.submitted:
                    continue
                for previous_item in previous.items:
                    if previous_item.family_id != item.family_id:
                        continue
                    previous_response = previous.submitted_followups.get(previous_item.item_id)
                    if not previous_response:
                        continue
                    match = _submission_similarity(response, previous_response)
                    if match is not None:
                        evidence.append(match.public(item.item_id))
                        break
                if evidence and evidence[-1]["item_id"] == item.item_id:
                    break
        return evidence


def _passes_hidden_check(response: str, check: HiddenCheck) -> bool:
    normalized = " ".join(response.casefold().split())
    return all(
        any(term.casefold() in normalized for term in concept_group)
        for concept_group in check.required_concepts
    )


def _looks_like_code(value: str) -> bool:
    return bool(
        re.search(
            r"[{};]|=>|\b(?:class|const|def|function|let|return|SELECT|FROM|WHERE)\b",
            value,
            re.IGNORECASE,
        )
    )


def _normalized_tokens(value: str) -> tuple[str, ...]:
    if _looks_like_code(value):
        without_comments = _CODE_COMMENT_PATTERN.sub(" ", value)
        tokens: list[str] = []
        for token in _CODE_TOKEN_PATTERN.findall(without_comments):
            folded = token.casefold()
            if folded.replace(".", "", 1).isdigit():
                tokens.append("<number>")
            elif re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", token) and folded not in _CODE_KEYWORDS:
                tokens.append("<identifier>")
            else:
                tokens.append(folded)
        return tuple(tokens)

    normalized = " ".join(value.casefold().split())
    return tuple(
        token
        for token in _TEXT_TOKEN_PATTERN.findall(normalized)
        if token not in _TEXT_BOILERPLATE
    )


def _submission_similarity(left: str, right: str) -> SimilarityMatch | None:
    left_tokens = _normalized_tokens(left)
    right_tokens = _normalized_tokens(right)
    if min(len(left_tokens), len(right_tokens)) < SIMILARITY_MIN_TOKENS:
        return None
    left_set = set(left_tokens)
    right_set = set(right_tokens)
    jaccard = len(left_set & right_set) / len(left_set | right_set)
    sequence = SequenceMatcher(a=left_tokens, b=right_tokens, autojunk=False).ratio()
    similarity = (jaccard * 0.4) + (sequence * 0.6)
    if similarity < SIMILARITY_REVIEW_THRESHOLD:
        return None
    modality = "code" if _looks_like_code(left) or _looks_like_code(right) else "text"
    return SimilarityMatch(modality, similarity)


def public_attempt(
    attempt: Attempt, *, canonical_review: dict[str, Any] | None = None
) -> dict[str, Any]:
    """Serialize an attempt without answer keys or scoring internals."""
    return {
        "attempt_id": attempt.attempt_id,
        "industry": attempt.industry,
        "specialization": attempt.specialization,
        "declared_grade": attempt.declared_grade,
        "status": "submitted" if attempt.submitted else "in_progress",
        "items": [
            {"item_id": item.item_id, "family_id": item.family_id, "family_version": item.family_version, "domain": item.domain, "difficulty": item.difficulty, "prompt": item.prompt, "options": item.options, "progressive": item.progressive, "artifact": item.artifact}
            for item in attempt.items
        ],
        **(
            {
                "score": attempt.score,
                "grade_state": attempt.grade_state,
                "integrity_signals": attempt.integrity_signals,
                "integrity_evidence": attempt.integrity_evidence,
                "canonical_review": canonical_review
                if canonical_review is not None
                else {
                    "status": "delayed",
                    "available_at": max(
                        attempt.canonical_available_at.values(),
                        default=attempt.created_at,
                    ),
                },
                "grade_offers": _grade_offers(attempt),
            }
            if attempt.submitted
            else {}
        ),
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
