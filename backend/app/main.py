import re
from typing import Annotated, Any
from uuid import uuid4

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from starlette.exceptions import HTTPException as StarletteHTTPException

from .assessments import AssessmentError, AssessmentService, public_attempt
from .db import get_db_session
from .errors import ErrorResponse, error_response, normalize_http_error

app = FastAPI(
    title="FSP Talent Platform API",
    version="0.1.0",
    description="Bootstrap API. Codex implements the target domain from the requirements matrix.",
)

REQUEST_ID_PATTERN = re.compile(r"^[A-Za-z0-9._-]{1,128}$")

assessment_service = AssessmentService()


class CreateAttemptRequest(BaseModel):
    candidate_id: str = Field(min_length=1, max_length=128)
    specialization: str
    declared_grade: str


class SubmitAttemptRequest(BaseModel):
    answers: dict[str, int]
    followups: dict[str, str] = Field(default_factory=dict)
    telemetry: dict[str, Any] = Field(default_factory=dict)


def _request_id(value: str | None) -> str:
    if value and REQUEST_ID_PATTERN.fullmatch(value):
        return value
    return str(uuid4())


@app.middleware("http")
async def request_id_middleware(request: Request, call_next):
    request.state.request_id = _request_id(request.headers.get("X-Request-ID"))
    response = await call_next(request)
    response.headers["X-Request-ID"] = request.state.request_id
    return response


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    code, message = normalize_http_error(exc.status_code, exc.detail)
    return error_response(request, status_code=exc.status_code, code=code, message=message)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    del exc  # Field details stay server-side; the public contract is intentionally stable.
    code, message = normalize_http_error(422, None)
    return error_response(request, status_code=422, code=code, message=message)


@app.exception_handler(Exception)
async def unexpected_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    del exc  # Do not serialize implementation details, secrets, or SQL text.
    code, message = normalize_http_error(500, None)
    return error_response(request, status_code=500, code=code, message=message)

@app.get("/health", tags=["system"], response_model=dict[str, str])
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get(
    "/health/ready",
    tags=["system"],
    response_model=dict[str, str],
    responses={503: {"model": ErrorResponse, "description": "Database unavailable"}},
)
def readiness(db: Annotated[Session, Depends(get_db_session)]) -> dict[str, str]:
    """Report readiness only when the configured database accepts a probe."""

    try:
        db.execute(text("SELECT 1"))
    except SQLAlchemyError as exc:
        raise HTTPException(status_code=503, detail="database_unavailable") from exc
    return {"status": "ok", "database": "ok"}

@app.get("/api/v1/system/info", tags=["system"], response_model=dict[str, str])
def system_info() -> dict[str, str]:
    return {
        "product": "FSP Talent Platform",
        "state": "bootstrap",
        "message": "Autonomous development workspace is ready.",
    }


@app.post(
    "/api/v1/assessments/attempts",
    tags=["assessments"],
    responses={
        409: {"model": ErrorResponse, "description": "Assessment cannot be created"},
        422: {"model": ErrorResponse, "description": "Invalid request"},
    },
)
def create_assessment_attempt(request: CreateAttemptRequest) -> dict[str, Any]:
    try:
        attempt = assessment_service.create_attempt(request.candidate_id, request.specialization, request.declared_grade)
    except AssessmentError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return public_attempt(attempt)


@app.get(
    "/api/v1/assessments/attempts/{attempt_id}",
    tags=["assessments"],
    responses={
        404: {"model": ErrorResponse, "description": "Assessment attempt not found"},
        422: {"model": ErrorResponse, "description": "Invalid request"},
    },
)
def get_assessment_attempt(attempt_id: str) -> dict[str, Any]:
    try:
        return public_attempt(assessment_service.get(attempt_id))
    except AssessmentError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.post(
    "/api/v1/assessments/attempts/{attempt_id}/submit",
    tags=["assessments"],
    responses={
        404: {"model": ErrorResponse, "description": "Assessment attempt not found"},
        409: {"model": ErrorResponse, "description": "Assessment cannot be submitted"},
        422: {"model": ErrorResponse, "description": "Invalid request"},
    },
)
def submit_assessment_attempt(attempt_id: str, request: SubmitAttemptRequest) -> dict[str, Any]:
    try:
        attempt = assessment_service.submit(attempt_id, request.answers, request.followups, request.telemetry)
    except AssessmentError as exc:
        status = 404 if str(exc) == "attempt_not_found" else 409
        raise HTTPException(status_code=status, detail=str(exc)) from exc
    return public_attempt(attempt)
