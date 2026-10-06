import re
from datetime import date, datetime
from typing import Annotated, Any, Literal
from uuid import uuid4

from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.cors import CORSMiddleware

from .assessments import AssessmentError, AssessmentService, public_attempt
from .auth import (
    Principal,
    Role,
    bind_role,
    build_verifier,
    is_allowed_registration_email,
    resolve_principal,
    sync_identity,
)
from .candidates import get_profile, update_profile
from .config import get_settings
from .db import get_db_session
from .errors import ErrorResponse, error_response, normalize_http_error
from .privacy import PrivacyState, get_privacy, request_export, update_privacy
from .protected_candidate import MinorState, get_protected_profile, update_protected_profile

app = FastAPI(
    title="FSP Talent Platform API",
    version="0.1.0",
    description="Bootstrap API. Codex implements the target domain from the requirements matrix.",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=get_settings().cors_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "PATCH", "OPTIONS"],
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
    identity_id: str | None
    keycloak_sub: str
    email: str
    role: str
    email_verified: bool
    onboarding_required: bool = False


class RoleOnboardingRequest(BaseModel):
    role: Literal["candidate", "employer"]


class CandidatePrivacyUpdateRequest(BaseModel):
    processing_consent: bool | None = None
    publication_consent: bool | None = None
    discoverable: bool | None = None


class CandidateExperience(BaseModel):
    model_config = ConfigDict(extra="forbid")

    role: str = Field(min_length=1, max_length=120)
    company: str = Field(min_length=1, max_length=120)
    started_on: str = Field(pattern=r"^\d{4}-(0[1-9]|1[0-2])$")
    ended_on: str | None = Field(default=None, pattern=r"^(present|\d{4}-(0[1-9]|1[0-2]))$")
    description: str | None = Field(default=None, max_length=1000)
    technologies: list[Annotated[str, Field(min_length=1, max_length=80)]] = Field(
        default_factory=list, max_length=20
    )


class CandidateWorkPreferences(BaseModel):
    model_config = ConfigDict(extra="forbid")

    work_mode: Literal["office", "hybrid", "remote"] | None = None
    employment_type: Literal["full_time", "part_time", "project"] | None = None
    availability: str | None = Field(default=None, max_length=120)


class CandidateProfileUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    display_name: str | None = Field(default=None, max_length=120)
    headline: str | None = Field(default=None, max_length=160)
    location: str | None = Field(default=None, max_length=120)
    summary: str | None = Field(default=None, max_length=2000)
    experience: list[CandidateExperience] | None = Field(default=None, max_length=12)
    skills: list[Annotated[str, Field(min_length=1, max_length=80)]] | None = Field(
        default=None, max_length=30
    )
    work_preferences: CandidateWorkPreferences | None = None


class CandidateProfileResponse(BaseModel):
    id: str
    display_name: str | None
    headline: str | None
    location: str | None
    summary: str | None
    experience: list[CandidateExperience]
    skills: list[str]
    work_preferences: CandidateWorkPreferences
    updated_at: datetime


class ProtectedCandidateProfileUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    date_of_birth: date | None = None


class ProtectedCandidateProfileResponse(BaseModel):
    date_of_birth: date | None
    minor_state: MinorState
    adult_age_years: int


class CandidatePrivacyResponse(BaseModel):
    processing_consent: bool
    processing_consent_version: str | None
    processing_consent_at: datetime | None
    publication_consent: bool
    publication_consent_version: str | None
    publication_consent_at: datetime | None
    discoverable: bool


class PrivacyRequestResponse(BaseModel):
    request_id: str
    request_type: Literal["export"]
    status: Literal["requested"]


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


def resolve_current_principal(
    principal: Annotated[Principal, Depends(get_current_principal)],
    db: Annotated[Session, Depends(get_db_session)],
) -> Principal:
    return resolve_principal(db, principal)


def candidate_principal(
    principal: Annotated[Principal, Depends(resolve_current_principal)],
) -> Principal:
    if principal.role != Role.CANDIDATE:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="role_required")
    return principal


def employer_principal(
    principal: Annotated[Principal, Depends(resolve_current_principal)],
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
    principal: Annotated[Principal, Depends(resolve_current_principal)],
    db: Annotated[Session, Depends(get_db_session)],
) -> AuthSessionResponse:
    if principal.role is None:
        return AuthSessionResponse(
            identity_id=None,
            keycloak_sub=principal.subject,
            email=principal.email,
            role="pending",
            email_verified=principal.email_verified,
            onboarding_required=True,
        )
    identity = sync_identity(db, principal)
    return AuthSessionResponse(
        identity_id=identity["id"],
        keycloak_sub=identity["keycloak_sub"],
        email=identity["email"],
        role=identity["role"],
        email_verified=identity["email_verified"],
        onboarding_required=False,
    )


