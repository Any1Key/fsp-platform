"""Offline deterministic keyword/Jaccard baseline for matching validation.

This comparator is deliberately separate from production Talent Radar. The
PII-free validation fixture has canonical skill slugs rather than resume
text, so those slugs are the baseline's keyword proxy. Synthetic relevance
labels and ProofMatch evidence dimensions are never used for scoring.
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from collections.abc import Iterable
from dataclasses import asdict, dataclass
from pathlib import Path

from .matching_validation import (
    LabeledMatchingCase,
    MatchingRelevanceArtifact,
    build_matching_relevance,
)
from .validation_dataset import DEFAULT_SEED

KEYWORD_BASELINE_VERSION = "2026-10-09"


@dataclass(frozen=True)
class KeywordBaselineCandidate:
    """One candidate's baseline score for a single need."""

    candidate_id: str
    score: float
    matched_keywords: tuple[str, ...]
    candidate_keyword_count: int
    need_keyword_count: int


@dataclass(frozen=True)
class KeywordBaselineNeedRanking:
    """Complete candidate ranking for one employer need."""

    need_id: str
    results: tuple[KeywordBaselineCandidate, ...]


@dataclass(frozen=True)
class KeywordBaselineArtifact:
    """Stable, label-free output of the offline keyword comparator."""

    keyword_baseline_version: str
    matching_validation_version: str
    dataset_version: str
    seed: str
    candidate_count: int
    need_count: int
    rankings: tuple[KeywordBaselineNeedRanking, ...]

    def to_dict(self) -> dict[str, object]:
        payload = asdict(self)
        payload["ranking_count"] = len(self.rankings)
        return payload

    def to_json(self, *, indent: int | None = 2) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=indent, sort_keys=True) + "\n"


def build_keyword_baseline(*, seed: str = DEFAULT_SEED) -> KeywordBaselineArtifact:
    """Build a complete baseline ranking from the fixed validation fixture."""

    matching = build_matching_relevance(seed=seed)
    return rank_keyword_baseline(matching)


def rank_keyword_baseline(
    artifact: MatchingRelevanceArtifact,
) -> KeywordBaselineArtifact:
    """Rank every candidate for every need using skill-keyword Jaccard overlap.

    Only candidate skills and the need's required/preferred skills are read
    from each case. In particular, ``expected_relevance`` and all assessment,
    FSP and freshness fields are intentionally ignored.
    """

    cases_by_need: dict[str, list[LabeledMatchingCase]] = defaultdict(list)
    for case in artifact.cases:
        cases_by_need[case.need_id].append(case)

    rankings: list[KeywordBaselineNeedRanking] = []
    for need_id, cases in cases_by_need.items():
        if not cases:
            continue
        candidate_ids = [case.candidate_id for case in cases]
        if len(candidate_ids) != len(set(candidate_ids)):
            raise ValueError(f"duplicate candidate in keyword baseline need {need_id}")

        need_keywords = _keywords((*cases[0].required_skills, *cases[0].preferred_skills))
        results = tuple(
            sorted(
                (
                    _score_candidate(case, need_keywords)
                    for case in cases
                ),
                key=lambda result: (-result.score, result.candidate_id),
            )
        )
        rankings.append(KeywordBaselineNeedRanking(need_id=need_id, results=results))

    rankings.sort(key=lambda ranking: ranking.need_id)
    return KeywordBaselineArtifact(
        keyword_baseline_version=KEYWORD_BASELINE_VERSION,
        matching_validation_version=artifact.matching_validation_version,
        dataset_version=artifact.dataset_version,
        seed=artifact.seed,
        candidate_count=artifact.candidate_count,
        need_count=artifact.need_count,
        rankings=tuple(rankings),
    )


def _score_candidate(
    case: LabeledMatchingCase,
    need_keywords: frozenset[str],
) -> KeywordBaselineCandidate:
    candidate_keywords = _keywords(case.candidate_skills)
    matched_keywords = tuple(sorted(candidate_keywords & need_keywords))
    union_size = len(candidate_keywords | need_keywords)
    score = len(matched_keywords) / union_size if union_size else 0.0
    return KeywordBaselineCandidate(
        candidate_id=case.candidate_id,
        score=round(score, 6),
        matched_keywords=matched_keywords,
        candidate_keyword_count=len(candidate_keywords),
        need_keyword_count=len(need_keywords),
    )


def _keywords(values: Iterable[str]) -> frozenset[str]:
    return frozenset(value.strip().casefold() for value in values if value.strip())


def write_keyword_baseline(path: str | Path, *, seed: str = DEFAULT_SEED) -> None:
    """Write a complete label-free baseline artifact to ``path``."""

    Path(path).write_text(build_keyword_baseline(seed=seed).to_json(), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Write offline keyword baseline rankings")
    parser.add_argument("--output", type=Path, help="JSON output path; stdout when omitted")
    parser.add_argument("--seed", default=DEFAULT_SEED)
    args = parser.parse_args()
    artifact = build_keyword_baseline(seed=args.seed)
    if args.output:
        args.output.write_text(artifact.to_json(), encoding="utf-8")
    else:
        print(artifact.to_json(indent=None), end="")


if __name__ == "__main__":
    main()
