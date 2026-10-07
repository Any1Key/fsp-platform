import re
from datetime import date, datetime, timedelta
from typing import Annotated, Any, Literal
from uuid import uuid4

from fastapi import Depends, FastAPI, File, HTTPException, Query, Request, UploadFile, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, Response
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.cors import CORSMiddleware

from .assessments import (
    RETEST_COOLDOWN_DAYS,
    AssessmentError,
    AssessmentService,
    public_history_item,
)
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
from .chat import (
    exchange_contact,
    get_conversation,
    list_conversations,
    mark_conversation_read,
    report_conversation,
    send_message,
)
from .companies import get_company, update_company
from .config import get_settings
from .db import get_db_session
from .discovery import RadarFilters, get_talent_radar
from .employer_evaluations import list_employer_assignments, save_employer_evaluation
from .employer_tasks import create_task, create_version, list_tasks, publish_task, update_draft
from .errors import ErrorResponse, error_response, normalize_http_error
from .fsp import (
    SyntheticFspRegistryAdapter,
    get_fsp,
    get_fsp_identity_bridge,
    link_fsp,
    unlink_fsp,
)
from .hiring_needs import create_hiring_need, get_hiring_need, update_hiring_need
from .invitations import (
    create_invitation,
    get_invitation_for_employer,
    list_candidate_invitations,
    list_employer_invitations,
    respond_to_invitation,
)
from .local_ai import LocalAiPort, build_local_ai_port, context_from_hiring_need
from .minor_consent import get_document_status, upload_document
from .pipelines import get_hiring_pipeline, update_hiring_pipeline
from .privacy import PrivacyState, get_privacy, request_export, update_privacy
from .profile_pdf import render_profile_pdf
from .protected_candidate import MinorState, get_protected_profile, update_protected_profile
from .resume import get_resume, review_resume, upload_resume
from .task_assignments import list_candidate_assignments, submit_candidate_assignment
from .taxonomy import list_taxonomy

app = FastAPI(
    title="FSP Talent Platform API",
    version="0.1.0",
    description="Bootstrap API. Codex implements the target domain from the requirements matrix.",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=get_settings().cors_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "PATCH", "PUT", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
)

REQUEST_ID_PATTERN = re.compile(r"^[A-Za-z0-9._-]{1,128}$")

assessment_service = AssessmentService(
    canonical_exposure_window=timedelta(days=get_settings().canonical_exposure_window_days)
)
fsp_registry = SyntheticFspRegistryAdapter()
local_ai_port: LocalAiPort = build_local_ai_port()
auth_verifier = build_verifier(get_settings())
bearer_scheme = HTTPBearer(auto_error=False)


class CreateAttemptRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

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


class CompanyProfileUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, max_length=160)
    description: str | None = Field(default=None, max_length=4000)
    industry: str | None = Field(default=None, max_length=120)
    website: str | None = Field(default=None, max_length=255, pattern=r"^https?://[^\s]+$")
    location: str | None = Field(default=None, max_length=120)
    public_contact_method: str | None = Field(default=None, max_length=160)


class CompanyProfileResponse(BaseModel):
    id: str
    name: str | None
    description: str | None
    industry: str | None
    website: str | None
    location: str | None
    public_contact_method: str | None
    created_at: datetime
    updated_at: datetime


class CreateInvitationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    candidate_profile_id: str = Field(min_length=1, max_length=36)
    salary_min_rub: int = Field(gt=0)
    salary_max_rub: int = Field(gt=0)
    offer_description: str = Field(min_length=1, max_length=4000)


class InvitationCompanyResponse(BaseModel):
    id: str
    name: str
    contact_method: str


class InvitationCandidateResponse(BaseModel):
    id: str
    display_name: str


class PipelineStagePreviewResponse(BaseModel):
    stage_type: Literal[
        "platform_review",
        "employer_task",
        "questionnaire",
        "portfolio_review",
        "interview",
        "custom",
        "final_decision",
    ]
    title: str
    required: bool
    estimated_minutes: int


class InvitationResponse(BaseModel):
    id: str
    status: Literal["pending", "accepted", "declined"]
    salary_min_rub: int
    salary_max_rub: int
    offer_description: str
    company: InvitationCompanyResponse
    candidate: InvitationCandidateResponse
    created_at: datetime
    updated_at: datetime
    responded_at: datetime | None
    matched_at: datetime | None
    contact_unlocked_at: datetime | None
    match_id: str | None
    pipeline_stages: list[PipelineStagePreviewResponse]


class InvitationActionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    action: Literal["accepted", "declined"]


class ChatMessageRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    body: str = Field(min_length=1, max_length=4000)


class ChatMessageResponse(BaseModel):
    id: str
    sender_is_current: bool
    body: str
    created_at: datetime
    read_at: datetime | None


class ChatContactRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    contact_type: Literal["email", "phone", "telegram", "other"]
    contact_value: str = Field(min_length=1, max_length=160)


class ChatContactResponse(BaseModel):
    id: str
    is_current: bool
    contact_type: Literal["email", "phone", "telegram", "other"]
    contact_value: str
    created_at: datetime


class ChatReportRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reason: Literal["spam", "harassment", "inappropriate", "other"]
    details: str | None = Field(default=None, max_length=500)


class ChatReportResponse(BaseModel):
    id: str
    status: Literal["open"]


class ChatConversationSummaryResponse(BaseModel):
    id: str
    match_id: str
    participant_label: str
    created_at: datetime
    last_message_at: datetime | None
    last_message_preview: str | None
    unread_count: int


class ChatConversationResponse(BaseModel):
    id: str
    match_id: str
    participant_label: str
    created_at: datetime
    last_message_at: datetime | None
    unread_count: int
    messages: list[ChatMessageResponse]
    contacts: list[ChatContactResponse]


class ChatReadResponse(BaseModel):
    conversation_id: str
    marked_count: int
    unread_count: int


class HiringNeedSkillResponse(BaseModel):
    slug: str
    name: str


class HiringNeedCategoryResponse(BaseModel):
    slug: str
    name: str


class HiringNeedRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    team: str | None = Field(default=None, max_length=160)
    role: str | None = Field(default=None, max_length=160)
    specialization: str | None = Field(default=None, max_length=100)
    grade: str | None = Field(default=None, max_length=50)
    required_skills: list[Annotated[str, Field(min_length=1, max_length=100)]] | None = Field(
        default=None, max_length=20
    )
    preferred_skills: list[Annotated[str, Field(min_length=1, max_length=100)]] | None = Field(
        default=None, max_length=20
    )


class HiringNeedResponse(BaseModel):
    id: str
    team: str
    role: str
    specialization: HiringNeedCategoryResponse
    grade: HiringNeedCategoryResponse
    required_skills: list[HiringNeedSkillResponse]
    preferred_skills: list[HiringNeedSkillResponse]
    created_at: datetime
    updated_at: datetime


PipelineStageType = Literal[
    "platform_review",
    "employer_task",
    "questionnaire",
    "portfolio_review",
    "interview",
    "custom",
    "final_decision",
]


class PipelineStageRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    stage_type: PipelineStageType
    title: str = Field(min_length=1, max_length=120)
    required: bool = True
    estimated_minutes: int = Field(ge=5, le=480)


class PipelineStageResponse(PipelineStageRequest):
    id: str
    position: int


class HiringPipelineRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    stages: list[PipelineStageRequest] = Field(min_length=2, max_length=12)


class HiringPipelineResponse(BaseModel):
    id: str
    hiring_need_id: str
    created_at: datetime
    updated_at: datetime
    stages: list[PipelineStageResponse]


class EmployerTaskRubricDimensionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=120)
    points: int = Field(gt=0, le=1000)
    description: str | None = Field(default=None, max_length=500)


class EmployerTaskContentRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1, max_length=160)
    instructions: str = Field(min_length=1, max_length=12000)
    target_skills: list[Annotated[str, Field(min_length=1, max_length=100)]] = Field(
        min_length=1, max_length=20
    )
    expected_grade: Literal["junior", "middle", "senior"]
    estimated_minutes: int = Field(ge=5, le=480)
    deadline_hours: int = Field(ge=1, le=720)
    rubric: list[EmployerTaskRubricDimensionRequest] = Field(min_length=1, max_length=12)


class CreateEmployerTaskRequest(EmployerTaskContentRequest):
    pipeline_stage_id: str = Field(min_length=1, max_length=36)


class EmployerTaskVersionSummaryResponse(BaseModel):
    id: str
    version_number: int
    status: Literal["draft", "published", "retired"]
    created_at: datetime
    published_at: datetime | None


class EmployerTaskVersionResponse(EmployerTaskVersionSummaryResponse, EmployerTaskContentRequest):
    pass


class EmployerTaskResponse(BaseModel):
    id: str
    hiring_need_id: str
    pipeline_stage_id: str | None
    status: Literal["draft", "published", "retired"]
    created_at: datetime
    updated_at: datetime
    current_version: EmployerTaskVersionResponse
    versions: list[EmployerTaskVersionSummaryResponse]


class LocalAiDraftSuggestionResponse(BaseModel):
    status: Literal["disabled", "completed", "failed"]
    source: Literal["disabled", "local"]
    reason: str | None
    draft: dict[str, Any] | None


class TaskSubmissionResponse(BaseModel):
    id: str
    attempt_number: int
    response_text: str
    submitted_at: datetime


class CandidateTaskResponse(BaseModel):
    version_number: int
    title: str
    instructions: str
    target_skills: list[str]
    expected_grade: Literal["junior", "middle", "senior"]
    estimated_minutes: int


class CandidateEvaluationResponse(BaseModel):
    score: int
    feedback: str | None
    released_at: datetime


class CandidateTaskAssignmentResponse(BaseModel):
    id: str
    match_id: str
    task_id: str
    task_version_id: str
    pipeline_stage_id: str
    stage_title: str
    status: Literal["assigned", "submitted", "expired"]
    assigned_at: datetime
    due_at: datetime
    submitted_at: datetime | None
    task: CandidateTaskResponse
    submissions: list[TaskSubmissionResponse]
    evaluation: CandidateEvaluationResponse | None


class CandidateTaskSubmissionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    response_text: str = Field(min_length=1, max_length=20000)


class EmployerEvaluationRubricScoreRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=120)
    points_awarded: int = Field(ge=0, le=1000)


class EmployerEvaluationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    rubric_scores: list[EmployerEvaluationRubricScoreRequest] = Field(min_length=1, max_length=12)
    feedback: str | None = Field(default=None, max_length=5000)
    release_to_candidate: bool = False


class EmployerEvaluationResponse(BaseModel):
    id: str
    assignment_id: str
    score: int
    rubric_scores: list[dict[str, Any]]
    feedback: str | None
    status: Literal["draft", "released"]
    created_at: datetime
    updated_at: datetime
    released_at: datetime | None


class EmployerTaskAssignmentTaskResponse(BaseModel):
    version_number: int
    title: str
    instructions: str
    target_skills: list[str]
    expected_grade: Literal["junior", "middle", "senior"]
    estimated_minutes: int
    rubric: list[dict[str, Any]]


class EmployerTaskAssignmentResponse(BaseModel):
    id: str
    match_id: str
    candidate_profile_id: str
    candidate_display_name: str
    task_id: str
    task_version_id: str
    pipeline_stage_id: str
    stage_title: str
    status: Literal["assigned", "submitted", "expired"]
    assigned_at: datetime
    due_at: datetime
    submitted_at: datetime | None
    task: EmployerTaskAssignmentTaskResponse
    submissions: list[TaskSubmissionResponse]
    evaluation: EmployerEvaluationResponse | None


class CandidateDashboardProfileResponse(BaseModel):
    display_name: str | None
    headline: str | None


class CandidateDashboardAttemptResponse(BaseModel):
    attempt_id: str
    specialization: str
    declared_grade: str
    status: Literal["in_progress", "submitted"]
    score: float | None
    grade_state: Literal["verified", "not_confirmed"] | None
    created_at: datetime


class CandidateCurrentAssessmentResponse(BaseModel):
    attempt_id: str
    specialization: str
    declared_grade: str
    verified_grade: str | None
    grade_state: Literal["verified", "not_confirmed"]
    score: float
    assessed_at: datetime


class CandidateDashboardResponse(BaseModel):
    profile: CandidateDashboardProfileResponse
    current_assessment: CandidateCurrentAssessmentResponse | None
    retest_available_at: datetime | None
    attempt_history: list[CandidateDashboardAttemptResponse]


