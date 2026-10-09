"""Vendor-neutral ATS integration contract and security primitives.

The core application owns the event shape and privacy boundary. Transport,
credential storage, delivery retries, and a vendor-specific HTTP client belong
behind :class:`AtsConnectorPort` and are intentionally not required by the
platform runtime.
"""

from __future__ import annotations

import hashlib
import hmac
import time
from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any, Literal, Protocol
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field

AtsEventType = Literal[
    "vacancy.created",
    "vacancy.updated",
    "vacancy.closed",
    "invitation.sent",
    "invitation.viewed",
    "invitation.accepted",
    "invitation.declined",
    "application.created",
    "application.status_changed",
    "contact.unlocked",
]
AtsEventDirection = Literal["platform_to_ats", "ats_to_platform"]

_EVENT_DIRECTIONS: dict[str, frozenset[str]] = {
    "vacancy.created": frozenset({"platform_to_ats", "ats_to_platform"}),
    "vacancy.updated": frozenset({"platform_to_ats", "ats_to_platform"}),
    "vacancy.closed": frozenset({"platform_to_ats", "ats_to_platform"}),
    "invitation.sent": frozenset({"platform_to_ats"}),
    "invitation.viewed": frozenset({"platform_to_ats"}),
    "invitation.accepted": frozenset({"platform_to_ats"}),
    "invitation.declined": frozenset({"platform_to_ats"}),
    "application.created": frozenset({"platform_to_ats", "ats_to_platform"}),
    "application.status_changed": frozenset({"platform_to_ats", "ats_to_platform"}),
    "contact.unlocked": frozenset({"platform_to_ats"}),
}

_CONTACT_FIELD_NAMES = frozenset(
    {
        "candidate_contact",
        "candidate_contacts",
        "candidate_email",
        "candidate_phone",
        "contact",
        "contact_method",
        "contacts",
        "email",
        "phone",
        "telegram",
        "whatsapp",
    }
)


class AtsContractError(ValueError):
    """Raised when an ATS payload violates the platform contract."""


class AtsAggregate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: str = Field(min_length=1, max_length=80)
    id: str = Field(min_length=1, max_length=128)


class AtsEventEnvelope(BaseModel):
    """Stable event envelope shared by outbound events and inbound webhooks."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    schema_name: Literal["fsp.ats.event.v1"] = Field(
        default="fsp.ats.event.v1",
        alias="schema",
    )
    event_id: str = Field(min_length=1, max_length=64)
    event_type: AtsEventType
    direction: AtsEventDirection
    employer_id: str = Field(min_length=1, max_length=128)
    aggregate: AtsAggregate
    occurred_at: datetime
    idempotency_key: str = Field(min_length=1, max_length=128)
    data: dict[str, Any]


class AtsEventDefinition(BaseModel):
    model_config = ConfigDict(extra="forbid")

    event_type: AtsEventType
    directions: list[AtsEventDirection]
    aggregate_types: list[str]
    description: str


class AtsWebhookContract(BaseModel):
    model_config = ConfigDict(extra="forbid")

    signature_header: str
    signature_format: str
    idempotency_header: str
    secret_scope: str
    replay_window_seconds: int
    canonical_payload: str
    duplicate_delivery: str


class AtsRetryContract(BaseModel):
    model_config = ConfigDict(extra="forbid")

    retryable_statuses: list[int]
    backoff: str
    dead_letter_visibility: str


class AtsContract(BaseModel):
    """Machine-readable contract exposed by the public API documentation."""

    model_config = ConfigDict(extra="forbid")

    api_version: Literal["v1"] = "v1"
    envelope_schema: str = "fsp.ats.event.v1"
    events: list[AtsEventDefinition]
    webhook: AtsWebhookContract
    retry: AtsRetryContract
    contact_policy: str


class AtsWebhookReceipt(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["accepted", "duplicate"]
    event_id: str
    idempotency_key: str


class AtsConnectorPort(Protocol):
    """Port implemented by a future employer-specific ATS connector."""

    def publish(self, event: AtsEventEnvelope) -> None:
        """Deliver one already-sanitized event to an employer's ATS."""

    def receive(
        self,
        *,
        payload: bytes,
        signature: str,
        secret: str,
        idempotency_key: str,
    ) -> AtsWebhookReceipt:
        """Verify and accept one signed ATS webhook."""


def _redact_contact_values(value: Any, *, contact_unlocked: bool) -> Any:
    if contact_unlocked:
        return value
    if isinstance(value, Mapping):
        return {
            str(key): _redact_contact_values(item, contact_unlocked=False)
            for key, item in value.items()
            if str(key).strip().lower() not in _CONTACT_FIELD_NAMES
        }
    if isinstance(value, list):
        return [_redact_contact_values(item, contact_unlocked=False) for item in value]
    if isinstance(value, tuple):
        return tuple(_redact_contact_values(item, contact_unlocked=False) for item in value)
    return value


