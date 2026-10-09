"""Offline, deterministic labeled relevance cases for matching validation.

The production Talent Radar is database-backed and must never consume
synthetic ground-truth labels. This module materializes the versioned
validation fixture into a self-contained case set for later baseline and
ranking-metric work.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from .validation_dataset import (
    DEFAULT_SEED,
    FRESHNESS_STATES,
    GRADE_STATES,
    GRADES,
    RELEVANCE_LABELS,
    SPECIALIZATION_SKILLS,
    ValidationDataset,
    generate_validation_dataset,
)

MATCHING_VALIDATION_VERSION = "2026-10-09"


@dataclass(frozen=True)
class LabeledMatchingCase:
    """One candidate/need pair and its synthetic relevance ground truth."""

    candidate_id: str
    need_id: str
    expected_relevance: str
    candidate_specialization: str
    candidate_grade: str
    candidate_grade_state: str
    candidate_skills: tuple[str, ...]
    candidate_evidence_freshness: str
    candidate_has_fsp_history: bool
    need_specialization: str
    need_grade: str
    required_skills: tuple[str, ...]
    preferred_skills: tuple[str, ...]


@dataclass(frozen=True)
class MatchingRelevanceArtifact:
    """Stable offline input for matching validation consumers."""

    matching_validation_version: str
    dataset_version: str
    seed: str
    candidate_count: int
    need_count: int
    cases: tuple[LabeledMatchingCase, ...]
    coverage: dict[str, Any]

    @property
    def case_count(self) -> int:
        return len(self.cases)

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["case_count"] = self.case_count
        return payload

    def to_json(self, *, indent: int | None = 2) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=indent, sort_keys=True) + "\n"


def build_matching_relevance(
    *, seed: str = DEFAULT_SEED,
) -> MatchingRelevanceArtifact:
    """Materialize the complete candidate/need label matrix.

    The function deliberately accepts only the offline dataset seed. It does
    not import the database session, production discovery service, or network
    adapters, which prevents synthetic labels from becoming ranking inputs.
    """

    dataset = generate_validation_dataset(seed=seed)
    candidates = {candidate.candidate_id: candidate for candidate in dataset.candidates}
    needs = {need.need_id: need for need in dataset.needs}
    labels = {(label.candidate_id, label.need_id): label.label for label in dataset.expected_relevance}
    expected_pairs = {
        (candidate.candidate_id, need.need_id)
        for candidate in dataset.candidates
        for need in dataset.needs
    }
    if len(labels) != len(dataset.expected_relevance):
        raise ValueError("matching relevance labels contain duplicate candidate/need pairs")
    if set(labels) != expected_pairs:
        raise ValueError("matching relevance labels do not cover every candidate/need pair")
    if not set(labels.values()).issubset(RELEVANCE_LABELS):
        raise ValueError("matching relevance label is outside the approved vocabulary")

    cases = tuple(
        _case(candidates[candidate_id], needs[need_id], labels[(candidate_id, need_id)])
        for need_id in (need.need_id for need in dataset.needs)
        for candidate_id in (candidate.candidate_id for candidate in dataset.candidates)
    )
    return MatchingRelevanceArtifact(
        matching_validation_version=MATCHING_VALIDATION_VERSION,
        dataset_version=dataset.dataset_version,
        seed=dataset.seed,
        candidate_count=dataset.candidate_count,
        need_count=dataset.need_count,
        cases=cases,
        coverage=_coverage(dataset, cases),
    )


def _case(candidate: Any, need: Any, expected_relevance: str) -> LabeledMatchingCase:
    return LabeledMatchingCase(
        candidate_id=candidate.candidate_id,
        need_id=need.need_id,
        expected_relevance=expected_relevance,
        candidate_specialization=candidate.specialization,
        candidate_grade=candidate.target_grade,
        candidate_grade_state=candidate.grade_state,
        candidate_skills=candidate.skills,
        candidate_evidence_freshness=candidate.evidence_freshness,
        candidate_has_fsp_history=candidate.has_fsp_history,
        need_specialization=need.specialization,
        need_grade=need.grade,
        required_skills=need.required_skills,
        preferred_skills=need.preferred_skills,
    )


def _coverage(dataset: ValidationDataset, cases: tuple[LabeledMatchingCase, ...]) -> dict[str, Any]:
    """Describe fixture coverage without calculating ranking quality metrics."""

    return {
        "expected_pair_count": dataset.candidate_count * dataset.need_count,
        "actual_pair_count": len(cases),
        "label_counts": _ordered_counts(
            (case.expected_relevance for case in cases), RELEVANCE_LABELS
        ),
        "candidate_grade_states": _ordered_counts(
            (candidate.grade_state for candidate in dataset.candidates), GRADE_STATES
        ),
        "candidate_fsp_history": {
            "with_history": sum(candidate.has_fsp_history for candidate in dataset.candidates),
            "without_history": sum(not candidate.has_fsp_history for candidate in dataset.candidates),
        },
        "candidate_evidence_freshness": _ordered_counts(
            (candidate.evidence_freshness for candidate in dataset.candidates), FRESHNESS_STATES
        ),
        "candidate_grades": _ordered_counts(
            (candidate.target_grade for candidate in dataset.candidates), GRADES
        ),
        "candidate_specializations": _ordered_counts(
            (candidate.specialization for candidate in dataset.candidates), SPECIALIZATION_SKILLS
        ),
        "need_specializations": _ordered_counts(
            (need.specialization for need in dataset.needs), SPECIALIZATION_SKILLS
        ),
    }


def _ordered_counts(values: Any, expected: Any) -> dict[str, int]:
    counts = Counter(values)
    return {key: counts.get(key, 0) for key in expected}


def write_matching_relevance(path: str | Path, *, seed: str = DEFAULT_SEED) -> None:
    """Write one deterministic JSON artifact for an offline validation run."""

    Path(path).write_text(build_matching_relevance(seed=seed).to_json(), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Write labeled matching relevance cases")
    parser.add_argument("--output", type=Path, help="JSON output path; stdout when omitted")
    parser.add_argument("--seed", default=DEFAULT_SEED)
    args = parser.parse_args()
    artifact = build_matching_relevance(seed=args.seed)
    if args.output:
        args.output.write_text(artifact.to_json(), encoding="utf-8")
    else:
        print(artifact.to_json(indent=None), end="")


if __name__ == "__main__":
    main()