class TaxonomySkillResponse(BaseModel):
    id: str
    slug: str
    name: str
    is_core: bool


class TaxonomySpecializationResponse(BaseModel):
    id: str
    slug: str
    name: str
    skills: list[TaxonomySkillResponse]


class TaxonomyGradeResponse(BaseModel):
    id: str
    slug: str
    name: str
    rank: int


class TaxonomyCategoryResponse(BaseModel):
    key: str
    specialization_slug: str
    grade_slug: str
    label: str


class TaxonomyResponse(BaseModel):
    specializations: list[TaxonomySpecializationResponse]
    grades: list[TaxonomyGradeResponse]
    categories: list[TaxonomyCategoryResponse]


class ProtectedCandidateProfileUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    date_of_birth: date | None = None


class ProtectedCandidateProfileResponse(BaseModel):
    date_of_birth: date | None
    minor_state: MinorState
    adult_age_years: int


class MinorConsentDocumentMetadata(BaseModel):
    id: str
    policy_version: str
    original_filename: str
    content_type: Literal["application/pdf"]
    size_bytes: int
    status: Literal["submitted", "approved", "rejected", "replaced", "withdrawn"]
    uploaded_at: datetime


class MinorConsentDocumentResponse(BaseModel):
    minor_state: MinorState
    required: bool
    policy_version: str
    document: MinorConsentDocumentMetadata | None


class ResumeDocumentMetadata(BaseModel):
    id: str
    original_filename: str
    content_type: Literal["application/pdf"]
    size_bytes: int
    status: Literal["uploaded"]
    uploaded_at: datetime


class ResumeExtractionResponse(BaseModel):
    id: str
    status: Literal["needs_review", "accepted", "rejected", "unsupported"]
    parser_version: str
    text_available: bool
    fields: dict[str, Any]
    extracted_at: datetime
    reviewed_at: datetime | None


class ResumeDocumentResponse(BaseModel):
    document: ResumeDocumentMetadata | None
    extraction: ResumeExtractionResponse | None


class ResumeReviewRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    accepted: bool
    display_name: str | None = Field(default=None, max_length=120)
    headline: str | None = Field(default=None, max_length=160)
    summary: str | None = Field(default=None, max_length=2000)
    skills: list[Annotated[str, Field(min_length=1, max_length=80)]] | None = Field(
        default=None, max_length=30
    )
    experience: list[CandidateExperience] | None = Field(default=None, max_length=12)


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


class FspLinkRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    fsp_id: str = Field(min_length=3, max_length=120)


class FspAchievementResponse(BaseModel):
    id: str
    event_name: str
    event_date: date
    discipline: str
    level: str
    achievement_type: str
    placement: str | None
    result: str | None
    verification: str
    mapping_version: str
    mapped_specialization: str | None
    mapped_skills: list[str]
    result_score: int = Field(ge=0, le=100)
    result_label: str
    recency_score: int = Field(ge=0, le=100)
    recency_label: str


class CandidateFspResponse(BaseModel):
    status: Literal["not_linked", "linked"]
    provider: str | None
    participant_id: str | None
    linked_at: datetime | None
    updated_at: datetime | None
    history_status: Literal["no_history", "has_history"]
    achievements: list[FspAchievementResponse]


class FspKeycloakIdentityResponse(BaseModel):
    provider: Literal["keycloak"]
    issuer: str
    subject_fingerprint: str = Field(pattern=r"^[0-9a-f]{16}$")


class FspBridgeStateResponse(BaseModel):
    provider: str | None
    participant_id: str | None
    status: Literal["not_linked", "linked"]
    history_status: Literal["no_history", "has_history"]


class FspIdentityBridgeResponse(BaseModel):
    bridge_version: str
    binding_mode: Literal["explicit_candidate_link"]
    keycloak: FspKeycloakIdentityResponse
    fsp: FspBridgeStateResponse
    registry_adapter: Literal["FspRegistryPort"]


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


@app.get(
    "/api/v1/taxonomy",
    tags=["taxonomy"],
    response_model=TaxonomyResponse,
    responses={500: {"model": ErrorResponse, "description": "Taxonomy unavailable"}},
)
def taxonomy(db: Annotated[Session, Depends(get_db_session)]) -> TaxonomyResponse:
    """Return the active, non-sensitive taxonomy catalog."""

    # The route is intentionally read-only and public. It is used to render
    # onboarding choices, while candidate results and profile data remain
    # protected by their own authenticated boundaries.
    return TaxonomyResponse.model_validate(list_taxonomy(db))


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


def chat_principal(
    principal: Annotated[Principal, Depends(resolve_current_principal)],
) -> Principal:
    if principal.role not in {Role.CANDIDATE, Role.EMPLOYER}:
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


@app.get(
    "/api/v1/employer/company",
    tags=["employer company"],
    response_model=CompanyProfileResponse,
    responses={403: {"model": ErrorResponse, "description": "Employer role required"}},
)
def employer_company(
    principal: Annotated[Principal, Depends(employer_principal)],
    db: Annotated[Session, Depends(get_db_session)],
) -> CompanyProfileResponse:
    """Return the authenticated employer's company profile only."""

    return CompanyProfileResponse.model_validate(get_company(db, principal))


@app.patch(
    "/api/v1/employer/company",
    tags=["employer company"],
    response_model=CompanyProfileResponse,
    responses={
        403: {"model": ErrorResponse, "description": "Employer role required"},
        422: {"model": ErrorResponse, "description": "Company profile is invalid"},
    },
)
def update_employer_company(
    request: CompanyProfileUpdateRequest,
    principal: Annotated[Principal, Depends(employer_principal)],
    db: Annotated[Session, Depends(get_db_session)],
) -> CompanyProfileResponse:
    changes = request.model_dump(exclude_unset=True)
    if not changes:
        raise HTTPException(status_code=422, detail="company_profile_update_required")
    return CompanyProfileResponse.model_validate(update_company(db, principal, changes))


