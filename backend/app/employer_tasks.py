"""Employer-owned task authoring and immutable task versions."""

from __future__ import annotations

import json
from typing import Any
from uuid import uuid4

from fastapi import HTTPException, status
from sqlalchemy import bindparam, text
from sqlalchemy.orm import Session

from .auth import Principal
from .companies import _ensure_company

GRADES = {"junior", "middle", "senior"}


def _require_hiring_need(db: Session, principal: Principal) -> tuple[str, str, str]:
    identity_id, company_id = _ensure_company(db, principal)
    hiring_need_id = db.execute(
        text("SELECT id FROM hiring_need WHERE company_id = :company_id"),
        {"company_id": company_id},
    ).scalar_one_or_none()
    if hiring_need_id is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="hiring_need_not_found")
    return identity_id, company_id, hiring_need_id


def _validate_stage(db: Session, company_id: str, hiring_need_id: str, stage_id: str) -> None:
    stage = db.execute(
        text(
            "SELECT ps.stage_type FROM pipeline_stage ps "
            "JOIN hiring_pipeline hp ON hp.id = ps.pipeline_id "
            "JOIN hiring_need hn ON hn.id = hp.hiring_need_id "
            "WHERE ps.id = :stage_id AND hn.id = :need_id AND hn.company_id = :company_id"
        ),
        {"stage_id": stage_id, "need_id": hiring_need_id, "company_id": company_id},
    ).scalar_one_or_none()
    if stage is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="employer_task_stage_not_found",
        )
    if stage != "employer_task":
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="employer_task_stage_required",
        )


def _validate_content(db: Session, payload: dict[str, Any]) -> dict[str, Any]:
    target_skills = [skill.strip() for skill in payload["target_skills"]]
    if len(set(target_skills)) != len(target_skills):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="employer_task_duplicate_skill",
        )
    if any(not skill for skill in target_skills):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="employer_task_skill_required",
        )
    if payload["expected_grade"] not in GRADES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="employer_task_grade_invalid",
        )

    skill_rows = list(
        db.execute(
            text(
                "SELECT slug FROM skill WHERE active = :active AND slug IN :slugs"
            ).bindparams(bindparam("slugs", expanding=True)),
            {"active": True, "slugs": tuple(target_skills)},
        ).scalars()
    )
    if set(skill_rows) != set(target_skills):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="employer_task_skill_not_available",
        )

    rubric = []
    for dimension in payload["rubric"]:
        name = dimension["name"].strip()
        if not name:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="employer_task_rubric_name_required",
            )
        rubric.append(
            {
                "name": name,
                "points": int(dimension["points"]),
                "description": (dimension.get("description") or "").strip() or None,
            }
        )
    if sum(item["points"] for item in rubric) <= 0:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="employer_task_rubric_points_required",
        )
    return {
        "title": payload["title"].strip(),
        "instructions": payload["instructions"].strip(),
        "target_skills": target_skills,
        "expected_grade": payload["expected_grade"],
        "estimated_minutes": int(payload["estimated_minutes"]),
        "deadline_hours": int(payload["deadline_hours"]),
        "rubric": rubric,
    }


def _task_scope(db: Session, company_id: str, task_id: str) -> dict[str, Any]:
    task = db.execute(
        text(
            "SELECT et.id, et.hiring_need_id, et.pipeline_stage_id, et.created_at, et.updated_at "
            "FROM employer_task et JOIN hiring_need hn ON hn.id = et.hiring_need_id "
            "WHERE et.id = :task_id AND hn.company_id = :company_id"
        ),
        {"task_id": task_id, "company_id": company_id},
    ).mappings().one_or_none()
    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="employer_task_not_found")
    return dict(task)


def _task_response(db: Session, task: dict[str, Any]) -> dict[str, Any]:
    versions = [
        dict(row)
        for row in db.execute(
            text(
                "SELECT id, version_number, status, title, instructions, target_skills, "
                "expected_grade, estimated_minutes, deadline_hours, rubric, created_at, published_at "
                "FROM employer_task_version WHERE task_id = :task_id "
                "ORDER BY version_number"
            ),
            {"task_id": task["id"]},
        ).mappings()
    ]
    current = next((version for version in reversed(versions) if version["status"] == "draft"), None)
    if current is None:
        current = next((version for version in reversed(versions) if version["status"] == "published"), None)
    if current is None:
        current = versions[-1]
    for version in versions:
        if isinstance(version["target_skills"], str):
            version["target_skills"] = json.loads(version["target_skills"])
        if isinstance(version["rubric"], str):
            version["rubric"] = json.loads(version["rubric"])
    return {
        **task,
        "status": current["status"],
        "current_version": current,
        "versions": [
            {
                "id": version["id"],
                "version_number": version["version_number"],
                "status": version["status"],
                "created_at": version["created_at"],
                "published_at": version["published_at"],
            }
            for version in versions
        ],
    }


