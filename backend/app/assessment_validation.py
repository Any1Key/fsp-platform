"""Deterministic synthetic validation for the calibrated assessment.

The harness runs labeled, synthetic ability profiles through the production
assessment domain. It is intentionally standard-library-only and offline so
that validation remains reproducible on the CPU-only target environment.

The score-to-grade bands in this module are a calibration view for measuring
discrimination. They do not change the product's declared-grade or
``verified``/``not_confirmed`` semantics.
"""

from __future__ import annotations

import json
import random
from argparse import ArgumentParser
from collections import Counter, defaultdict
from collections.abc import Iterable, Sequence
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from math import sqrt
from pathlib import Path
from typing import Any

from .assessments import GRADES, AssessmentService

VALIDATION_VERSION = "2026-10-07"
DEFAULT_SEED = "fsp-assessment-calibration-2026-10-07"
SPECIALIZATION = "Backend Engineering"
DEFAULT_CANDIDATES_PER_GRADE = 24
JUNIOR_SCORE_CEILING = 40.0
MIDDLE_SCORE_CEILING = 65.0
GRADE_COLLAPSE_SHARE = 0.80

_ABILITY_CENTERS = {"Junior": 0.35, "Middle": 0.72, "Senior": 0.97}
_FOLLOWUP_EXPLANATION = (
    "bounded retry backoff limit transaction rollback deterministic seed "
    "reproducibility budget p95 latency"
)
_CRITICAL_DOMAINS = ("api_fundamentals", "security_operations")


@dataclass(frozen=True)
class SyntheticCandidate:
    candidate_id: str
    target_grade: str
    ability: float


@dataclass(frozen=True)
class ItemObservation:
    candidate_id: str
    target_grade: str
    family_id: str
    domain: str
    difficulty: int
    correct: bool
    score: float


@dataclass(frozen=True)
class ValidationObservation:
    candidate_id: str
    target_grade: str
    predicted_grade: str
    score: float
    form_signature: tuple[tuple[str, str], ...]
    items: tuple[ItemObservation, ...]


@dataclass(frozen=True)
class AssessmentValidationReport:
    validation_version: str
    seed: str
    specialization: str
    candidates_per_grade: int
    sample_size: int
    confusion_matrix: dict[str, dict[str, int]]
    macro_f1: float
    grade_agreement: float
    predicted_distribution: dict[str, int]
    grade_collapse: bool
    grade_collapse_threshold: float
    grade_collapse_dominant_grade: str | None
    grade_collapse_share: float
    equivalent_form_score_difference: float
    retest_agreement: float
    item_metrics: dict[str, dict[str, float | int]]
    mean_item_discrimination: float
    positive_item_discrimination_rate: float
    critical_domain_reliability: dict[str, float]
    form_uniqueness_rate: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def generate_synthetic_candidates(
    *,
    seed: str = DEFAULT_SEED,
    candidates_per_grade: int = DEFAULT_CANDIDATES_PER_GRADE,
) -> tuple[SyntheticCandidate, ...]:
    """Create labeled ability profiles without curving or quota adjustment."""

    if candidates_per_grade < 2:
        raise ValueError("at least two candidates per grade are required")
    rng = random.Random(seed)
    candidates: list[SyntheticCandidate] = []
    for grade in GRADES:
        center = _ABILITY_CENTERS[grade]
        for index in range(candidates_per_grade):
            ability = max(0.05, min(0.99, center + rng.gauss(0.0, 0.025)))
            candidates.append(
                SyntheticCandidate(
                    candidate_id=f"synthetic-{grade.casefold()}-{index:03d}",
                    target_grade=grade,
                    ability=round(ability, 6),
                )
            )
    return tuple(candidates)


def grade_from_validation_score(score: float) -> str:
    """Map a score to a calibration band used only by this validation harness."""

    if score < JUNIOR_SCORE_CEILING:
        return "Junior"
    if score < MIDDLE_SCORE_CEILING:
        return "Middle"
    return "Senior"


def grade_collapse_detected(
    predicted_grades: Iterable[str], *, threshold: float = GRADE_COLLAPSE_SHARE
) -> bool:
    """Return true when one predicted grade absorbs an almost-all share."""

    return bool(grade_collapse_details(predicted_grades, threshold=threshold)["collapsed"])