@app.get(
    "/api/v1/employer/hiring-need",
    tags=["employer hiring need"],
    response_model=HiringNeedResponse | None,
    responses={403: {"model": ErrorResponse, "description": "Employer role required"}},
)
def employer_hiring_need(
    principal: Annotated[Principal, Depends(employer_principal)],
    db: Annotated[Session, Depends(get_db_session)],
) -> HiringNeedResponse | None:
    """Return the authenticated employer's current hiring need, if created."""

    need = get_hiring_need(db, principal)
    return HiringNeedResponse.model_validate(need) if need else None


@app.post(
    "/api/v1/employer/hiring-need",
    tags=["employer hiring need"],
    response_model=HiringNeedResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        403: {"model": ErrorResponse, "description": "Employer role required"},
        409: {"model": ErrorResponse, "description": "Hiring need already exists"},
        422: {"model": ErrorResponse, "description": "Hiring need is invalid"},
    },
)
def create_employer_hiring_need(
    request: HiringNeedRequest,
    principal: Annotated[Principal, Depends(employer_principal)],
    db: Annotated[Session, Depends(get_db_session)],
) -> HiringNeedResponse:
    payload = request.model_dump(exclude_unset=True)
    return HiringNeedResponse.model_validate(create_hiring_need(db, principal, payload))


@app.patch(
    "/api/v1/employer/hiring-need",
    tags=["employer hiring need"],
    response_model=HiringNeedResponse,
    responses={
        403: {"model": ErrorResponse, "description": "Employer role required"},
        404: {"model": ErrorResponse, "description": "Hiring need not found"},
        422: {"model": ErrorResponse, "description": "Hiring need is invalid"},
    },
)
def update_employer_hiring_need(
    request: HiringNeedRequest,
    principal: Annotated[Principal, Depends(employer_principal)],
    db: Annotated[Session, Depends(get_db_session)],
) -> HiringNeedResponse:
    payload = request.model_dump(exclude_unset=True)
    if not payload:
        raise HTTPException(status_code=422, detail="hiring_need_update_required")
    return HiringNeedResponse.model_validate(update_hiring_need(db, principal, payload))


@app.get(
    "/api/v1/employer/hiring-pipeline",
    tags=["employer hiring pipeline"],
    response_model=HiringPipelineResponse,
    responses={
        403: {"model": ErrorResponse, "description": "Employer role required"},
        404: {"model": ErrorResponse, "description": "Hiring need not found"},
    },
)
def employer_hiring_pipeline(
    principal: Annotated[Principal, Depends(employer_principal)],
    db: Annotated[Session, Depends(get_db_session)],
) -> HiringPipelineResponse:
    """Return the employer-owned ordered hiring pipeline."""

    return HiringPipelineResponse.model_validate(get_hiring_pipeline(db, principal))


@app.put(
    "/api/v1/employer/hiring-pipeline",
    tags=["employer hiring pipeline"],
    response_model=HiringPipelineResponse,
    responses={
        403: {"model": ErrorResponse, "description": "Employer role required"},
        404: {"model": ErrorResponse, "description": "Hiring need not found"},
        422: {"model": ErrorResponse, "description": "Pipeline stages are invalid"},
    },
)
def update_employer_hiring_pipeline(
    request: HiringPipelineRequest,
    principal: Annotated[Principal, Depends(employer_principal)],
    db: Annotated[Session, Depends(get_db_session)],
) -> HiringPipelineResponse:
    return HiringPipelineResponse.model_validate(
        update_hiring_pipeline(
            db,
            principal,
            [stage.model_dump() for stage in request.stages],
        )
    )


@app.get(
    "/api/v1/employer/tasks",
    tags=["employer tasks"],
    response_model=list[EmployerTaskResponse],
    responses={
        403: {"model": ErrorResponse, "description": "Employer role required"},
        404: {"model": ErrorResponse, "description": "Hiring need not found"},
    },
)
def employer_tasks(
    principal: Annotated[Principal, Depends(employer_principal)],
    db: Annotated[Session, Depends(get_db_session)],
) -> list[EmployerTaskResponse]:
    """Return task definitions owned by the current employer."""

    return [EmployerTaskResponse.model_validate(task) for task in list_tasks(db, principal)]


@app.post(
    "/api/v1/employer/tasks/draft-suggestion",
    tags=["employer tasks"],
    response_model=LocalAiDraftSuggestionResponse,
    responses={
        403: {"model": ErrorResponse, "description": "Employer role required"},
        404: {"model": ErrorResponse, "description": "Hiring need not found"},
    },
)
async def employer_task_draft_suggestion(
    principal: Annotated[Principal, Depends(employer_principal)],
    db: Annotated[Session, Depends(get_db_session)],
) -> LocalAiDraftSuggestionResponse:
    """Probe optional task assistance without persisting or blocking authoring."""

    need = get_hiring_need(db, principal)
    if need is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="hiring_need_not_found")
    result = await local_ai_port.propose_task_draft(context_from_hiring_need(need))
    return LocalAiDraftSuggestionResponse(
        status=result.status,
        source=result.source,
        reason=result.reason,
        draft=result.draft,
    )


@app.post(
    "/api/v1/employer/tasks",
    tags=["employer tasks"],
    response_model=EmployerTaskResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        403: {"model": ErrorResponse, "description": "Employer role required"},
        404: {"model": ErrorResponse, "description": "Hiring need not found"},
        422: {"model": ErrorResponse, "description": "Task definition is invalid"},
    },
)
def create_employer_task(
    request: CreateEmployerTaskRequest,
    principal: Annotated[Principal, Depends(employer_principal)],
    db: Annotated[Session, Depends(get_db_session)],
) -> EmployerTaskResponse:
    return EmployerTaskResponse.model_validate(
        create_task(
            db,
            principal,
            request.pipeline_stage_id,
            request.model_dump(exclude={"pipeline_stage_id"}),
        )
    )


@app.post(
    "/api/v1/employer/tasks/{task_id}/versions",
    tags=["employer tasks"],
    response_model=EmployerTaskResponse,
    responses={
        403: {"model": ErrorResponse, "description": "Employer role required"},
        404: {"model": ErrorResponse, "description": "Task not found"},
        409: {"model": ErrorResponse, "description": "A draft version already exists"},
        422: {"model": ErrorResponse, "description": "Task definition is invalid"},
    },
)
def create_employer_task_version(
    task_id: str,
    request: EmployerTaskContentRequest,
    principal: Annotated[Principal, Depends(employer_principal)],
    db: Annotated[Session, Depends(get_db_session)],
) -> EmployerTaskResponse:
    return EmployerTaskResponse.model_validate(
        create_version(db, principal, task_id, request.model_dump())
    )