@app.post(
    "/api/v1/auth/onboarding/role",
    tags=["auth"],
    response_model=AuthSessionResponse,
    responses={
        409: {"model": ErrorResponse, "description": "Role is already bound"},
        422: {"model": ErrorResponse, "description": "Unsupported onboarding role"},
    },
)
def complete_role_onboarding(
    request: RoleOnboardingRequest,
    principal: Annotated[Principal, Depends(get_current_principal)],
    db: Annotated[Session, Depends(get_db_session)],
) -> AuthSessionResponse:
    identity = bind_role(db, principal, Role(request.role))
    return AuthSessionResponse(
        identity_id=identity["id"],
        keycloak_sub=identity["keycloak_sub"],
        email=identity["email"],
        role=identity["role"],
        email_verified=identity["email_verified"],
        onboarding_required=False,
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
        onboarding_required=False,
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


def _privacy_response(state: PrivacyState) -> CandidatePrivacyResponse:
    return CandidatePrivacyResponse(
        processing_consent=state.processing_consent,
        processing_consent_version=state.processing_consent_version,
        processing_consent_at=state.processing_consent_at,
        publication_consent=state.publication_consent,
        publication_consent_version=state.publication_consent_version,
        publication_consent_at=state.publication_consent_at,
        discoverable=state.discoverable,
    )


@app.get(
    "/api/v1/candidate/privacy",
    tags=["candidate privacy"],
    response_model=CandidatePrivacyResponse,
    responses={403: {"model": ErrorResponse, "description": "Candidate role required"}},
)
def candidate_privacy(
    principal: Annotated[Principal, Depends(candidate_principal)],
    db: Annotated[Session, Depends(get_db_session)],
) -> CandidatePrivacyResponse:
    return _privacy_response(get_privacy(db, principal))


@app.patch(
    "/api/v1/candidate/privacy",
    tags=["candidate privacy"],
    response_model=CandidatePrivacyResponse,
    responses={
        403: {"model": ErrorResponse, "description": "Candidate role required"},
        409: {"model": ErrorResponse, "description": "Consent dependency is not satisfied"},
    },
)
def update_candidate_privacy(
    request: CandidatePrivacyUpdateRequest,
    principal: Annotated[Principal, Depends(candidate_principal)],
    db: Annotated[Session, Depends(get_db_session)],
) -> CandidatePrivacyResponse:
    if request.processing_consent is None and request.publication_consent is None and request.discoverable is None:
        raise HTTPException(status_code=422, detail="privacy_update_required")
    state = update_privacy(
        db,
        principal,
        get_settings(),
        processing_consent=request.processing_consent,
        publication_consent=request.publication_consent,
        discoverable=request.discoverable,
    )
    return _privacy_response(state)


@app.post(
    "/api/v1/candidate/privacy/export",
    tags=["candidate privacy"],
    response_model=PrivacyRequestResponse,
    status_code=202,
    responses={403: {"model": ErrorResponse, "description": "Candidate role required"}},
)
def request_candidate_export(
    principal: Annotated[Principal, Depends(candidate_principal)],
    db: Annotated[Session, Depends(get_db_session)],
) -> PrivacyRequestResponse:
    request_id, request_status = request_export(db, principal)
    return PrivacyRequestResponse(request_id=request_id, request_type="export", status=request_status)


@app.get(
    "/api/v1/candidate/profile",
    tags=["candidate profile"],
    response_model=CandidateProfileResponse,
    responses={403: {"model": ErrorResponse, "description": "Candidate role required"}},
)
def candidate_profile(
    principal: Annotated[Principal, Depends(candidate_principal)],
    db: Annotated[Session, Depends(get_db_session)],
) -> CandidateProfileResponse:
    return CandidateProfileResponse.model_validate(get_profile(db, principal))


@app.patch(
    "/api/v1/candidate/profile",
    tags=["candidate profile"],
    response_model=CandidateProfileResponse,
    responses={
        403: {"model": ErrorResponse, "description": "Candidate role required"},
        409: {"model": ErrorResponse, "description": "Processing consent is required"},
    },
)
def update_candidate_profile(
    request: CandidateProfileUpdateRequest,
    principal: Annotated[Principal, Depends(candidate_principal)],
    db: Annotated[Session, Depends(get_db_session)],
) -> CandidateProfileResponse:
    changes = request.model_dump(exclude_unset=True)
    if not changes:
        raise HTTPException(status_code=422, detail="profile_update_required")
    return CandidateProfileResponse.model_validate(update_profile(db, principal, changes))


@app.get(
    "/api/v1/candidate/protected-profile",
    tags=["candidate privacy"],
    response_model=ProtectedCandidateProfileResponse,
    responses={403: {"model": ErrorResponse, "description": "Candidate role required"}},
)
def candidate_protected_profile(
    principal: Annotated[Principal, Depends(candidate_principal)],
    db: Annotated[Session, Depends(get_db_session)],
) -> ProtectedCandidateProfileResponse:
    return ProtectedCandidateProfileResponse.model_validate(
        get_protected_profile(db, principal, get_settings())
    )


@app.patch(
    "/api/v1/candidate/protected-profile",
    tags=["candidate privacy"],
    response_model=ProtectedCandidateProfileResponse,
    responses={
        403: {"model": ErrorResponse, "description": "Candidate role required"},
        409: {"model": ErrorResponse, "description": "Processing consent is required"},
        422: {"model": ErrorResponse, "description": "Date of birth is invalid"},
    },
)
def update_candidate_protected_profile(
    request: ProtectedCandidateProfileUpdateRequest,
    principal: Annotated[Principal, Depends(candidate_principal)],
    db: Annotated[Session, Depends(get_db_session)],
) -> ProtectedCandidateProfileResponse:
    if "date_of_birth" not in request.model_fields_set:
        raise HTTPException(status_code=422, detail="protected_profile_update_required")
    return ProtectedCandidateProfileResponse.model_validate(
        update_protected_profile(
            db,
            principal,
            get_settings(),
            date_of_birth=request.date_of_birth,
        )
    )


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
