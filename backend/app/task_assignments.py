"""Match-bound employer task assignments and candidate submissions."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

from fastapi import HTTPException, status
from sqlalchemy import text
from sqlalchemy.orm import Session

from .auth import Principal, sync_identity


def _now() -> datetime:
    return datetime.now(UTC)


def _aware(value: datetime | str) -> datetime:
    """SQLite returns naive timestamps even when the column is timezone-aware."""

    if isinstance(value, str):
        value = datetime.fromisoformat(value)
    return value if value.tzinfo is not None else value.replace(tzinfo=UTC)


def _json_list(value: Any) -> list[str]:
    if isinstance(value, str):
        return json.loads(value)
    return list(value or [])


def _candidate_profile_id(db: Session, principal: Principal) -> str:
    identity = sync_identity(db, principal)
    profile_id = db.execute(
        text("SELECT id FROM candidate_profile WHERE identity_id = :identity_id"),
        {"identity_id": identity["id"]},
    ).scalar_one_or_none()
    if profile_id is None:
        profile_id = str(uuid4())
        db.execute(
            text("INSERT INTO candidate_profile (id, identity_id) VALUES (:id, :identity_id)"),
            {"id": profile_id, "identity_id": identity["id"]},
        )
        db.commit()
    return profile_id


def _published_task_rows_for_match(db: Session, match_id: str) -> list[dict[str, Any]]:
    return [
        dict(row)
        for row in db.execute(
            text(
                "SELECT tm.id AS match_id, tm.candidate_profile_id, et.id AS task_id, "
                "et.pipeline_stage_id, etv.id AS task_version_id, etv.deadline_hours "
                "FROM talent_match tm "
                "JOIN invitation i ON i.id = tm.invitation_id "
                "JOIN hiring_need hn ON hn.company_id = i.company_id "
                "JOIN employer_task et ON et.hiring_need_id = hn.id "
                "JOIN employer_task_version etv ON etv.task_id = et.id "
                "  AND etv.status = 'published' "
                "WHERE tm.id = :match_id AND et.pipeline_stage_id IS NOT NULL"
            ),
            {"match_id": match_id},
        ).mappings()
    ]


def ensure_assignments_for_match(db: Session, match_id: str) -> bool:
    """Assign each published employer task once, without committing the caller's transaction."""

    created = False
    assigned_at = _now()
    for task in _published_task_rows_for_match(db, match_id):
        exists = db.execute(
            text(
                "SELECT 1 FROM task_assignment WHERE match_id = :match_id AND task_id = :task_id"
            ),
            {"match_id": match_id, "task_id": task["task_id"]},
        ).scalar_one_or_none()
        if exists is not None:
            continue
        db.execute(
            text(
                "INSERT INTO task_assignment "
                "(id, match_id, candidate_profile_id, task_id, task_version_id, "
                "pipeline_stage_id, assigned_at, due_at) "
                "VALUES (:id, :match_id, :candidate_profile_id, :task_id, :task_version_id, "
                ":pipeline_stage_id, :assigned_at, :due_at)"
            ),
            {
                "id": str(uuid4()),
                "match_id": match_id,
                "candidate_profile_id": task["candidate_profile_id"],
                "task_id": task["task_id"],
                "task_version_id": task["task_version_id"],
                "pipeline_stage_id": task["pipeline_stage_id"],
                "assigned_at": assigned_at,
                "due_at": assigned_at + timedelta(hours=int(task["deadline_hours"])),
            },
        )
        created = True
    return created


