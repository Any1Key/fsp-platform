from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from .assessments import AssessmentError, AssessmentService, public_attempt

app = FastAPI(
    title="FSP Talent Platform API",
    version="0.1.0",
    description="Bootstrap API. Codex implements the target domain from the requirements matrix.",
)

assessment_service = AssessmentService()


class CreateAttemptRequest(BaseModel):
    candidate_id: str = Field(min_length=1, max_length=128)
    specialization: str
    declared_grade: str


class SubmitAttemptRequest(BaseModel):
    answers: dict[str, int]
    followups: dict[str, str] = {}
    telemetry: dict[str, Any] = {}

@app.get("/health", tags=["system"])
def health() -> dict[str, str]:
    return {"status": "ok"}

@app.get("/api/v1/system/info", tags=["system"])
def system_info() -> dict[str, str]:
    return {
        "product": "FSP Talent Platform",
        "state": "bootstrap",
        "message": "Autonomous development workspace is ready.",
    }


@app.post("/api/v1/assessments/attempts", tags=["assessments"])
def create_assessment_attempt(request: CreateAttemptRequest) -> dict[str, Any]:
    try:
        attempt = assessment_service.create_attempt(request.candidate_id, request.specialization, request.declared_grade)
    except AssessmentError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return public_attempt(attempt)


@app.get("/api/v1/assessments/attempts/{attempt_id}", tags=["assessments"])
def get_assessment_attempt(attempt_id: str) -> dict[str, Any]:
    try:
        return public_attempt(assessment_service.get(attempt_id))
    except AssessmentError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.post("/api/v1/assessments/attempts/{attempt_id}/submit", tags=["assessments"])
def submit_assessment_attempt(attempt_id: str, request: SubmitAttemptRequest) -> dict[str, Any]:
    try:
        attempt = assessment_service.submit(attempt_id, request.answers, request.followups, request.telemetry)
    except AssessmentError as exc:
        status = 404 if str(exc) == "attempt_not_found" else 409
        raise HTTPException(status_code=status, detail=str(exc)) from exc
    return public_attempt(attempt)
