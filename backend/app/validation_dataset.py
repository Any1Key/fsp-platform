"""Deterministic, PII-free fixtures shared by validation work units.

The generator is deliberately independent from the database and HTTP layers.
It gives later matching and assessment validation units one stable fixture
contract without turning synthetic labels into production ranking rules.
"""

from __future__ import annotations

import argparse
import json
import random
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

DATASET_VERSION = "2026-10-09"
DEFAULT_SEED = "fsp-validation-dataset-2026-10-09"
EXPECTED_CANDIDATE_COUNT = 80
EXPECTED_NEED_COUNT = 20

GRADES = ("Junior", "Middle", "Senior")
GRADE_CENTERS = {"Junior": 0.35, "Middle": 0.72, "Senior": 0.97}
GRADE_STATES = ("verified", "unconfirmed")
FRESHNESS_STATES = ("fresh", "expiring", "stale")
RELEVANCE_LABELS = ("relevant", "adjacent", "not_relevant")

SPECIALIZATION_SKILLS: dict[str, tuple[str, ...]] = {
    "backend-engineering": ("python", "sql", "rest-apis", "git"),
    "frontend-engineering": ("typescript", "automated-testing", "git"),
    "full-stack-engineering": ("python", "typescript", "sql", "rest-apis", "git"),
    "qa-test-automation": ("automated-testing", "python", "sql", "git"),
    "devops-sre": ("docker", "kubernetes", "python", "git"),
    "data-engineering": ("python", "sql", "data-modeling", "docker"),
    "data-science-ml": ("python", "sql", "machine-learning", "data-modeling"),
    "mobile-engineering": ("swift", "automated-testing", "git"),
}


@dataclass(frozen=True)
class AssessmentResponseProfile:
    """Synthetic response inputs, not answer keys or candidate data."""

    target_grade: str
    ability: float
    response_seed: str


@dataclass(frozen=True)
class ValidationCandidate:
    candidate_id: str
    specialization: str
    target_grade: str
    grade_state: str
    skills: tuple[str, ...]
    evidence_freshness: str
    has_fsp_history: bool
    assessment: AssessmentResponseProfile


@dataclass(frozen=True)
class ValidationNeed:
    need_id: str
    specialization: str
    grade: str
    required_skills: tuple[str, ...]
    preferred_skills: tuple[str, ...]


@dataclass(frozen=True)
class ExpectedRelevance:
    candidate_id: str
    need_id: str
    label: str


@dataclass(frozen=True)
class ValidationDataset:
    dataset_version: str
    seed: str
    candidates: tuple[ValidationCandidate, ...]
    needs: tuple[ValidationNeed, ...]
    expected_relevance: tuple[ExpectedRelevance, ...]

    @property
    def candidate_count(self) -> int:
        return len(self.candidates)

    @property
    def need_count(self) -> int:
        return len(self.needs)

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-safe, self-describing fixture document."""

        payload = asdict(self)
        payload["candidate_count"] = self.candidate_count
        payload["need_count"] = self.need_count
        payload["relevance_label_count"] = len(self.expected_relevance)
        return payload

    def to_json(self, *, indent: int | None = 2) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=indent, sort_keys=True) + "\n"


def generate_validation_dataset(*, seed: str = DEFAULT_SEED) -> ValidationDataset:
    """Generate the fixed-size validation fixture from ``seed``.

    The seed changes values, but not the dataset shape or its taxonomy
    vocabulary. No quota is applied to any measured outcome; labels are
    generated from explicit synthetic ground-truth rules below.
    """

    rng = random.Random(seed)
    specializations = tuple(SPECIALIZATION_SKILLS)
    candidates = tuple(
        _candidate(index, specialization, rng, seed)
        for index in range(EXPECTED_CANDIDATE_COUNT)
        for specialization in (specializations[index % len(specializations)],)
    )
    needs = tuple(
        _need(index, specializations[index % len(specializations)])
        for index in range(EXPECTED_NEED_COUNT)
    )
    expected_relevance = tuple(
        ExpectedRelevance(
            candidate_id=candidate.candidate_id,
            need_id=need.need_id,
            label=_relevance_label(candidate, need),
        )
        for need in needs
        for candidate in candidates
    )
    return ValidationDataset(
        dataset_version=DATASET_VERSION,
        seed=seed,
        candidates=candidates,
        needs=needs,
        expected_relevance=expected_relevance,
    )


def _candidate(
    index: int,
    specialization: str,
    rng: random.Random,
    seed: str,
) -> ValidationCandidate:
    target_grade = GRADES[index % len(GRADES)]
    available_skills = SPECIALIZATION_SKILLS[specialization]
    skills = tuple(
        skill
        for position, skill in enumerate(available_skills)
        if position == 0 or (index + position) % 3 != 0
    )
    ability = max(0.05, min(0.99, GRADE_CENTERS[target_grade] + rng.gauss(0.0, 0.025)))
    candidate_id = f"synthetic-candidate-{index:03d}"
    return ValidationCandidate(
        candidate_id=candidate_id,
        specialization=specialization,
        target_grade=target_grade,
        grade_state="unconfirmed" if index % 5 == 0 else "verified",
        skills=skills,
        evidence_freshness=FRESHNESS_STATES[index % len(FRESHNESS_STATES)],
        has_fsp_history=index % 3 != 0,
        assessment=AssessmentResponseProfile(
            target_grade=target_grade,
            ability=round(ability, 6),
            response_seed=f"{seed}:assessment:{candidate_id}",
        ),
    )


def _need(index: int, specialization: str) -> ValidationNeed:
    skills = SPECIALIZATION_SKILLS[specialization]
    return ValidationNeed(
        need_id=f"synthetic-need-{index:03d}",
        specialization=specialization,
        grade=GRADES[(index + 1) % len(GRADES)],
        required_skills=skills[:2],
        preferred_skills=skills[2:4],
    )


def _relevance_label(candidate: ValidationCandidate, need: ValidationNeed) -> str:
    shared_required = len(set(candidate.skills) & set(need.required_skills))
    required_coverage = shared_required / len(need.required_skills)
    same_specialization = candidate.specialization == need.specialization
    grade_distance = abs(GRADES.index(candidate.target_grade) - GRADES.index(need.grade))

    if same_specialization and grade_distance == 0 and required_coverage == 1:
        return "relevant"
    if same_specialization and grade_distance <= 1 and required_coverage >= 0.5:
        return "adjacent"
    if not same_specialization and required_coverage == 1 and grade_distance == 0:
        return "adjacent"
    return "not_relevant"


def write_dataset(path: str | Path, *, seed: str = DEFAULT_SEED) -> None:
    """Write one deterministic fixture artifact for offline validation runs."""

    Path(path).write_text(generate_validation_dataset(seed=seed).to_json(), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Write the synthetic FSP validation dataset")
    parser.add_argument("--output", type=Path, help="JSON output path; stdout when omitted")
    parser.add_argument("--seed", default=DEFAULT_SEED)
    args = parser.parse_args()
    dataset = generate_validation_dataset(seed=args.seed)
    if args.output:
        args.output.write_text(dataset.to_json(), encoding="utf-8")
    else:
        print(dataset.to_json(indent=None), end="")


if __name__ == "__main__":
    main()
