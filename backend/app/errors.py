"""Shared API error schemas and safe error response helpers."""

from __future__ import annotations

from typing import Any

from fastapi import Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict


class ErrorBody(BaseModel):
    """Stable machine-readable error details exposed to API clients."""

    model_config = ConfigDict(extra="forbid")

    code: str
    message: str
    request_id: str


class ErrorResponse(BaseModel):
    """The common error envelope for every non-success API response."""

    model_config = ConfigDict(extra="forbid")

    error: ErrorBody


ERROR_MESSAGES: dict[str, tuple[str, str]] = {
    "invalid_access_token": (
        "INVALID_ACCESS_TOKEN",
        "The access token is invalid or expired.",
    ),
    "email_not_verified": (
        "EMAIL_NOT_VERIFIED",
        "Email verification is required before using the platform.",
    ),
    "registration_domain_not_allowed": (
        "REGISTRATION_DOMAIN_NOT_ALLOWED",
        "Registration is available only for email domains ending in .ru.",
    ),
    "unsupported_or_ambiguous_role": (
        "UNSUPPORTED_ROLE",
        "The account must have exactly one supported platform role.",
    ),
    "role_required": (
        "ROLE_REQUIRED",
        "This area is restricted to the account role.",
    ),
    "identity_email_conflict": (
        "IDENTITY_EMAIL_CONFLICT",
        "The email is already linked to another identity.",
    ),
    "identity_already_exists": (
        "IDENTITY_ALREADY_EXISTS",
        "The identity could not be provisioned safely.",
    ),
    "identity_role_conflict": (
        "IDENTITY_ROLE_CONFLICT",
        "The account already has a different platform role.",
    ),
    "role_onboarding_required": (
        "ROLE_ONBOARDING_REQUIRED",
        "Choose a platform role before using this area.",
    ),
    "unsupported_onboarding_role": (
        "UNSUPPORTED_ONBOARDING_ROLE",
        "Choose either the candidate or employer role.",
    ),
    "processing_consent_required": (
        "PROCESSING_CONSENT_REQUIRED",
        "Processing consent is required before publication.",
    ),
    "company_name_required": (
        "COMPANY_NAME_REQUIRED",
        "A company name is required before the profile can be saved.",
    ),
    "company_profile_update_required": (
        "COMPANY_PROFILE_UPDATE_REQUIRED",
        "At least one company profile field is required.",
    ),
    "hiring_need_fields_required": (
        "HIRING_NEED_FIELDS_REQUIRED",
        "Team, role, specialization and target grade are required.",
    ),
    "hiring_need_skills_required": (
        "HIRING_NEED_SKILLS_REQUIRED",
        "Select at least one required or preferred skill.",
    ),
    "hiring_need_taxonomy_invalid": (
        "HIRING_NEED_TAXONOMY_INVALID",
        "The specialization or target grade is not available.",
    ),
    "hiring_need_skill_not_available": (
        "HIRING_NEED_SKILL_NOT_AVAILABLE",
        "A selected skill is not available in the active taxonomy.",
    ),
    "hiring_need_duplicate_skill": (
        "HIRING_NEED_DUPLICATE_SKILL",
        "A skill can be selected only once and in one preference group.",
    ),
    "hiring_need_too_many_skills": (
        "HIRING_NEED_TOO_MANY_SKILLS",
        "Select no more than 20 skills.",
    ),
    "hiring_need_already_exists": (
        "HIRING_NEED_ALREADY_EXISTS",
        "The current hiring need already exists; update it instead.",
    ),
    "hiring_need_not_found": (
        "HIRING_NEED_NOT_FOUND",
        "Create a hiring need before updating it.",
    ),
    "hiring_need_update_required": (
        "HIRING_NEED_UPDATE_REQUIRED",
        "At least one hiring need field is required.",
    ),
    "hiring_pipeline_stage_count_invalid": (
        "HIRING_PIPELINE_STAGE_COUNT_INVALID",
        "A hiring pipeline must contain between two and twelve stages.",
    ),
    "hiring_pipeline_stage_type_invalid": (
        "HIRING_PIPELINE_STAGE_TYPE_INVALID",
        "The hiring pipeline stage type is not supported.",
    ),
    "hiring_pipeline_stage_title_required": (
        "HIRING_PIPELINE_STAGE_TITLE_REQUIRED",
        "Every hiring pipeline stage needs a title.",
    ),
    "hiring_pipeline_platform_review_required": (
        "HIRING_PIPELINE_PLATFORM_REVIEW_REQUIRED",
        "The Verified Skill Passport review is required in the pipeline.",
    ),
    "hiring_pipeline_final_decision_required": (
        "HIRING_PIPELINE_FINAL_DECISION_REQUIRED",
        "The final decision stage is required in the pipeline.",
    ),
    "hiring_pipeline_duration_invalid": (
        "HIRING_PIPELINE_DURATION_INVALID",
        "Stage duration must be between five and 480 minutes.",
    ),
    "hiring_need_required_for_talent_radar": (
        "HIRING_NEED_REQUIRED_FOR_TALENT_RADAR",
        "Create a hiring need before opening Talent Radar.",
    ),
    "invitation_salary_invalid": (
        "INVITATION_SALARY_INVALID",
        "Salary minimum and maximum must be positive and the minimum cannot exceed the maximum.",
    ),
    "invitation_offer_required": (
        "INVITATION_OFFER_REQUIRED",
        "An offer description is required for an invitation.",
    ),
    "invitation_company_contact_required": (
        "INVITATION_COMPANY_CONTACT_REQUIRED",
        "Complete the company name and public contact method before sending an invitation.",
    ),
    "invitation_candidate_not_available": (
        "INVITATION_CANDIDATE_NOT_AVAILABLE",
        "The candidate is not currently available for reverse recruitment.",
    ),
    "invitation_candidate_grade_not_confirmed": (
        "INVITATION_CANDIDATE_GRADE_NOT_CONFIRMED",
        "Only candidates with a confirmed platform grade can receive reverse-recruitment invitations.",
    ),
    "invitation_already_pending": (
        "INVITATION_ALREADY_PENDING",
        "A pending invitation already exists for this candidate.",
    ),
    "invitation_not_found": (
        "INVITATION_NOT_FOUND",
        "The invitation was not found.",
    ),
    "invitation_not_pending": (
        "INVITATION_NOT_PENDING",
        "Only a pending invitation can be changed.",
    ),
    "conversation_not_found": (
        "CONVERSATION_NOT_FOUND",
        "The conversation was not found or is not available to this account.",
    ),
    "conversation_match_invalid": (
        "CONVERSATION_MATCH_INVALID",
        "The matched parties could not be added to a private conversation.",
    ),
    "message_body_required": (
        "MESSAGE_BODY_REQUIRED",
        "A non-empty text message is required.",
    ),
    "contact_value_required": (
        "CONTACT_VALUE_REQUIRED",
        "A contact value is required when sharing contact details.",
    ),
    "talent_radar_limit_invalid": (
        "TALENT_RADAR_LIMIT_INVALID",
        "Talent Radar limit must be between 1 and 100.",
    ),
    "talent_radar_specialization_invalid": (
        "TALENT_RADAR_SPECIALIZATION_INVALID",
        "The Talent Radar specialization filter is not available.",
    ),
    "talent_radar_grade_invalid": (
        "TALENT_RADAR_GRADE_INVALID",
        "The Talent Radar grade filter is not available.",
    ),
    "talent_radar_skill_invalid": (
        "TALENT_RADAR_SKILL_INVALID",
        "The Talent Radar skill filter is not available.",
    ),
    "talent_radar_fsp_invalid": (
        "TALENT_RADAR_FSP_INVALID",
        "The Talent Radar FSP filter is not available.",
    ),
    "fsp_participant_not_found": (
        "FSP_PARTICIPANT_NOT_FOUND",
        "The FSP participant was not found in the configured registry.",
    ),
    "date_of_birth_in_future": (
        "DATE_OF_BIRTH_IN_FUTURE",
        "Date of birth cannot be in the future.",
    ),
    "publication_consent_required": (
        "PUBLICATION_CONSENT_REQUIRED",
        "Publication consent is required before discoverability.",
    ),
    "minor_document_processing_consent_required": (
        "MINOR_DOCUMENT_PROCESSING_CONSENT_REQUIRED",
        "Processing consent is required before uploading a representative document.",
    ),
    "minor_document_only_for_minor": (
        "MINOR_DOCUMENT_ONLY_FOR_MINOR",
        "A representative consent document is required only for a minor profile.",
    ),
    "minor_consent_document_required": (
        "MINOR_CONSENT_DOCUMENT_REQUIRED",
        "A parent or legal-representative consent document is required before publication.",
    ),
    "minor_document_invalid_filename": (
        "MINOR_DOCUMENT_INVALID_FILENAME",
        "Upload a PDF document with a valid filename.",
    ),
    "minor_document_invalid_type": (
        "MINOR_DOCUMENT_INVALID_TYPE",
        "The representative document must be uploaded as a PDF.",
    ),
    "minor_document_invalid_pdf": (
        "MINOR_DOCUMENT_INVALID_PDF",
        "The uploaded file is not a valid PDF document.",
    ),
    "minor_document_too_large": (
        "MINOR_DOCUMENT_TOO_LARGE",
        "The representative document exceeds the configured size limit.",
    ),
    "resume_invalid_filename": (
        "RESUME_INVALID_FILENAME",
        "Upload a PDF document with a valid filename.",
    ),
    "resume_invalid_type": (
        "RESUME_INVALID_TYPE",
        "The resume must be uploaded as a PDF.",
    ),
    "resume_invalid_pdf": (
        "RESUME_INVALID_PDF",
        "The uploaded file is not a valid PDF document.",
    ),
    "resume_too_large": (
        "RESUME_TOO_LARGE",
        "The resume exceeds the configured size limit.",
    ),
    "resume_not_found": (
        "RESUME_NOT_FOUND",
        "The requested resume is not available.",
    ),
    "resume_extraction_not_found": (
        "RESUME_EXTRACTION_NOT_FOUND",
        "No extracted fields are available for this resume.",
    ),
    "resume_already_reviewed": (
        "RESUME_ALREADY_REVIEWED",
        "This resume extraction has already been reviewed.",
    ),
    "resume_extraction_unavailable": (
        "RESUME_EXTRACTION_UNAVAILABLE",
        "This PDF does not contain extractable text.",
    ),
    "authorization_header_required": (
        "AUTHORIZATION_REQUIRED",
        "A Bearer access token is required.",
    ),
    "database_unavailable": (
        "DATABASE_UNAVAILABLE",
        "The application database is temporarily unavailable.",
    ),
    "attempt_not_found": (
        "ASSESSMENT_ATTEMPT_NOT_FOUND",
        "The assessment attempt was not found.",
    ),
    "attempt_already_submitted": (
        "ASSESSMENT_ATTEMPT_ALREADY_SUBMITTED",
        "The assessment attempt has already been submitted.",
    ),
    "retest_locked_until_90_days": (
        "ASSESSMENT_RETEST_LOCKED",
        "A new assessment attempt is not available yet.",
    ),
    "all_items_are_required": (
        "ASSESSMENT_ITEMS_REQUIRED",
        "Answers are required for every assessment item.",
    ),
    "unsupported specialization or grade": (
        "ASSESSMENT_BLUEPRINT_UNSUPPORTED",
        "The requested specialization or grade is not supported.",
    ),
    "template_family_exposure_budget_reached": (
        "ASSESSMENT_EXPOSURE_LIMIT",
        "The assessment form is temporarily unavailable.",
    ),
}


