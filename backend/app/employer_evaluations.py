"""Employer-owned grading and evidence for matched task assignments."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from fastapi import HTTPException, status
from sqlalchemy import text
from sqlalchemy.orm import Session

from .auth import Principal
from .companies import _ensure_company


def _now() -> datetime:
    return datetime.now(UTC)


def _json_value(value: Any) -> Any:
    return json.loads(value) if isinstance(value, str) else value


def _evaluation_response(row: dict[str, Any]) -> dict[str, Any]:
    result = {
        "id": row["id"],
        "assignment_id": row["assignment_id"],
        "score": int(row["score"]),
        "rubric_scores": _json_value(row["rubric_scores"]),
        "feedback": row["feedback"],
        "status": row["status"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
        "released_at": row["released_at"],
    }
    return result


def _candidate_evaluation_response(row: dict[str, Any] | None) -> dict[str, Any] | None:
    if row is None or row["status"] != "released":
        return None
    return {
        "score": int(row["score"]),
        "feedback": row["feedback"],
        "released_at": row["released_at"],
    }


def _assignment_row(db: Session, identity_id: str, assignment_id: str) -> dict[str, Any]:
    row = db.execute(
        text(
            "SELECT ta.id, ta.match_id, ta.candidate_profile_id, ta.task_id, "
            "ta.task_version_id, ta.pipeline_stage_id, ta.status, ta.assigned_at, "
            "ta.due_at, ta.submitted_at, ps.title AS stage_title, "
            "cp.display_name AS candidate_display_name, etv.version_number, etv.title, "
            "etv.instructions, etv.target_skills, etv.expected_grade, "
            "etv.estimated_minutes, etv.rubric, ee.id AS evaluation_id, "
            "ee.assignment_id AS evaluation_assignment_id, ee.score AS evaluation_score, "
            "ee.rubric_scores AS evaluation_rubric_scores, ee.feedback AS evaluation_feedback, "
            "ee.status AS evaluation_status, ee.created_at AS evaluation_created_at, "
            "ee.updated_at AS evaluation_updated_at, ee.released_at AS evaluation_released_at "
            "FROM task_assignment ta "
            "JOIN talent_match tm ON tm.id = ta.match_id "
            "JOIN employer_task et ON et.id = ta.task_id "
            "JOIN hiring_need hn ON hn.id = et.hiring_need_id "
            "JOIN company c ON c.id = hn.company_id "
            "JOIN pipeline_stage ps ON ps.id = ta.pipeline_stage_id "
            "JOIN employer_task_version etv ON etv.id = ta.task_version_id "
            "JOIN candidate_profile cp ON cp.id = ta.candidate_profile_id "
            "LEFT JOIN employer_evaluation ee ON ee.assignment_id = ta.id "
            "WHERE ta.id = :assignment_id AND tm.employer_identity_id = :identity_id "
            "AND c.owner_identity_id = :identity_id"
        ),
        {"assignment_id": assignment_id, "identity_id": identity_id},
    ).mappings().one_or_none()
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="employer_task_assignment_not_found",
        )
    return dict(row)


def _submissions(db: Session, assignment_id: str) -> list[dict[str, Any]]:
    return [
        dict(row)
        for row in db.execute(
            text(
                "SELECT id, attempt_number, response_text, submitted_at "
                "FROM task_submission WHERE assignment_id = :assignment_id "
                "ORDER BY attempt_number"
            ),
            {"assignment_id": assignment_id},
        ).mappings()
    ]


def _employer_assignment_response(db: Session, row: dict[str, Any]) -> dict[str, Any]:
    evaluation = None
    if row["evaluation_id"] is not None:
        evaluation = _evaluation_response(
            {
                "id": row["evaluation_id"],
                "assignment_id": row["evaluation_assignment_id"],
                "score": row["evaluation_score"],
                "rubric_scores": row["evaluation_rubric_scores"],
                "feedback": row["evaluation_feedback"],
                "status": row["evaluation_status"],
                "created_at": row["evaluation_created_at"],
                "updated_at": row["evaluation_updated_at"],
                "released_at": row["evaluation_released_at"],
            }
        )
    return {
        "id": row["id"],
        "match_id": row["match_id"],
        "candidate_profile_id": row["candidate_profile_id"],
        "candidate_display_name": row["candidate_display_name"] or "Candidate",
        "task_id": row["task_id"],
        "task_version_id": row["task_version_id"],
        "pipeline_stage_id": row["pipeline_stage_id"],
        "stage_title": row["stage_title"],
        "status": row["status"],
        "assigned_at": row["assigned_at"],
        "due_at": row["due_at"],
        "submitted_at": row["submitted_at"],
        "task": {
            "version_number": row["version_number"],
            "title": row["title"],
            "instructions": row["instructions"],
            "target_skills": _json_value(row["target_skills"]),
            "expected_grade": row["expected_grade"],
            "estimated_minutes": row["estimated_minutes"],
            "rubric": _json_value(row["rubric"]),
        },
        "submissions": _submissions(db, row["id"]),
        "evaluation": evaluation,
    }


def list_employer_assignments(db: Session, principal: Principal) -> list[dict[str, Any]]:
    identity_id, _ = _ensure_company(db, principal)
    rows = db.execute(
        text(
            "SELECT ta.id "
            "FROM task_assignment ta "
            "JOIN talent_match tm ON tm.id = ta.match_id "
            "JOIN employer_task et ON et.id = ta.task_id "
            "JOIN hiring_need hn ON hn.id = et.hiring_need_id "
            "JOIN company c ON c.id = hn.company_id "
            "WHERE tm.employer_identity_id = :identity_id "
            "AND c.owner_identity_id = :identity_id "
            "ORDER BY ta.assigned_at DESC, ta.id"
        ),
        {"identity_id": identity_id},
    ).scalars()
    return [
        _employer_assignment_response(db, _assignment_row(db, identity_id, assignment_id))
        for assignment_id in rows
    ]


def _validate_rubric_scores(
    assigned_rubric: Any, submitted_scores: list[dict[str, Any]]
) -> tuple[list[dict[str, Any]], int]:
    rubric = _json_value(assigned_rubric)
    by_name = {str(item["name"]): int(item["points"]) for item in rubric}
    names = [str(item["name"]).strip() for item in submitted_scores]
    if len(names) != len(set(names)) or set(names) != set(by_name):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="employer_evaluation_rubric_mismatch",
        )

    normalized: list[dict[str, Any]] = []
    awarded_total = 0
    maximum_total = sum(by_name.values())
    for item, name in zip(submitted_scores, names, strict=True):
        awarded = int(item["points_awarded"])
        maximum = by_name[name]
        if awarded < 0 or awarded > maximum:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="employer_evaluation_score_out_of_range",
            )
        normalized.append(
            {"name": name, "points_awarded": awarded, "max_points": maximum}
        )
        awarded_total += awarded
    score = int((awarded_total * 100 / maximum_total) + 0.5)
    return normalized, score


def save_employer_evaluation(
    db: Session,
    principal: Principal,
    assignment_id: str,
    rubric_scores: list[dict[str, Any]],
    feedback: str | None,
    release_to_candidate: bool,
) -> dict[str, Any]:
    identity_id, _ = _ensure_company(db, principal)
    assignment = _assignment_row(db, identity_id, assignment_id)
    if db.execute(
        text("SELECT 1 FROM task_submission WHERE assignment_id = :assignment_id LIMIT 1"),
        {"assignment_id": assignment_id},
    ).scalar_one_or_none() is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="employer_evaluation_submission_required",
        )
    normalized, score = _validate_rubric_scores(assignment["rubric"], rubric_scores)
    clean_feedback = feedback.strip() if feedback else None
    now = _now()
    evaluation_id = assignment["evaluation_id"] or str(uuid4())
    released_at = now if release_to_candidate else None
    if assignment["evaluation_id"] is None:
        db.execute(
            text(
                "INSERT INTO employer_evaluation "
                "(id, assignment_id, employer_identity_id, score, rubric_scores, feedback, "
                "status, created_at, updated_at, released_at) "
                "VALUES (:id, :assignment_id, :identity_id, :score, :rubric_scores, :feedback, "
                ":status, :created_at, :updated_at, :released_at)"
            ),
            {
                "id": evaluation_id,
                "assignment_id": assignment_id,
                "identity_id": identity_id,
                "score": score,
                "rubric_scores": json.dumps(normalized, separators=(",", ":")),
                "feedback": clean_feedback,
                "status": "released" if release_to_candidate else "draft",
                "created_at": now,
                "updated_at": now,
                "released_at": released_at,
            },
        )
    else:
        db.execute(
            text(
                "UPDATE employer_evaluation SET score = :score, rubric_scores = :rubric_scores, "
                "feedback = :feedback, status = :status, updated_at = :updated_at, "
                "released_at = :released_at WHERE id = :id AND employer_identity_id = :identity_id"
            ),
            {
                "id": evaluation_id,
                "identity_id": identity_id,
                "score": score,
                "rubric_scores": json.dumps(normalized, separators=(",", ":")),
                "feedback": clean_feedback,
                "status": "released" if release_to_candidate else "draft",
                "updated_at": now,
                "released_at": released_at,
            },
        )
    db.commit()
    refreshed = _assignment_row(db, identity_id, assignment_id)
    return _employer_assignment_response(db, refreshed)


def get_released_candidate_evaluation(
    db: Session, assignment_id: str
) -> dict[str, Any] | None:
    row = db.execute(
        text(
            "SELECT score, feedback, status, released_at FROM employer_evaluation "
            "WHERE assignment_id = :assignment_id"
        ),
        {"assignment_id": assignment_id},
    ).mappings().one_or_none()
    return _candidate_evaluation_response(dict(row) if row is not None else None)