@app.patch(
    "/api/v1/employer/tasks/{task_id}/draft",
    tags=["employer tasks"],
    response_model=EmployerTaskResponse,
    responses={
        403: {"model": ErrorResponse, "description": "Employer role required"},
        404: {"model": ErrorResponse, "description": "Task not found"},
        422: {"model": ErrorResponse, "description": "Task definition is invalid"},
    },
)
def update_employer_task_draft(
    task_id: str,
    request: EmployerTaskContentRequest,
    principal: Annotated[Principal, Depends(employer_principal)],
    db: Annotated[Session, Depends(get_db_session)],
) -> EmployerTaskResponse:
    return EmployerTaskResponse.model_validate(
        update_draft(db, principal, task_id, request.model_dump())
    )


@app.post(
    "/api/v1/employer/tasks/{task_id}/publish",
    tags=["employer tasks"],
    response_model=EmployerTaskResponse,
    responses={
        403: {"model": ErrorResponse, "description": "Employer role required"},
        404: {"model": ErrorResponse, "description": "Task not found"},
        409: {"model": ErrorResponse, "description": "A draft version is required"},
    },
)
def publish_employer_task(
    task_id: str,
    principal: Annotated[Principal, Depends(employer_principal)],
    db: Annotated[Session, Depends(get_db_session)],
) -> EmployerTaskResponse:
    return EmployerTaskResponse.model_validate(publish_task(db, principal, task_id))


@app.get(
    "/api/v1/employer/talent-radar",
    tags=["employer discovery"],
    response_model=dict[str, Any],
    responses={
        403: {"model": ErrorResponse, "description": "Employer role required"},
        409: {"model": ErrorResponse, "description": "A hiring need is required"},
        422: {"model": ErrorResponse, "description": "Talent Radar filter is invalid"},
    },
)
def employer_talent_radar(
    principal: Annotated[Principal, Depends(employer_principal)],
    db: Annotated[Session, Depends(get_db_session)],
    q: str | None = Query(default=None, max_length=120),
    specialization: str | None = Query(default=None, max_length=100),
    grade: str | None = Query(default=None, max_length=50),
    skill: str | None = Query(default=None, max_length=100),
    fsp: Literal["all", "with_history", "without_history"] = Query(default="all"),
    include_unconfirmed: bool = Query(default=True),
    limit: int = Query(default=30, ge=1, le=100),
) -> dict[str, Any]:
    """Return a consent-gated, explainable candidate discovery snapshot."""

    return get_talent_radar(
        db,
        principal,
        assessment_service,
        RadarFilters(
            query=(q or "").strip(),
            specialization=(specialization or "").strip() or None,
            grade=(grade or "").strip() or None,
            skill=(skill or "").strip() or None,
            fsp=fsp,
            include_unconfirmed=include_unconfirmed,
            limit=limit,
        ),
    )


@app.post(
    "/api/v1/employer/invitations",
    tags=["employer invitations"],
    response_model=InvitationResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        403: {"model": ErrorResponse, "description": "Employer role required"},
        404: {"model": ErrorResponse, "description": "Candidate is not available"},
        409: {"model": ErrorResponse, "description": "Pending invitation already exists"},
        422: {"model": ErrorResponse, "description": "Salary, offer, or company contact is invalid"},
    },
)
def create_employer_invitation(
    request: CreateInvitationRequest,
    principal: Annotated[Principal, Depends(employer_principal)],
    db: Annotated[Session, Depends(get_db_session)],
) -> InvitationResponse:
    return InvitationResponse.model_validate(
        create_invitation(
            db,
            principal,
            candidate_profile_id=request.candidate_profile_id,
            salary_min_rub=request.salary_min_rub,
            salary_max_rub=request.salary_max_rub,
            offer_description=request.offer_description,
            assessment_service=assessment_service,
        )
    )


@app.get(
    "/api/v1/employer/invitations",
    tags=["employer invitations"],
    response_model=list[InvitationResponse],
    responses={403: {"model": ErrorResponse, "description": "Employer role required"}},
)
def employer_invitations(
    principal: Annotated[Principal, Depends(employer_principal)],
    db: Annotated[Session, Depends(get_db_session)],
) -> list[InvitationResponse]:
    return [InvitationResponse.model_validate(item) for item in list_employer_invitations(db, principal)]


@app.get(
    "/api/v1/employer/invitations/{invitation_id}",
    tags=["employer invitations"],
    response_model=InvitationResponse,
    responses={
        403: {"model": ErrorResponse, "description": "Employer role required"},
        404: {"model": ErrorResponse, "description": "Invitation not found"},
    },
)
def employer_invitation(
    invitation_id: str,
    principal: Annotated[Principal, Depends(employer_principal)],
    db: Annotated[Session, Depends(get_db_session)],
) -> InvitationResponse:
    return InvitationResponse.model_validate(get_invitation_for_employer(db, principal, invitation_id))


@app.get(
    "/api/v1/candidate/invitations",
    tags=["candidate invitations"],
    response_model=list[InvitationResponse],
    responses={403: {"model": ErrorResponse, "description": "Candidate role required"}},
)
def candidate_invitations(
    principal: Annotated[Principal, Depends(candidate_principal)],
    db: Annotated[Session, Depends(get_db_session)],
) -> list[InvitationResponse]:
    return [InvitationResponse.model_validate(item) for item in list_candidate_invitations(db, principal)]


@app.post(
    "/api/v1/candidate/invitations/{invitation_id}/respond",
    tags=["candidate invitations"],
    response_model=InvitationResponse,
    responses={
        403: {"model": ErrorResponse, "description": "Candidate role required"},
        404: {"model": ErrorResponse, "description": "Invitation not found"},
        409: {"model": ErrorResponse, "description": "Invitation is no longer pending"},
    },
)
def respond_candidate_invitation(
    invitation_id: str,
    request: InvitationActionRequest,
    principal: Annotated[Principal, Depends(candidate_principal)],
    db: Annotated[Session, Depends(get_db_session)],
) -> InvitationResponse:
    return InvitationResponse.model_validate(
        respond_to_invitation(db, principal, invitation_id, request.action)
    )