def list_tasks(db: Session, principal: Principal) -> list[dict[str, Any]]:
    _, company_id, hiring_need_id = _require_hiring_need(db, principal)
    tasks = db.execute(
        text(
            "SELECT id, hiring_need_id, pipeline_stage_id, created_at, updated_at "
            "FROM employer_task WHERE hiring_need_id = :need_id ORDER BY created_at, id"
        ),
        {"need_id": hiring_need_id},
    ).mappings()
    del company_id  # Ownership was established by _require_hiring_need.
    return [_task_response(db, dict(task)) for task in tasks]


def create_task(
    db: Session,
    principal: Principal,
    stage_id: str,
    payload: dict[str, Any],
) -> dict[str, Any]:
    identity_id, company_id, hiring_need_id = _require_hiring_need(db, principal)
    _validate_stage(db, company_id, hiring_need_id, stage_id)
    content = _validate_content(db, payload)
    task_id = str(uuid4())
    db.execute(
        text(
            "INSERT INTO employer_task "
            "(id, hiring_need_id, pipeline_stage_id, created_by_identity_id) "
            "VALUES (:id, :need_id, :stage_id, :identity_id)"
        ),
        {"id": task_id, "need_id": hiring_need_id, "stage_id": stage_id, "identity_id": identity_id},
    )
    db.execute(
        text(
            "INSERT INTO employer_task_version "
            "(id, task_id, version_number, status, title, instructions, target_skills, "
            "expected_grade, estimated_minutes, deadline_hours, rubric, created_by_identity_id, updated_by_identity_id) "
            "VALUES (:id, :task_id, 1, 'draft', :title, :instructions, :target_skills, "
            ":expected_grade, :estimated_minutes, :deadline_hours, :rubric, :identity_id, :identity_id)"
        ),
        {
            "id": str(uuid4()),
            "task_id": task_id,
            "identity_id": identity_id,
            "target_skills": json.dumps(content["target_skills"], separators=(",", ":")),
            "rubric": json.dumps(content["rubric"], ensure_ascii=False, separators=(",", ":")),
            **{key: value for key, value in content.items() if key not in {"target_skills", "rubric"}},
        },
    )
    db.commit()
    return _task_response(db, _task_scope(db, company_id, task_id))


def _next_version(db: Session, task_id: str) -> int:
    return int(
        db.execute(
            text("SELECT COALESCE(MAX(version_number), 0) + 1 FROM employer_task_version WHERE task_id = :task_id"),
            {"task_id": task_id},
        ).scalar_one()
    )


def create_version(
    db: Session,
    principal: Principal,
    task_id: str,
    payload: dict[str, Any],
) -> dict[str, Any]:
    identity_id, company_id = _ensure_company(db, principal)
    _task_scope(db, company_id, task_id)
    if db.execute(
        text("SELECT 1 FROM employer_task_version WHERE task_id = :task_id AND status = 'draft'"),
        {"task_id": task_id},
    ).scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="employer_task_draft_exists")
    content = _validate_content(db, payload)
    db.execute(
        text(
            "INSERT INTO employer_task_version "
            "(id, task_id, version_number, status, title, instructions, target_skills, "
            "expected_grade, estimated_minutes, deadline_hours, rubric, created_by_identity_id, updated_by_identity_id) "
            "VALUES (:id, :task_id, :version_number, 'draft', :title, :instructions, :target_skills, "
            ":expected_grade, :estimated_minutes, :deadline_hours, :rubric, :identity_id, :identity_id)"
        ),
        {
            "id": str(uuid4()),
            "task_id": task_id,
            "version_number": _next_version(db, task_id),
            "identity_id": identity_id,
            "target_skills": json.dumps(content["target_skills"], separators=(",", ":")),
            "rubric": json.dumps(content["rubric"], ensure_ascii=False, separators=(",", ":")),
            **{key: value for key, value in content.items() if key not in {"target_skills", "rubric"}},
        },
    )
    db.execute(text("UPDATE employer_task SET updated_at = CURRENT_TIMESTAMP WHERE id = :id"), {"id": task_id})
    db.commit()
    return _task_response(db, _task_scope(db, company_id, task_id))