def request_id_for(request: Request) -> str:
    """Return the middleware-assigned ID, with a safe fallback for direct use."""

    return getattr(request.state, "request_id", "unknown")


def error_response(
    request: Request,
    *,
    status_code: int,
    code: str,
    message: str,
    headers: dict[str, str] | None = None,
) -> JSONResponse:
    """Build the single response shape used by all API exception handlers."""

    request_id = request_id_for(request)
    response_headers = {"X-Request-ID": request_id}
    if headers:
        response_headers.update(headers)
    return JSONResponse(
        status_code=status_code,
        content={
            "error": {
                "code": code,
                "message": message,
                "request_id": request_id,
            }
        },
        headers=response_headers,
    )


def normalize_http_error(status_code: int, detail: Any) -> tuple[str, str]:
    """Map internal route details to stable, non-sensitive public errors."""

    if isinstance(detail, str) and detail in ERROR_MESSAGES:
        return ERROR_MESSAGES[detail]
    if status_code == 400:
        return "BAD_REQUEST", "The request could not be processed."
    if status_code == 401:
        return "UNAUTHENTICATED", "Authentication is required."
    if status_code == 403:
        return "FORBIDDEN", "You do not have permission to perform this action."
    if status_code == 404:
        return "RESOURCE_NOT_FOUND", "The requested resource was not found."
    if status_code == 409:
        return "CONFLICT", "The request conflicts with the current resource state."
    if status_code == 422:
        return "VALIDATION_ERROR", "Request validation failed."
    if status_code >= 500:
        return "INTERNAL_ERROR", "The service could not complete the request."
    return "REQUEST_ERROR", "The request could not be processed."