@app.get(
    "/api/v1/candidate/task-assignments",
    tags=["candidate employer tasks"],
    response_model=list[CandidateTaskAssignmentResponse],
    responses={403: {"model": ErrorResponse, "description": "Candidate role required"}},
)
def candidate_task_assignments(
    principal: Annotated[Principal, Depends(candidate_principal)],
    db: Annotated[Session, Depends(get_db_session)],
) -> list[CandidateTaskAssignmentResponse]:
    """Return employer tasks assigned through accepted matches only."""

    return [
        CandidateTaskAssignmentResponse.model_validate(item)
        for item in list_candidate_assignments(db, principal)
    ]


@app.post(
    "/api/v1/candidate/task-assignments/{assignment_id}/submissions",
    tags=["candidate employer tasks"],
    response_model=CandidateTaskAssignmentResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        403: {"model": ErrorResponse, "description": "Candidate role required"},
        404: {"model": ErrorResponse, "description": "Assignment not found"},
        409: {"model": ErrorResponse, "description": "Assignment deadline has passed"},
        422: {"model": ErrorResponse, "description": "Submission is invalid"},
    },
)
def submit_candidate_task(
    assignment_id: str,
    request: CandidateTaskSubmissionRequest,
    principal: Annotated[Principal, Depends(candidate_principal)],
    db: Annotated[Session, Depends(get_db_session)],
) -> CandidateTaskAssignmentResponse:
    return CandidateTaskAssignmentResponse.model_validate(
        submit_candidate_assignment(db, principal, assignment_id, request.response_text)
    )


@app.get(
    "/api/v1/employer/task-assignments",
    tags=["employer tasks"],
    response_model=list[EmployerTaskAssignmentResponse],
    responses={403: {"model": ErrorResponse, "description": "Employer role required"}},
)
def employer_task_assignments(
    principal: Annotated[Principal, Depends(employer_principal)],
    db: Annotated[Session, Depends(get_db_session)],
) -> list[EmployerTaskAssignmentResponse]:
    """Return matched candidate task submissions owned by the current employer."""

    return [
        EmployerTaskAssignmentResponse.model_validate(item)
        for item in list_employer_assignments(db, principal)
    ]


@app.put(
    "/api/v1/employer/task-assignments/{assignment_id}/evaluation",
    tags=["employer tasks"],
    response_model=EmployerTaskAssignmentResponse,
    responses={
        403: {"model": ErrorResponse, "description": "Employer role required"},
        404: {"model": ErrorResponse, "description": "Assignment not found"},
        409: {"model": ErrorResponse, "description": "A candidate submission is required"},
        422: {"model": ErrorResponse, "description": "Evaluation rubric is invalid"},
    },
)
def evaluate_employer_task(
    assignment_id: str,
    request: EmployerEvaluationRequest,
    principal: Annotated[Principal, Depends(employer_principal)],
    db: Annotated[Session, Depends(get_db_session)],
) -> EmployerTaskAssignmentResponse:
    return EmployerTaskAssignmentResponse.model_validate(
        save_employer_evaluation(
            db,
            principal,
            assignment_id,
            [score.model_dump() for score in request.rubric_scores],
            request.feedback,
            request.release_to_candidate,
        )
    )


@app.get(
    "/api/v1/chat/conversations",
    tags=["chat"],
    response_model=list[ChatConversationSummaryResponse],
    responses={403: {"model": ErrorResponse, "description": "Candidate or employer role required"}},
)
def chat_conversations(
    principal: Annotated[Principal, Depends(chat_principal)],
    db: Annotated[Session, Depends(get_db_session)],
) -> list[ChatConversationSummaryResponse]:
    """List only conversations belonging to the authenticated matched party."""

    return [ChatConversationSummaryResponse.model_validate(item) for item in list_conversations(db, principal)]


@app.get(
    "/api/v1/chat/conversations/{conversation_id}",
    tags=["chat"],
    response_model=ChatConversationResponse,
    responses={
        403: {"model": ErrorResponse, "description": "Candidate or employer role required"},
        404: {"model": ErrorResponse, "description": "Conversation not found or not accessible"},
    },
)
def chat_conversation(
    conversation_id: str,
    principal: Annotated[Principal, Depends(chat_principal)],
    db: Annotated[Session, Depends(get_db_session)],
    limit: int = Query(default=100, ge=1, le=200),
) -> ChatConversationResponse:
    return ChatConversationResponse.model_validate(
        get_conversation(db, principal, conversation_id, limit=limit)
    )


@app.post(
    "/api/v1/chat/conversations/{conversation_id}/messages",
    tags=["chat"],
    response_model=ChatMessageResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        403: {"model": ErrorResponse, "description": "Candidate or employer role required"},
        404: {"model": ErrorResponse, "description": "Conversation not found or not accessible"},
        422: {"model": ErrorResponse, "description": "Message body is invalid"},
    },
)
def create_chat_message(
    conversation_id: str,
    request: ChatMessageRequest,
    principal: Annotated[Principal, Depends(chat_principal)],
    db: Annotated[Session, Depends(get_db_session)],
) -> ChatMessageResponse:
    return ChatMessageResponse.model_validate(send_message(db, principal, conversation_id, request.body))


@app.post(
    "/api/v1/chat/conversations/{conversation_id}/read",
    tags=["chat"],
    response_model=ChatReadResponse,
    responses={
        403: {"model": ErrorResponse, "description": "Candidate or employer role required"},
        404: {"model": ErrorResponse, "description": "Conversation not found or not accessible"},
    },
)
def read_chat_conversation(
    conversation_id: str,
    principal: Annotated[Principal, Depends(chat_principal)],
    db: Annotated[Session, Depends(get_db_session)],
) -> ChatReadResponse:
    return ChatReadResponse.model_validate(mark_conversation_read(db, principal, conversation_id))