def grade_collapse_details(
    predicted_grades: Iterable[str], *, threshold: float = GRADE_COLLAPSE_SHARE
) -> dict[str, bool | str | float | int | None]:
    """Return an auditable collapse result for a predicted-grade sample.

    An empty sample is treated as collapsed because it cannot demonstrate
    grade coverage. Its dominant share is reported as zero so consumers can
    distinguish missing evidence from an observed one-grade concentration.
    """

    if not 0 < threshold <= 1:
        raise ValueError("grade-collapse threshold must be in (0, 1]")
    predictions = list(predicted_grades)
    if not predictions:
        return {
            "collapsed": True,
            "dominant_grade": None,
            "dominant_share": 0.0,
            "sample_size": 0,
            "threshold": threshold,
        }
    counts = Counter(predictions)
    dominant_count = max(counts.values())
    dominant_grade = next(grade for grade in predictions if counts[grade] == dominant_count)
    dominant_share = dominant_count / len(predictions)
    return {
        "collapsed": dominant_share >= threshold,
        "dominant_grade": dominant_grade,
        "dominant_share": round(dominant_share, 4),
        "sample_size": len(predictions),
        "threshold": threshold,
    }


def run_validation(
    *,
    seed: str = DEFAULT_SEED,
    candidates_per_grade: int = DEFAULT_CANDIDATES_PER_GRADE,
) -> AssessmentValidationReport:
    """Run the synthetic validation suite through the actual assessment service."""

    candidates = generate_synthetic_candidates(
        seed=seed, candidates_per_grade=candidates_per_grade
    )
    rng = random.Random(f"{seed}:responses")
    primary: list[ValidationObservation] = []
    retests: list[tuple[ValidationObservation, ValidationObservation]] = []
    all_signatures: list[tuple[tuple[str, str], ...]] = []

    for candidate in candidates:
        first = _run_candidate(candidate, rng)
        retest = _run_candidate(candidate, rng, candidate_suffix=":retest")
        primary.append(first)
        retests.append((first, retest))
        all_signatures.extend((first.form_signature, retest.form_signature))

    confusion = _confusion_matrix(primary)
    predictions = [observation.predicted_grade for observation in primary]
    collapse = grade_collapse_details(predictions)
    item_observations = [item for observation in primary for item in observation.items]
    item_metrics = _item_metrics(item_observations)
    return AssessmentValidationReport(
        validation_version=VALIDATION_VERSION,
        seed=seed,
        specialization=SPECIALIZATION,
        candidates_per_grade=candidates_per_grade,
        sample_size=len(primary),
        confusion_matrix=confusion,
        macro_f1=round(_macro_f1(confusion), 4),
        grade_agreement=round(
            sum(confusion[grade][grade] for grade in GRADES) / len(primary), 4
        ),
        predicted_distribution={grade: predictions.count(grade) for grade in GRADES},
        grade_collapse=bool(collapse["collapsed"]),
        grade_collapse_threshold=GRADE_COLLAPSE_SHARE,
        grade_collapse_dominant_grade=collapse["dominant_grade"],
        grade_collapse_share=float(collapse["dominant_share"]),
        equivalent_form_score_difference=round(
            sum(abs(first.score - second.score) for first, second in retests)
            / len(retests),
            4,
        ),
        retest_agreement=round(
            sum(first.predicted_grade == second.predicted_grade for first, second in retests)
            / len(retests),
            4,
        ),
        item_metrics=item_metrics,
        mean_item_discrimination=round(
            sum(metric["discrimination"] for metric in item_metrics.values())
            / len(item_metrics),
            4,
        ),
        positive_item_discrimination_rate=round(
            sum(metric["discrimination"] > 0 for metric in item_metrics.values())
            / len(item_metrics),
            4,
        ),
        critical_domain_reliability=_critical_domain_reliability(item_observations),
        form_uniqueness_rate=round(
            len(set(all_signatures)) / len(all_signatures), 4
        ),
    )


def _run_candidate(
    candidate: SyntheticCandidate,
    rng: random.Random,
    *,
    candidate_suffix: str = "",
) -> ValidationObservation:
    service = AssessmentService(
        now=datetime(2026, 10, 7, tzinfo=UTC),
        seed_factory=lambda: f"{rng.getrandbits(128):032x}",
    )
    attempt = service.create_attempt(
        f"{candidate.candidate_id}{candidate_suffix}", SPECIALIZATION, candidate.target_grade
    )
    answers: dict[str, int] = {}
    followups: dict[str, str] = {}
    for item in attempt.items:
        probability = max(
            0.05,
            min(0.99, candidate.ability - ((item.difficulty - 2) * 0.06)),
        )
        if rng.random() < probability:
            answers[item.item_id] = attempt.answer_keys[item.item_id]
            if item.progressive and rng.random() < probability:
                followups[item.item_id] = _FOLLOWUP_EXPLANATION
        else:
            answers[item.item_id] = (attempt.answer_keys[item.item_id] + 1) % len(item.options)
    result = service.submit(attempt.attempt_id, answers, followups)
    assert result.score is not None
    items = tuple(
        ItemObservation(
            candidate_id=candidate.candidate_id,
            target_grade=candidate.target_grade,
            family_id=item.family_id,
            domain=item.domain,
            difficulty=item.difficulty,
            correct=answers[item.item_id] == attempt.answer_keys[item.item_id],
            score=result.score,
        )
        for item in attempt.items
    )
    signature = tuple((item.family_id, item.artifact) for item in attempt.items)
    return ValidationObservation(
        candidate_id=candidate.candidate_id,
        target_grade=candidate.target_grade,
        predicted_grade=grade_from_validation_score(result.score),
        score=result.score,
        form_signature=signature,
        items=items,
    )


