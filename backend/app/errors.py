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