@app.post(
    "/api/v1/chat/conversations/{conversation_id}/contacts",
    tags=["chat"],
    response_model=ChatContactResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        403: {"model": ErrorResponse, "description": "Candidate or employer role required"},
        404: {"model": ErrorResponse, "description": "Conversation not found or not accessible"},
        422: {"model": ErrorResponse, "description": "Contact value is invalid"},
    },
)
def share_chat_contact(
    conversation_id: str,
    request: ChatContactRequest,
    principal: Annotated[Principal, Depends(chat_principal)],
    db: Annotated[Session, Depends(get_db_session)],
) -> ChatContactResponse:
    return ChatContactResponse.model_validate(
        exchange_contact(
            db,
            principal,
            conversation_id,
            contact_type=request.contact_type,
            contact_value=request.contact_value,
        )
    )


@app.post(
    "/api/v1/chat/conversations/{conversation_id}/reports",
    tags=["chat"],
    response_model=ChatReportResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        403: {"model": ErrorResponse, "description": "Candidate or employer role required"},
        404: {"model": ErrorResponse, "description": "Conversation not found or not accessible"},
    },
)
def report_chat_conversation(
    conversation_id: str,
    request: ChatReportRequest,
    principal: Annotated[Principal, Depends(chat_principal)],
    db: Annotated[Session, Depends(get_db_session)],
) -> ChatReportResponse:
    return ChatReportResponse.model_validate(
        report_conversation(
            db,
            principal,
            conversation_id,
            reason=request.reason,
            details=request.details,
        )
    )


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


@app.get(
    "/api/v1/candidate/dashboard",
    tags=["candidate dashboard"],
    response_model=CandidateDashboardResponse,
    responses={403: {"model": ErrorResponse, "description": "Candidate role required"}},
)
def candidate_dashboard(
    principal: Annotated[Principal, Depends(candidate_principal)],
    db: Annotated[Session, Depends(get_db_session)],
) -> CandidateDashboardResponse:
    """Return the authenticated candidate's safe assessment overview."""

    profile = get_profile(db, principal)
    attempts = assessment_service.history_for(principal.subject)
    submitted_attempts = [attempt for attempt in attempts if attempt.submitted]
    latest_submitted = submitted_attempts[-1] if submitted_attempts else None
    latest_attempt = attempts[-1] if attempts else None

    current = None
    if latest_submitted is not None and latest_submitted.score is not None and latest_submitted.grade_state:
        current = CandidateCurrentAssessmentResponse(
            attempt_id=latest_submitted.attempt_id,
            specialization=latest_submitted.specialization,
            declared_grade=latest_submitted.declared_grade,
            verified_grade=(
                latest_submitted.declared_grade
                if latest_submitted.grade_state == "verified"
                else None
            ),
            grade_state=latest_submitted.grade_state,
            score=latest_submitted.score,
            assessed_at=latest_submitted.created_at,
        )

    return CandidateDashboardResponse(
        profile=CandidateDashboardProfileResponse(
            display_name=profile["display_name"],
            headline=profile["headline"],
        ),
        current_assessment=current,
        retest_available_at=(
            latest_attempt.created_at + timedelta(days=RETEST_COOLDOWN_DAYS)
            if latest_attempt is not None
            else None
        ),
        attempt_history=[
            CandidateDashboardAttemptResponse.model_validate(public_history_item(attempt))
            for attempt in reversed(attempts)
        ],
    )


@app.get(
    "/api/v1/candidate/profile/pdf",
    tags=["candidate profile"],
    response_class=Response,
    responses={
        200: {"content": {"application/pdf": {}}},
        403: {"model": ErrorResponse, "description": "Candidate role required"},
    },
)
def download_candidate_profile_pdf(
    principal: Annotated[Principal, Depends(candidate_principal)],
    db: Annotated[Session, Depends(get_db_session)],
) -> Response:
    """Generate a non-persisted standardized artifact from public profile fields."""

    profile = get_profile(db, principal)
    return Response(
        content=render_profile_pdf(profile),
        media_type="application/pdf",
        headers={"Content-Disposition": 'attachment; filename="fsp-standardized-profile.pdf"'},
    )


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
    "/api/v1/candidate/fsp",
    tags=["candidate FSP"],
    response_model=CandidateFspResponse,
    responses={403: {"model": ErrorResponse, "description": "Candidate role required"}},
)
def candidate_fsp(
    principal: Annotated[Principal, Depends(candidate_principal)],
    db: Annotated[Session, Depends(get_db_session)],
) -> CandidateFspResponse:
    """Return the candidate's FSP link and safe synthetic evidence snapshot."""

    return CandidateFspResponse.model_validate(get_fsp(db, principal))


@app.get(
    "/api/v1/candidate/fsp/integration",
    tags=["candidate FSP"],
    response_model=FspIdentityBridgeResponse,
    responses={403: {"model": ErrorResponse, "description": "Candidate role required"}},
)
def candidate_fsp_integration(
    principal: Annotated[Principal, Depends(candidate_principal)],
    db: Annotated[Session, Depends(get_db_session)],
) -> FspIdentityBridgeResponse:
    """Expose the safe Keycloak-to-FSP application-link demonstration contract."""

    return FspIdentityBridgeResponse.model_validate(
        get_fsp_identity_bridge(
            db,
            principal,
            keycloak_issuer=auth_verifier.settings.keycloak_issuer,
        )
    )


@app.post(
    "/api/v1/candidate/fsp-link",
    tags=["candidate FSP"],
    response_model=CandidateFspResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        403: {"model": ErrorResponse, "description": "Candidate role required"},
        404: {"model": ErrorResponse, "description": "FSP participant not found"},
        409: {"model": ErrorResponse, "description": "Processing consent is required"},
    },
)
def link_candidate_fsp(
    request: FspLinkRequest,
    principal: Annotated[Principal, Depends(candidate_principal)],
    db: Annotated[Session, Depends(get_db_session)],
) -> CandidateFspResponse:
    return CandidateFspResponse.model_validate(link_fsp(db, principal, request.fsp_id, fsp_registry))


@app.delete(
    "/api/v1/candidate/fsp-link",
    tags=["candidate FSP"],
    status_code=status.HTTP_204_NO_CONTENT,
    responses={403: {"model": ErrorResponse, "description": "Candidate role required"}},
)
def unlink_candidate_fsp(
    principal: Annotated[Principal, Depends(candidate_principal)],
    db: Annotated[Session, Depends(get_db_session)],
) -> Response:
    unlink_fsp(db, principal)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


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