def _confusion_matrix(
    observations: Iterable[ValidationObservation],
) -> dict[str, dict[str, int]]:
    matrix = {actual: {predicted: 0 for predicted in GRADES} for actual in GRADES}
    for observation in observations:
        matrix[observation.target_grade][observation.predicted_grade] += 1
    return matrix


def _macro_f1(matrix: dict[str, dict[str, int]]) -> float:
    f1_scores: list[float] = []
    for grade in GRADES:
        true_positive = matrix[grade][grade]
        false_positive = sum(matrix[actual][grade] for actual in GRADES if actual != grade)
        false_negative = sum(matrix[grade][predicted] for predicted in GRADES if predicted != grade)
        precision = true_positive / (true_positive + false_positive) if true_positive + false_positive else 0
        recall = true_positive / (true_positive + false_negative) if true_positive + false_negative else 0
        f1_scores.append(2 * precision * recall / (precision + recall) if precision + recall else 0)
    return sum(f1_scores) / len(f1_scores)


def _item_metrics(items: Iterable[ItemObservation]) -> dict[str, dict[str, float | int]]:
    grouped: dict[str, list[ItemObservation]] = defaultdict(list)
    for item in items:
        grouped[item.family_id].append(item)
    metrics: dict[str, dict[str, float | int]] = {}
    for family_id, family_items in sorted(grouped.items()):
        pass_rate = sum(item.correct for item in family_items) / len(family_items)
        metrics[family_id] = {
            "observations": len(family_items),
            "pass_rate": round(pass_rate, 4),
            "difficulty": round(1 - pass_rate, 4),
            "discrimination": round(_point_biserial(family_items), 4),
        }
    return metrics


def _point_biserial(items: list[ItemObservation]) -> float:
    if not items:
        return 0.0
    correct_scores = [item.score for item in items if item.correct]
    incorrect_scores = [item.score for item in items if not item.correct]
    if not correct_scores or not incorrect_scores:
        return 0.0
    all_scores = [item.score for item in items]
    mean_score = sum(all_scores) / len(all_scores)
    variance = sum((score - mean_score) ** 2 for score in all_scores) / (len(all_scores) - 1)
    standard_deviation = sqrt(variance) if variance else 0.0
    if not standard_deviation:
        return 0.0
    p = len(correct_scores) / len(items)
    q = 1 - p
    return ((sum(correct_scores) / len(correct_scores)) - (sum(incorrect_scores) / len(incorrect_scores))) / standard_deviation * sqrt(p * q)


def _critical_domain_reliability(items: Iterable[ItemObservation]) -> dict[str, float]:
    grouped: dict[str, list[bool]] = defaultdict(list)
    for item in items:
        if item.domain in _CRITICAL_DOMAINS:
            grouped[item.domain].append(item.correct)
    return {
        domain: round(sum(correct for correct in grouped.get(domain, [])) / len(grouped[domain]), 4)
        if grouped.get(domain)
        else 0.0
        for domain in _CRITICAL_DOMAINS
    }


def write_report(report: AssessmentValidationReport, path: str | Path) -> None:
    """Write one deterministic report artifact without synthetic identifiers."""

    Path(path).write_text(
        json.dumps(report.to_dict(), ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def main(argv: Sequence[str] | None = None) -> None:
    parser = ArgumentParser(description="Run synthetic calibrated-assessment validation")
    parser.add_argument("--seed", default=DEFAULT_SEED)
    parser.add_argument("--candidates-per-grade", type=int, default=DEFAULT_CANDIDATES_PER_GRADE)
    parser.add_argument(
        "--output",
        type=Path,
        help="optional path for the JSON report artifact; stdout is always retained",
    )
    args = parser.parse_args(argv)
    report = run_validation(
        seed=args.seed,
        candidates_per_grade=args.candidates_per_grade,
    )
    if args.output:
        write_report(report, args.output)
    print(json.dumps(report.to_dict(), ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
