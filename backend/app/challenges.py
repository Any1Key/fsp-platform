"""Recurring short employer challenges bound to an existing match."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

from fastapi import HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from .auth import Principal, sync_identity
from .companies import _ensure_company

CHALLENGE_DEADLINE_HOURS = 72


def _now() -> datetime:
    return datetime.now(UTC)


def _aware(value: datetime | str) -> datetime:
    if isinstance(value, str):
        value = datetime.fromisoformat(value)
    return value if value.tzinfo is not None else value.replace(tzinfo=UTC)


def _json(value: Any) -> Any:
    return json.loads(value) if isinstance(value, str) else value


def _validate_content(payload: dict[str, Any]) -> dict[str, Any]:
    title = str(payload.get("title", "")).strip()
    instructions = str(payload.get("instructions", "")).strip()
    target_skill = str(payload.get("target_skill", "")).strip()
    estimated_minutes = int(payload.get("estimated_minutes", 0))
    cadence_days = int(payload.get("cadence_days", 0))
    if not title or not instructions or not target_skill:
        raise HTTPException(status_code=422, detail="challenge_fields_required")
    if not 5 <= estimated_minutes <= 20:
        raise HTTPException(status_code=422, detail="challenge_duration_invalid")
    if not 1 <= cadence_days <= 90:
        raise HTTPException(status_code=422, detail="challenge_cadence_invalid")
    rubric = []
    for item in payload.get("rubric", []):
        name = str(item.get("name", "")).strip()
        points = int(item.get("points", 0))
        description = str(item.get("description") or "").strip() or None
        if not name or points <= 0:
            raise HTTPException(status_code=422, detail="challenge_rubric_invalid")
        rubric.append({"name": name, "points": points, "description": description})
    names = [item["name"] for item in rubric]
    if not rubric or len(names) != len(set(names)) or sum(item["points"] for item in rubric) <= 0:
        raise HTTPException(status_code=422, detail="challenge_rubric_invalid")
    return {
        "title": title,
        "instructions": instructions,
        "target_skill": target_skill,
        "estimated_minutes": estimated_minutes,
        "cadence_days": cadence_days,
        "rubric": rubric,
    }


def _assignment_row(db: Session, assignment_id: str, *, identity_id: str | None = None, profile_id: str | None = None):
    filters = ["ca.id = :assignment_id"]
    params: dict[str, Any] = {"assignment_id": assignment_id}
    if identity_id is not None:
        filters.append("c.owner_identity_id = :identity_id")
        params["identity_id"] = identity_id
    if profile_id is not None:
        filters.append("tm.candidate_profile_id = :profile_id")
        params["profile_id"] = profile_id
    row = db.execute(
        text(
            "SELECT ca.id, ca.challenge_id, ca.cycle_number, ca.assigned_at, ca.due_at, ca.status, "
            "ca.submitted_at, ch.company_id, ch.match_id, ch.title, ch.instructions, ch.target_skill, "
            "ch.estimated_minutes, ch.cadence_days, ch.rubric, ch.status AS challenge_status, "
            "tm.candidate_profile_id, cp.display_name AS candidate_display_name, "
            "c.owner_identity_id, cs.id AS submission_id, cs.response_text, cs.submitted_at AS response_submitted_at, "
            "cr.id AS result_id, cr.score, cr.rubric_scores, cr.feedback, cr.status AS result_status, "
            "cr.evidence_fresh_until, cr.released_at "
            "FROM challenge_assignment ca JOIN challenge ch ON ch.id = ca.challenge_id "
            "JOIN talent_match tm ON tm.id = ch.match_id "
            "JOIN invitation i ON i.id = tm.invitation_id "
            "JOIN company c ON c.id = i.company_id "
            "JOIN candidate_profile cp ON cp.id = tm.candidate_profile_id "
            "LEFT JOIN challenge_submission cs ON cs.assignment_id = ca.id "
            "LEFT JOIN challenge_result cr ON cr.assignment_id = ca.id "
            f"WHERE {' AND '.join(filters)}"
        ),
        params,
    ).mappings().one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="challenge_assignment_not_found")
    return row


def _sync_expired(db: Session, row) -> str:
    if row["status"] == "assigned" and _aware(row["due_at"]) < _now():
        db.execute(
            text("UPDATE challenge_assignment SET status = 'expired' WHERE id = :id"),
            {"id": row["id"]},
        )
        db.commit()
        return "expired"
    if row["status"] == "assigned" and _aware(row["assigned_at"]) > _now():
        return "scheduled"
    return row["status"]


def _public(row, *, employer: bool) -> dict[str, Any]:
    status_value = row["status"]
    if row["status"] == "assigned":
        if _aware(row["due_at"]) < _now():
            status_value = "expired"
        elif _aware(row["assigned_at"]) > _now():
            status_value = "scheduled"
    result = None
    if row["result_id"] is not None and (employer or row["result_status"] == "released"):
        result = {
            "score": row["score"],
            "feedback": row["feedback"],
            "status": row["result_status"],
            "evidence_fresh_until": row["evidence_fresh_until"],
            "released_at": row["released_at"],
        }
        if employer:
            result["rubric_scores"] = _json(row["rubric_scores"])
    submission = None
    if row["submission_id"] is not None:
        submission = {
            "id": row["submission_id"],
            "response_text": row["response_text"],
            "submitted_at": row["response_submitted_at"],
        }
    payload = {
        "id": row["id"],
        "challenge_id": row["challenge_id"],
        "match_id": row["match_id"],
        "cycle_number": row["cycle_number"],
        "status": status_value,
        "assigned_at": row["assigned_at"],
        "due_at": row["due_at"],
        "submitted_at": row["submitted_at"],
        "challenge": {
            "title": row["title"],
            "instructions": row["instructions"],
            "target_skill": row["target_skill"],
            "estimated_minutes": row["estimated_minutes"],
            "cadence_days": row["cadence_days"],
        },
        "submission": submission,
        "result": result,
    }
    if employer:
        payload["candidate_display_name"] = row["candidate_display_name"] or "Candidate"
        payload["rubric"] = _json(row["rubric"])
    return payload


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


def create_challenge(db: Session, principal: Principal, payload: dict[str, Any]) -> dict[str, Any]:
    identity_id, company_id = _ensure_company(db, principal)
    content = _validate_content(payload)
    match = db.execute(
        text(
            "SELECT tm.id, tm.candidate_profile_id FROM talent_match tm "
            "JOIN invitation i ON i.id = tm.invitation_id "
            "WHERE tm.id = :match_id AND tm.employer_identity_id = :identity_id "
            "AND i.company_id = :company_id"
        ),
        {"match_id": payload["match_id"], "identity_id": identity_id, "company_id": company_id},
    ).mappings().one_or_none()
    if match is None:
        raise HTTPException(status_code=404, detail="challenge_match_not_found")
    challenge_id = str(uuid4())
    now = _now()
    db.execute(
        text(
            "INSERT INTO challenge (id, company_id, match_id, created_by_identity_id, title, instructions, "
            "target_skill, estimated_minutes, cadence_days, rubric) VALUES "
            "(:id, :company_id, :match_id, :identity_id, :title, :instructions, :target_skill, "
            ":estimated_minutes, :cadence_days, :rubric)"
        ),
        {"id": challenge_id, "company_id": company_id, "match_id": payload["match_id"], "identity_id": identity_id, **{key: value if key != "rubric" else json.dumps(value, ensure_ascii=False, separators=(",", ":")) for key, value in content.items()}},
    )
    assignment_id = str(uuid4())
    db.execute(
        text(
            "INSERT INTO challenge_assignment (id, challenge_id, cycle_number, assigned_at, due_at) "
            "VALUES (:id, :challenge_id, 1, :assigned_at, :due_at)"
        ),
        {"id": assignment_id, "challenge_id": challenge_id, "assigned_at": now, "due_at": now + timedelta(hours=CHALLENGE_DEADLINE_HOURS)},
    )
    db.commit()
    return _public(_assignment_row(db, assignment_id, identity_id=identity_id), employer=True)


def list_employer_challenges(db: Session, principal: Principal) -> list[dict[str, Any]]:
    identity_id, _ = _ensure_company(db, principal)
    rows = db.execute(
        text(
            "SELECT ca.id FROM challenge_assignment ca JOIN challenge ch ON ch.id = ca.challenge_id "
            "JOIN talent_match tm ON tm.id = ch.match_id JOIN invitation i ON i.id = tm.invitation_id "
            "WHERE i.employer_identity_id = :identity_id ORDER BY ca.assigned_at DESC, ca.cycle_number DESC"
        ),
        {"identity_id": identity_id},
    ).scalars()
    return [_public(_assignment_row(db, assignment_id, identity_id=identity_id), employer=True) for assignment_id in rows]


def list_candidate_challenges(db: Session, principal: Principal) -> list[dict[str, Any]]:
    profile_id = _candidate_profile_id(db, principal)
    rows = db.execute(
        text(
            "SELECT ca.id FROM challenge_assignment ca JOIN challenge ch ON ch.id = ca.challenge_id "
            "JOIN talent_match tm ON tm.id = ch.match_id "
            "WHERE tm.candidate_profile_id = :profile_id AND ch.status = 'active' "
            "ORDER BY ca.assigned_at DESC, ca.cycle_number DESC"
        ),
        {"profile_id": profile_id},
    ).scalars()
    return [_public(_assignment_row(db, assignment_id, profile_id=profile_id), employer=False) for assignment_id in rows]


def submit_challenge(db: Session, principal: Principal, assignment_id: str, response_text: str) -> dict[str, Any]:
    profile_id = _candidate_profile_id(db, principal)
    row = _assignment_row(db, assignment_id, profile_id=profile_id)
    status_value = _sync_expired(db, row)
    if status_value == "scheduled":
        raise HTTPException(status_code=409, detail="challenge_not_started")
    if status_value == "expired":
        raise HTTPException(status_code=409, detail="challenge_deadline_passed")
    if row["submission_id"] is not None:
        raise HTTPException(status_code=409, detail="challenge_submission_exists")
    clean = response_text.strip()
    if not clean:
        raise HTTPException(status_code=422, detail="challenge_response_required")
    now = _now()
    db.execute(
        text("INSERT INTO challenge_submission (id, assignment_id, response_text, submitted_at) VALUES (:id, :assignment_id, :response_text, :submitted_at)"),
        {"id": str(uuid4()), "assignment_id": assignment_id, "response_text": clean, "submitted_at": now},
    )
    db.execute(text("UPDATE challenge_assignment SET status = 'submitted', submitted_at = :now WHERE id = :id"), {"id": assignment_id, "now": now})
    db.commit()
    return _public(_assignment_row(db, assignment_id, profile_id=profile_id), employer=False)


def _validate_scores(rubric_value: Any, scores: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], int]:
    rubric = _json(rubric_value)
    maximums = {item["name"]: int(item["points"]) for item in rubric}
    names = [str(item.get("name", "")).strip() for item in scores]
    if set(names) != set(maximums) or len(names) != len(set(names)):
        raise HTTPException(status_code=422, detail="challenge_rubric_mismatch")
    normalized = []
    total = 0
    for item, name in zip(scores, names, strict=True):
        awarded = int(item.get("points_awarded", -1))
        if awarded < 0 or awarded > maximums[name]:
            raise HTTPException(status_code=422, detail="challenge_score_out_of_range")
        normalized.append({"name": name, "points_awarded": awarded, "max_points": maximums[name]})
        total += awarded
    maximum = sum(maximums.values())
    return normalized, int((total * 100 / maximum) + 0.5)


def grade_challenge(db: Session, principal: Principal, assignment_id: str, scores: list[dict[str, Any]], feedback: str | None, release: bool) -> dict[str, Any]:
    identity_id, _ = _ensure_company(db, principal)
    row = _assignment_row(db, assignment_id, identity_id=identity_id)
    if row["submission_id"] is None:
        raise HTTPException(status_code=409, detail="challenge_submission_required")
    if row["result_id"] is not None:
        raise HTTPException(status_code=409, detail="challenge_result_exists")
    normalized, score = _validate_scores(row["rubric"], scores)
    now = _now()
    freshness = now + timedelta(days=int(row["cadence_days"])) if release else None
    db.execute(
        text(
            "INSERT INTO challenge_result (id, assignment_id, employer_identity_id, score, rubric_scores, feedback, status, "
            "evidence_fresh_until, created_at, updated_at, released_at) VALUES "
            "(:id, :assignment_id, :identity_id, :score, :rubric_scores, :feedback, :result_status, :freshness, :now, :now, :released_at)"
        ),
        {"id": str(uuid4()), "assignment_id": assignment_id, "identity_id": identity_id, "score": score, "rubric_scores": json.dumps(normalized, separators=(",", ":")), "feedback": feedback.strip() if feedback else None, "result_status": "released" if release else "draft", "freshness": freshness, "now": now, "released_at": now if release else None},
    )
    db.execute(text("UPDATE challenge_assignment SET status = 'graded' WHERE id = :id"), {"id": assignment_id})
    if release:
        next_cycle = int(row["cycle_number"]) + 1
        assigned_at = freshness
        db.execute(
            text("INSERT INTO challenge_assignment (id, challenge_id, cycle_number, assigned_at, due_at) VALUES (:id, :challenge_id, :cycle_number, :assigned_at, :due_at)"),
            {"id": str(uuid4()), "challenge_id": row["challenge_id"], "cycle_number": next_cycle, "assigned_at": assigned_at, "due_at": assigned_at + timedelta(hours=CHALLENGE_DEADLINE_HOURS)},
        )
    db.commit()
    return _public(_assignment_row(db, assignment_id, identity_id=identity_id), employer=True)