def _assignment_row(db: Session, profile_id: str, assignment_id: str) -> dict[str, Any]:
    row = db.execute(
        text(
            "SELECT ta.id, ta.match_id, ta.candidate_profile_id, ta.task_id, "
            "ta.task_version_id, ta.pipeline_stage_id, ta.status, ta.assigned_at, "
            "ta.due_at, ta.submitted_at, ps.title AS stage_title, "
            "etv.version_number, etv.title, etv.instructions, etv.target_skills, "
            "etv.expected_grade, etv.estimated_minutes "
            "FROM task_assignment ta "
            "JOIN talent_match tm ON tm.id = ta.match_id "
            "JOIN pipeline_stage ps ON ps.id = ta.pipeline_stage_id "
            "JOIN employer_task_version etv ON etv.id = ta.task_version_id "
            "WHERE ta.id = :assignment_id AND ta.candidate_profile_id = :profile_id "
            "AND tm.candidate_profile_id = :profile_id"
        ),
        {"assignment_id": assignment_id, "profile_id": profile_id},
    ).mappings().one_or_none()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="task_assignment_not_found")
    result = dict(row)
    if _aware(result["due_at"]) <= _now() and result["status"] != "submitted":
        db.execute(
            text(
                "UPDATE task_assignment SET status = 'expired' "
                "WHERE id = :assignment_id AND status <> 'submitted'"
            ),
            {"assignment_id": assignment_id},
        )
        db.commit()
        result["status"] = "expired"
    result["target_skills"] = _json_list(result["target_skills"])
    result["submissions"] = [
        dict(submission)
        for submission in db.execute(
            text(
                "SELECT id, attempt_number, response_text, submitted_at "
                "FROM task_submission WHERE assignment_id = :assignment_id "
                "ORDER BY attempt_number"
            ),
            {"assignment_id": assignment_id},
        ).mappings()
    ]
    return result


def _public_assignment(db: Session, profile_id: str, assignment_id: str) -> dict[str, Any]:
    row = _assignment_row(db, profile_id, assignment_id)
    return {
        "id": row["id"],
        "match_id": row["match_id"],
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
            "target_skills": row["target_skills"],
            "expected_grade": row["expected_grade"],
            "estimated_minutes": row["estimated_minutes"],
        },
        "submissions": row["submissions"],
    }


def list_candidate_assignments(db: Session, principal: Principal) -> list[dict[str, Any]]:
    profile_id = _candidate_profile_id(db, principal)
    match_ids = db.execute(
        text("SELECT id FROM talent_match WHERE candidate_profile_id = :profile_id"),
        {"profile_id": profile_id},
    ).scalars().all()
    created = any(ensure_assignments_for_match(db, match_id) for match_id in match_ids)
    if created:
        db.commit()
    assignments = db.execute(
        text(
            "SELECT id FROM task_assignment WHERE candidate_profile_id = :profile_id "
            "ORDER BY due_at, assigned_at, id"
        ),
        {"profile_id": profile_id},
    ).scalars().all()
    return [_public_assignment(db, profile_id, assignment_id) for assignment_id in assignments]


def submit_candidate_assignment(
    db: Session,
    principal: Principal,
    assignment_id: str,
    response_text: str,
) -> dict[str, Any]:
    profile_id = _candidate_profile_id(db, principal)
    if not response_text.strip():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="task_submission_response_required",
        )
    row = _assignment_row(db, profile_id, assignment_id)
    if row["status"] == "expired" or _aware(row["due_at"]) <= _now():
        if row["status"] != "expired":
            db.execute(
                text("UPDATE task_assignment SET status = 'expired' WHERE id = :id"),
                {"id": assignment_id},
            )
            db.commit()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="task_assignment_deadline_passed",
        )
    attempt_number = int(
        db.execute(
            text(
                "SELECT COALESCE(MAX(attempt_number), 0) + 1 "
                "FROM task_submission WHERE assignment_id = :assignment_id"
            ),
            {"assignment_id": assignment_id},
        ).scalar_one()
    )
    submitted_at = _now()
    db.execute(
        text(
            "INSERT INTO task_submission "
            "(id, assignment_id, attempt_number, response_text, submitted_at) "
            "VALUES (:id, :assignment_id, :attempt_number, :response_text, :submitted_at)"
        ),
        {
            "id": str(uuid4()),
            "assignment_id": assignment_id,
            "attempt_number": attempt_number,
            "response_text": response_text.strip(),
            "submitted_at": submitted_at,
        },
    )
    db.execute(
        text(
            "UPDATE task_assignment SET status = 'submitted', submitted_at = :submitted_at "
            "WHERE id = :assignment_id"
        ),
        {"assignment_id": assignment_id, "submitted_at": submitted_at},
    )
    db.commit()
    return _public_assignment(db, profile_id, assignment_id)
