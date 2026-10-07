"""Employer-owned ordered hiring pipeline configuration."""

from __future__ import annotations

import json
from typing import Any
from uuid import uuid4

from fastapi import HTTPException, status
from sqlalchemy import text
from sqlalchemy.orm import Session

from .auth import Principal
from .companies import _ensure_company

STAGE_TYPES = {
    "platform_review",
    "employer_task",
    "questionnaire",
    "portfolio_review",
    "interview",
    "custom",
    "final_decision",
}

DEFAULT_STAGES = (
    {
        "stage_type": "platform_review",
        "title": "Проверка Verified Skill Passport",
        "required": True,
        "estimated_minutes": 15,
    },
    {
        "stage_type": "final_decision",
        "title": "Финальное решение",
        "required": True,
        "estimated_minutes": 15,
    },
)


def _require_hiring_need(db: Session, principal: Principal) -> tuple[str, str]:
    _, company_id = _ensure_company(db, principal)
    hiring_need_id = db.execute(
        text("SELECT id FROM hiring_need WHERE company_id = :company_id"),
        {"company_id": company_id},
    ).scalar_one_or_none()
    if hiring_need_id is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="hiring_need_not_found")
    return company_id, hiring_need_id


def _validate_stages(stages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not 2 <= len(stages) <= 12:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="hiring_pipeline_stage_count_invalid",
        )

    normalized: list[dict[str, Any]] = []
    for position, stage in enumerate(stages):
        stage_type = stage.get("stage_type")
        title = stage.get("title")
        if stage_type not in STAGE_TYPES:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="hiring_pipeline_stage_type_invalid",
            )
        if not isinstance(title, str) or not title.strip():
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="hiring_pipeline_stage_title_required",
            )
        normalized.append(
            {
                "position": position,
                "stage_type": stage_type,
                "title": title.strip(),
                "required": bool(stage.get("required", True)),
                "estimated_minutes": int(stage.get("estimated_minutes", 30)),
            }
        )

    if sum(stage["stage_type"] == "platform_review" for stage in normalized) != 1:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="hiring_pipeline_platform_review_required",
        )
    if sum(stage["stage_type"] == "final_decision" for stage in normalized) != 1:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="hiring_pipeline_final_decision_required",
        )
    if any(not 5 <= stage["estimated_minutes"] <= 480 for stage in normalized):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="hiring_pipeline_duration_invalid",
        )
    return normalized


def _ensure_pipeline(db: Session, hiring_need_id: str) -> tuple[str, bool]:
    pipeline_id = db.execute(
        text("SELECT id FROM hiring_pipeline WHERE hiring_need_id = :hiring_need_id"),
        {"hiring_need_id": hiring_need_id},
    ).scalar_one_or_none()
    if pipeline_id is not None:
        return pipeline_id, False

    pipeline_id = str(uuid4())
    db.execute(
        text("INSERT INTO hiring_pipeline (id, hiring_need_id) VALUES (:id, :hiring_need_id)"),
        {"id": pipeline_id, "hiring_need_id": hiring_need_id},
    )
    for position, stage in enumerate(DEFAULT_STAGES):
        db.execute(
            text(
                "INSERT INTO pipeline_stage "
                "(id, pipeline_id, position, stage_type, title, required, estimated_minutes) "
                "VALUES (:id, :pipeline_id, :position, :stage_type, :title, :required, :estimated_minutes)"
            ),
            {
                "id": str(uuid4()),
                "pipeline_id": pipeline_id,
                "position": position,
                **stage,
            },
        )
    return pipeline_id, True


def _pipeline_response(db: Session, pipeline_id: str, hiring_need_id: str) -> dict[str, Any]:
    pipeline = db.execute(
        text(
            "SELECT id, hiring_need_id, created_at, updated_at "
            "FROM hiring_pipeline WHERE id = :pipeline_id AND hiring_need_id = :hiring_need_id"
        ),
        {"pipeline_id": pipeline_id, "hiring_need_id": hiring_need_id},
    ).mappings().one()
    stages = db.execute(
        text(
            "SELECT id, position, stage_type, title, required, estimated_minutes "
            "FROM pipeline_stage WHERE pipeline_id = :pipeline_id ORDER BY position, id"
        ),
        {"pipeline_id": pipeline_id},
    ).mappings()
    return {**pipeline, "stages": [dict(stage) for stage in stages]}


def get_hiring_pipeline(db: Session, principal: Principal) -> dict[str, Any]:
    _, hiring_need_id = _require_hiring_need(db, principal)
    pipeline_id, created = _ensure_pipeline(db, hiring_need_id)
    if created:
        db.commit()
    return _pipeline_response(db, pipeline_id, hiring_need_id)


def update_hiring_pipeline(
    db: Session,
    principal: Principal,
    stages: list[dict[str, Any]],
) -> dict[str, Any]:
    _, hiring_need_id = _require_hiring_need(db, principal)
    normalized = _validate_stages(stages)
    pipeline_id, _ = _ensure_pipeline(db, hiring_need_id)
    db.execute(text("DELETE FROM pipeline_stage WHERE pipeline_id = :pipeline_id"), {"pipeline_id": pipeline_id})
    for stage in normalized:
        db.execute(
            text(
                "INSERT INTO pipeline_stage "
                "(id, pipeline_id, position, stage_type, title, required, estimated_minutes) "
                "VALUES (:id, :pipeline_id, :position, :stage_type, :title, :required, :estimated_minutes)"
            ),
            {"id": str(uuid4()), "pipeline_id": pipeline_id, **stage},
        )
    db.execute(
        text("UPDATE hiring_pipeline SET updated_at = CURRENT_TIMESTAMP WHERE id = :pipeline_id"),
        {"pipeline_id": pipeline_id},
    )
    db.commit()
    return _pipeline_response(db, pipeline_id, hiring_need_id)


def pipeline_snapshot_for_company(db: Session, company_id: str) -> list[dict[str, Any]]:
    rows = db.execute(
        text(
            "SELECT ps.stage_type, ps.title, ps.required, ps.estimated_minutes "
            "FROM pipeline_stage ps "
            "JOIN hiring_pipeline hp ON hp.id = ps.pipeline_id "
            "JOIN hiring_need hn ON hn.id = hp.hiring_need_id "
            "WHERE hn.company_id = :company_id ORDER BY ps.position, ps.id"
        ),
        {"company_id": company_id},
    ).mappings()
    return [dict(row) for row in rows]


def snapshot_json(stages: list[dict[str, Any]]) -> str:
    """Serialize only the safe, candidate-visible stage metadata."""

    return json.dumps(stages, separators=(",", ":"), ensure_ascii=False)