def update_draft(
    db: Session,
    principal: Principal,
    task_id: str,
    payload: dict[str, Any],
) -> dict[str, Any]:
    identity_id, company_id = _ensure_company(db, principal)
    task = _task_scope(db, company_id, task_id)
    content = _validate_content(db, payload)
    draft_id = db.execute(
        text("SELECT id FROM employer_task_version WHERE task_id = :task_id AND status = 'draft' ORDER BY version_number DESC"),
        {"task_id": task_id},
    ).scalar_one_or_none()
    if draft_id is None:
        version_number = _next_version(db, task_id)
        db.execute(
            text(
                "INSERT INTO employer_task_version "
                "(id, task_id, version_number, status, title, instructions, target_skills, "
                "expected_grade, estimated_minutes, deadline_hours, rubric, created_by_identity_id, updated_by_identity_id) "
                "VALUES (:id, :task_id, :version_number, 'draft', :title, :instructions, :target_skills, "
                ":expected_grade, :estimated_minutes, :deadline_hours, :rubric, :identity_id, :identity_id)"
            ),
            {
                "id": str(uuid4()),
                "task_id": task_id,
                "version_number": version_number,
                "identity_id": identity_id,
                "target_skills": json.dumps(content["target_skills"], separators=(",", ":")),
                "rubric": json.dumps(content["rubric"], ensure_ascii=False, separators=(",", ":")),
                **{key: value for key, value in content.items() if key not in {"target_skills", "rubric"}},
            },
        )
    else:
        db.execute(
            text(
                "UPDATE employer_task_version SET title = :title, instructions = :instructions, "
                "target_skills = :target_skills, expected_grade = :expected_grade, "
                "estimated_minutes = :estimated_minutes, deadline_hours = :deadline_hours, rubric = :rubric, "
                "updated_at = CURRENT_TIMESTAMP, updated_by_identity_id = :identity_id "
                "WHERE id = :id"
            ),
            {
                "id": draft_id,
                "identity_id": identity_id,
                "target_skills": json.dumps(content["target_skills"], separators=(",", ":")),
                "rubric": json.dumps(content["rubric"], ensure_ascii=False, separators=(",", ":")),
                **{key: value for key, value in content.items() if key not in {"target_skills", "rubric"}},
            },
        )
    db.execute(text("UPDATE employer_task SET updated_at = CURRENT_TIMESTAMP WHERE id = :id"), {"id": task["id"]})
    db.commit()
    return _task_response(db, _task_scope(db, company_id, task_id))


def publish_task(db: Session, principal: Principal, task_id: str) -> dict[str, Any]:
    identity_id, company_id = _ensure_company(db, principal)
    task = _task_scope(db, company_id, task_id)
    draft_id = db.execute(
        text(
            "SELECT id FROM employer_task_version WHERE task_id = :task_id AND status = 'draft' "
            "ORDER BY version_number DESC"
        ),
        {"task_id": task_id},
    ).scalar_one_or_none()
    if draft_id is None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="employer_task_draft_required")
    db.execute(
        text("UPDATE employer_task_version SET status = 'retired' WHERE task_id = :task_id AND status = 'published'"),
        {"task_id": task_id},
    )
    db.execute(
        text(
            "UPDATE employer_task_version SET status = 'published', published_at = CURRENT_TIMESTAMP, "
            "updated_at = CURRENT_TIMESTAMP, updated_by_identity_id = :identity_id, "
            "published_by_identity_id = :identity_id "
            "WHERE id = :id"
        ),
        {"id": draft_id, "identity_id": identity_id},
    )
    _index_approved_example(db, draft_id, identity_id)
    db.execute(text("UPDATE employer_task SET updated_at = CURRENT_TIMESTAMP WHERE id = :id"), {"id": task["id"]})
    db.commit()
    return _task_response(db, _task_scope(db, company_id, task_id))


def _index_approved_example(db: Session, task_version_id: str, identity_id: str) -> None:
    """Record a published immutable version in the employer task memory index."""

    if db.execute(
        text("SELECT 1 FROM employer_task_example WHERE task_version_id = :version_id"),
        {"version_id": task_version_id},
    ).scalar_one_or_none():
        return
    source = db.execute(
        text(
            "SELECT etv.target_skills, etv.estimated_minutes, etv.deadline_hours, "
            "et.hiring_need_id, hn.company_id, s.slug AS specialization_slug, "
            "g.slug AS grade_slug "
            "FROM employer_task_version etv "
            "JOIN employer_task et ON et.id = etv.task_id "
            "JOIN hiring_need hn ON hn.id = et.hiring_need_id "
            "JOIN specialization s ON s.id = hn.specialization_id "
            "JOIN grade g ON g.id = hn.grade_id "
            "WHERE etv.id = :version_id"
        ),
        {"version_id": task_version_id},
    ).mappings().one()
    db.execute(
        text(
            "INSERT INTO employer_task_example "
            "(id, task_version_id, company_id, specialization_slug, grade_slug, "
            "target_skills, estimated_minutes, deadline_hours, approval_status, "
            "approved_at, approved_by_identity_id) "
            "VALUES (:id, :version_id, :company_id, :specialization, :grade, "
            ":target_skills, :estimated_minutes, :deadline_hours, 'approved', "
            "CURRENT_TIMESTAMP, :identity_id)"
        ),
        {
            "id": str(uuid4()),
            "version_id": task_version_id,
            "company_id": source["company_id"],
            "specialization": source["specialization_slug"],
            "grade": source["grade_slug"],
            "target_skills": source["target_skills"],
            "estimated_minutes": source["estimated_minutes"],
            "deadline_hours": source["deadline_hours"],
            "identity_id": identity_id,
        },
    )
