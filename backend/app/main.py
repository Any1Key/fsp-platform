import re
from typing import Annotated, Any, Literal
from uuid import uuid4

from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.cors import CORSMiddleware

from .assessments import AssessmentError, AssessmentService, public_attempt
from .auth import Principal, Role, build_verifier, is_allowed_registration_email, sync_identity
from .config import get_settings
from .db import get_db_session
from .errors import ErrorResponse, error_response, normalize_http_error

app = FastAPI(
    title="FSP Talent Platform API",
    version="0.1.0",
    description="Bootstrap API. Codex implements the target domain from the requirements matrix.",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=get_settings().cors_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
)

REQUEST_ID_PATTERN = re.compile(r"^[A-Za-z0-9._-]{1,128}$")

assessment_service = AssessmentService()
auth_verifier = build_verifier(get_settings())
bearer_scheme = HTTPBearer(auto_error=False)


class CreateAttemptRequest(BaseModel):
    candidate_id: str = Field(min_length=1, max_length=128)
    specialization: str
    declared_grade: str


class SubmitAttemptRequest(BaseModel):
    answers: dict[str, int]
    followups: dict[str, str] = Field(default_factory=dict)
    telemetry: dict[str, Any] = Field(default_factory=dict)


class RegistrationCheckRequest(BaseModel):
    email: str = Field(min_length=3, max_length=320)
    role: Literal["candidate", "employer"]


class RegistrationCheckResponse(BaseModel):
    allowed: bool
    email: str
    role: Literal["candidate", "employer"]


class AuthSessionResponse(BaseModel):
    identity_id: str
    keycloak_sub: str
    email: str
    role: str
    email_verified: bool


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
    return error_response(
        request,
        status_code=exc.status_code,
        code=code,
        message=message,
        headers=exc.headers,
    )


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


def get_current_principal(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
) -> Principal:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="authorization_header_required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return auth_verifier.verify(credentials.credentials)


def candidate_principal(
    principal: Annotated[Principal, Depends(get_current_principal)],
) -> Principal:
    if principal.role != Role.CANDIDATE:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="role_required")
    return principal


def employer_principal(
    principal: Annotated[Principal, Depends(get_current_principal)],
) -> Principal:
    if principal.role != Role.EMPLOYER:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="role_required")
    return principal


@app.post(
    "/api/v1/auth/registration/check",
    tags=["auth"],
    response_model=RegistrationCheckResponse,
    responses={403: {"model": ErrorResponse, "description": "Email domain is not allowed"}},
)
def check_registration(request: RegistrationCheckRequest) -> RegistrationCheckResponse:
    """Preflight the same domain policy applied at the authenticated boundary."""

    normalized_email = request.email.strip().lower()
    if not is_allowed_registration_email(normalized_email):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="registration_domain_not_allowed")
    return RegistrationCheckResponse(allowed=True, email=normalized_email, role=request.role)


@app.get(
    "/api/v1/auth/me",
    tags=["auth"],
    response_model=AuthSessionResponse,
    responses={401: {"model": ErrorResponse, "description": "Authentication required"}},
)
def auth_me(
    principal: Annotated[Principal, Depends(get_current_principal)],
    db: Annotated[Session, Depends(get_db_session)],
) -> AuthSessionResponse:
    identity = sync_identity(db, principal)
    return AuthSessionResponse(
        identity_id=identity["id"],
        keycloak_sub=identity["keycloak_sub"],
        email=identity["email"],
        role=identity["role"],
        email_verified=identity["email_verified"],
    )


def _role_context(
    principal: Principal,
    db: Session,
) -> AuthSessionResponse:
    identity = sync_identity(db, principal)
    return AuthSessionResponse(
        identity_id=identity["id"],
        keycloak_sub=identity["keycloak_sub"],
        email=identity["email"],
        role=identity["role"],
        email_verified=identity["email_verified"],
    )


@app.get(
    "/api/v1/candidate/context",
    tags=["auth"],
    response_model=AuthSessionResponse,
    responses={403: {"model": ErrorResponse, "description": "Candidate role required"}},
)
def candidate_context(
    principal: Annotated[Principal, Depends(candidate_principal)],
    db: Annotated[Session, Depends(get_db_session)],
) -> AuthSessionResponse:
    return _role_context(principal, db)


@app.get(
    "/api/v1/employer/context",
    tags=["auth"],
    response_model=AuthSessionResponse,
    responses={403: {"model": ErrorResponse, "description": "Employer role required"}},
)
def employer_context(
    principal: Annotated[Principal, Depends(employer_principal)],
    db: Annotated[Session, Depends(get_db_session)],
) -> AuthSessionResponse:
    return _role_context(principal, db)


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