def sanitize_event_data(data: Mapping[str, Any], *, contact_unlocked: bool) -> dict[str, Any]:
    """Copy event data and remove contact fields until match unlock.

    This deliberately uses a conservative field-name denylist. Connector
    authors must not rely on a particular UI projection to enforce privacy.
    """

    sanitized = _redact_contact_values(data, contact_unlocked=contact_unlocked)
    if not isinstance(sanitized, dict):  # pragma: no cover - Mapping always yields dict
        raise AtsContractError("event_data_must_be_an_object")
    return sanitized


def build_event(
    *,
    event_type: AtsEventType,
    direction: AtsEventDirection,
    employer_id: str,
    aggregate_type: str,
    aggregate_id: str,
    data: Mapping[str, Any],
    contact_unlocked: bool,
    event_id: str | None = None,
    idempotency_key: str | None = None,
    occurred_at: datetime | None = None,
) -> AtsEventEnvelope:
    """Create an event with the contact boundary applied server-side."""

    if direction not in _EVENT_DIRECTIONS[event_type]:
        raise AtsContractError("event_direction_invalid")
    event_time = occurred_at or datetime.now(UTC)
    if event_time.tzinfo is None:
        raise AtsContractError("occurred_at_must_include_timezone")
    return AtsEventEnvelope(
        event_id=event_id or str(uuid4()),
        event_type=event_type,
        direction=direction,
        employer_id=employer_id,
        aggregate=AtsAggregate(type=aggregate_type, id=aggregate_id),
        occurred_at=event_time,
        idempotency_key=idempotency_key or event_id or str(uuid4()),
        data=sanitize_event_data(data, contact_unlocked=contact_unlocked),
    )


def serialize_event(event: AtsEventEnvelope) -> bytes:
    """Serialize an event with the public wire aliases preserved."""

    return event.model_dump_json(by_alias=True).encode("utf-8")


def sign_webhook(payload: bytes, secret: str, *, timestamp: int) -> str:
    """Return the versioned HMAC header for an exact raw request body."""

    if not secret:
        raise AtsContractError("webhook_secret_required")
    signed = f"{timestamp}.".encode() + payload
    digest = hmac.new(secret.encode("utf-8"), signed, hashlib.sha256).hexdigest()
    return f"t={timestamp},v1={digest}"


def verify_webhook_signature(
    payload: bytes,
    signature: str,
    secret: str,
    *,
    now: int | None = None,
    tolerance_seconds: int = 300,
) -> int:
    """Verify HMAC and freshness, returning the signed Unix timestamp."""

    if not secret:
        raise AtsContractError("webhook_secret_required")
    values: dict[str, list[str]] = {}
    for part in signature.split(","):
        key, separator, value = part.strip().partition("=")
        if not separator or not key or not value:
            raise AtsContractError("webhook_signature_invalid")
        values.setdefault(key, []).append(value)
    timestamps = values.get("t", [])
    versions = values.get("v1", [])
    if len(timestamps) != 1 or not versions:
        raise AtsContractError("webhook_signature_invalid")
    try:
        timestamp = int(timestamps[0])
    except ValueError as exc:
        raise AtsContractError("webhook_signature_invalid") from exc
    current_time = int(time.time()) if now is None else now
    if abs(current_time - timestamp) > tolerance_seconds:
        raise AtsContractError("webhook_signature_expired")
    expected = sign_webhook(payload, secret, timestamp=timestamp).split("v1=", 1)[1]
    if not any(hmac.compare_digest(expected, candidate) for candidate in versions):
        raise AtsContractError("webhook_signature_invalid")
    return timestamp


class AtsReplayGuard:
    """Small process-local guard for the contract and tests.

    A production connector must replace this with durable, shared storage so
    multiple API workers cannot accept the same idempotency key concurrently.
    """

    def __init__(self, *, ttl_seconds: int = 300, max_entries: int = 10_000) -> None:
        if ttl_seconds <= 0 or max_entries <= 0:
            raise ValueError("replay_guard_limits_must_be_positive")
        self.ttl_seconds = ttl_seconds
        self.max_entries = max_entries
        self._expires_at: dict[str, int] = {}

    def accept(self, idempotency_key: str, *, now: int | None = None) -> bool:
        if not idempotency_key:
            raise AtsContractError("idempotency_key_required")
        current_time = int(time.time()) if now is None else now
        self._expires_at = {
            key: expires_at
            for key, expires_at in self._expires_at.items()
            if expires_at > current_time
        }
        if idempotency_key in self._expires_at:
            return False
        if len(self._expires_at) >= self.max_entries:
            oldest_key = min(self._expires_at, key=self._expires_at.get)
            del self._expires_at[oldest_key]
        self._expires_at[idempotency_key] = current_time + self.ttl_seconds
        return True