@app.get(
    "/api/v1/candidate/minor-consent-document",
    tags=["candidate privacy"],
    response_model=MinorConsentDocumentResponse,
    responses={403: {"model": ErrorResponse, "description": "Candidate role required"}},
)
def candidate_minor_consent_document(
    principal: Annotated[Principal, Depends(candidate_principal)],
    db: Annotated[Session, Depends(get_db_session)],
) -> MinorConsentDocumentResponse:
    return MinorConsentDocumentResponse.model_validate(
        get_document_status(db, principal, get_settings())
    )


@app.post(
    "/api/v1/candidate/minor-consent-document",
    tags=["candidate privacy"],
    response_model=MinorConsentDocumentResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        403: {"model": ErrorResponse, "description": "Candidate role required"},
        409: {"model": ErrorResponse, "description": "Minor document prerequisite is not satisfied"},
        422: {"model": ErrorResponse, "description": "Invalid PDF upload"},
    },
)
def upload_candidate_minor_consent_document(
    document: Annotated[UploadFile, File(description="Private parent/legal-representative PDF")],
    principal: Annotated[Principal, Depends(candidate_principal)],
    db: Annotated[Session, Depends(get_db_session)],
) -> MinorConsentDocumentResponse:
    return MinorConsentDocumentResponse.model_validate(
        upload_document(db, principal, get_settings(), document)
    )


@app.get(
    "/api/v1/candidate/resume",
    tags=["candidate resume"],
    response_model=ResumeDocumentResponse,
    responses={403: {"model": ErrorResponse, "description": "Candidate role required"}},
)
def candidate_resume(
    principal: Annotated[Principal, Depends(candidate_principal)],
    db: Annotated[Session, Depends(get_db_session)],
) -> ResumeDocumentResponse:
    return ResumeDocumentResponse.model_validate(get_resume(db, principal))


@app.post(
    "/api/v1/candidate/resume",
    tags=["candidate resume"],
    response_model=ResumeDocumentResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        403: {"model": ErrorResponse, "description": "Candidate role required"},
        409: {"model": ErrorResponse, "description": "Processing consent is required"},
        422: {"model": ErrorResponse, "description": "Invalid PDF upload"},
    },
)
def upload_candidate_resume(
    resume: Annotated[UploadFile, File(description="Private candidate PDF resume")],
    principal: Annotated[Principal, Depends(candidate_principal)],
    db: Annotated[Session, Depends(get_db_session)],
) -> ResumeDocumentResponse:
    return ResumeDocumentResponse.model_validate(
        upload_resume(db, principal, get_settings(), resume)
    )


@app.patch(
    "/api/v1/candidate/resume/{document_id}/review",
    tags=["candidate resume"],
    response_model=ResumeDocumentResponse,
    responses={
        403: {"model": ErrorResponse, "description": "Candidate role required"},
        404: {"model": ErrorResponse, "description": "Resume or extraction not found"},
        409: {"model": ErrorResponse, "description": "Resume extraction cannot be reviewed"},
    },
)
def review_candidate_resume(
    document_id: str,
    request: ResumeReviewRequest,
    principal: Annotated[Principal, Depends(candidate_principal)],
    db: Annotated[Session, Depends(get_db_session)],
) -> ResumeDocumentResponse:
    return ResumeDocumentResponse.model_validate(
        review_resume(
            db,
            principal,
            document_id,
            accepted=request.accepted,
            fields=request.model_dump(exclude={"accepted"}, exclude_none=True),
        )
    )


@app.post(
    "/api/v1/assessments/attempts",
    tags=["assessments"],
    responses={
        401: {"model": ErrorResponse, "description": "Authentication required"},
        403: {"model": ErrorResponse, "description": "Candidate role required"},
        409: {"model": ErrorResponse, "description": "Assessment cannot be created"},
        422: {"model": ErrorResponse, "description": "Invalid request"},
    },
)
def create_assessment_attempt(
    request: CreateAttemptRequest,
    principal: Annotated[Principal, Depends(candidate_principal)],
) -> dict[str, Any]:
    try:
        attempt = assessment_service.create_attempt(
            principal.subject,
            request.specialization,
            request.declared_grade,
        )
    except AssessmentError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return assessment_service.public_attempt(attempt)


def _candidate_attempt(attempt_id: str, principal: Principal):
    try:
        attempt = assessment_service.get(attempt_id)
    except AssessmentError as exc:
        raise HTTPException(status_code=404, detail="attempt_not_found") from exc
    if attempt.candidate_id != principal.subject:
        # Do not reveal whether another candidate's attempt exists.
        raise HTTPException(status_code=404, detail="attempt_not_found")
    return attempt


@app.get(
    "/api/v1/assessments/attempts/{attempt_id}",
    tags=["assessments"],
    responses={
        401: {"model": ErrorResponse, "description": "Authentication required"},
        403: {"model": ErrorResponse, "description": "Candidate role required"},
        404: {"model": ErrorResponse, "description": "Assessment attempt not found"},
        422: {"model": ErrorResponse, "description": "Invalid request"},
    },
)
def get_assessment_attempt(
    attempt_id: str,
    principal: Annotated[Principal, Depends(candidate_principal)],
) -> dict[str, Any]:
    try:
        return assessment_service.public_attempt(_candidate_attempt(attempt_id, principal))
    except AssessmentError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.post(
    "/api/v1/assessments/attempts/{attempt_id}/submit",
    tags=["assessments"],
    responses={
        401: {"model": ErrorResponse, "description": "Authentication required"},
        403: {"model": ErrorResponse, "description": "Candidate role required"},
        404: {"model": ErrorResponse, "description": "Assessment attempt not found"},
        409: {"model": ErrorResponse, "description": "Assessment cannot be submitted"},
        422: {"model": ErrorResponse, "description": "Invalid request"},
    },
)
def submit_assessment_attempt(
    attempt_id: str,
    request: SubmitAttemptRequest,
    principal: Annotated[Principal, Depends(candidate_principal)],
) -> dict[str, Any]:
    try:
        _candidate_attempt(attempt_id, principal)
        attempt = assessment_service.submit(attempt_id, request.answers, request.followups, request.telemetry)
    except AssessmentError as exc:
        status = 404 if str(exc) == "attempt_not_found" else 409
        raise HTTPException(status_code=status, detail=str(exc)) from exc
    return assessment_service.public_attempt(attempt)