def accept_signed_webhook(
    payload: bytes,
    *,
    signature: str,
    secret: str,
    idempotency_key: str,
    replay_guard: AtsReplayGuard,
    now: int | None = None,
) -> tuple[AtsEventEnvelope, AtsWebhookReceipt]:
    """Verify, validate, and classify one inbound webhook delivery."""

    verify_webhook_signature(payload, signature, secret, now=now)
    try:
        event = AtsEventEnvelope.model_validate_json(payload)
    except ValueError as exc:
        raise AtsContractError("webhook_payload_invalid") from exc
    if event.direction != "ats_to_platform":
        raise AtsContractError("webhook_direction_invalid")
    if event.direction not in _EVENT_DIRECTIONS[event.event_type]:
        raise AtsContractError("event_direction_invalid")
    if event.idempotency_key != idempotency_key:
        raise AtsContractError("idempotency_key_mismatch")
    accepted = replay_guard.accept(idempotency_key, now=now)
    receipt = AtsWebhookReceipt(
        status="accepted" if accepted else "duplicate",
        event_id=event.event_id,
        idempotency_key=idempotency_key,
    )
    return event, receipt


def ats_contract() -> AtsContract:
    return AtsContract(
        events=[
            AtsEventDefinition(
                event_type="vacancy.created",
                directions=["platform_to_ats", "ats_to_platform"],
                aggregate_types=["vacancy"],
                description="A vacancy is created or imported for an employer.",
            ),
            AtsEventDefinition(
                event_type="vacancy.updated",
                directions=["platform_to_ats", "ats_to_platform"],
                aggregate_types=["vacancy"],
                description="A vacancy's non-identity fields change.",
            ),
            AtsEventDefinition(
                event_type="vacancy.closed",
                directions=["platform_to_ats", "ats_to_platform"],
                aggregate_types=["vacancy"],
                description="A vacancy stops accepting applications.",
            ),
            AtsEventDefinition(
                event_type="invitation.sent",
                directions=["platform_to_ats"],
                aggregate_types=["invitation"],
                description="A salary-bearing reverse-recruitment invitation is sent.",
            ),
            AtsEventDefinition(
                event_type="invitation.viewed",
                directions=["platform_to_ats"],
                aggregate_types=["invitation"],
                description="A candidate views an invitation in their inbox.",
            ),
            AtsEventDefinition(
                event_type="invitation.accepted",
                directions=["platform_to_ats"],
                aggregate_types=["invitation"],
                description="A candidate accepts and the invitation becomes a match.",
            ),
            AtsEventDefinition(
                event_type="invitation.declined",
                directions=["platform_to_ats"],
                aggregate_types=["invitation"],
                description="A candidate declines an invitation.",
            ),
            AtsEventDefinition(
                event_type="application.created",
                directions=["platform_to_ats", "ats_to_platform"],
                aggregate_types=["application"],
                description="A candidate application is created or imported.",
            ),
            AtsEventDefinition(
                event_type="application.status_changed",
                directions=["platform_to_ats", "ats_to_platform"],
                aggregate_types=["application"],
                description="An application moves to another employer-owned status.",
            ),
            AtsEventDefinition(
                event_type="contact.unlocked",
                directions=["platform_to_ats"],
                aggregate_types=["talent_match"],
                description="An accepted match unlocks the authorized contact flow.",
            ),
        ],
        webhook=AtsWebhookContract(
            signature_header="X-FSP-Signature",
            signature_format="t={unix_seconds},v1={hex_hmac_sha256(t + '.' + raw_body)}",
            idempotency_header="Idempotency-Key",
            secret_scope="one credential per employer connector; never in event payloads",
            replay_window_seconds=300,
            canonical_payload="The exact UTF-8 request bytes, without JSON reformatting.",
            duplicate_delivery="Return the original event identity with status duplicate; do not apply side effects twice.",
        ),
        retry=AtsRetryContract(
            retryable_statuses=[408, 425, 429, 500, 502, 503, 504],
            backoff="exponential with jitter, bounded by connector policy",
            dead_letter_visibility="Persist delivery failure metadata without payload secrets and expose it to the employer integration operator.",
        ),
        contact_policy="Candidate contact fields are omitted until an accepted invitation creates a match and emits contact.unlocked.",
    )
