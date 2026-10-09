from datetime import UTC, datetime

import pytest

from app.ats import (
    AtsContractError,
    AtsReplayGuard,
    accept_signed_webhook,
    ats_contract,
    build_event,
    serialize_event,
    sign_webhook,
    verify_webhook_signature,
)


def test_ats_contract_endpoint_and_openapi_expose_versioned_security_boundary(auth_context):
    client, _, _ = auth_context

    response = client.get("/api/v1/integrations/ats/v1/contract")

    assert response.status_code == 200
    body = response.json()
    assert body["api_version"] == "v1"
    assert body["envelope_schema"] == "fsp.ats.event.v1"
    assert {event["event_type"] for event in body["events"]} == {
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
    }
    assert body["webhook"]["signature_header"] == "X-FSP-Signature"
    assert body["webhook"]["idempotency_header"] == "Idempotency-Key"
    assert "until an accepted invitation" in body["contact_policy"]

    openapi = client.get("/openapi.json").json()
    operation = openapi["paths"]["/api/v1/integrations/ats/v1/contract"]["get"]
    assert operation["tags"] == ["integrations"]
    assert operation["responses"]["200"]["content"]["application/json"]["schema"]["$ref"].endswith(
        "/AtsContract"
    )


def test_event_builder_redacts_candidate_contact_until_match_unlock():
    data = {
        "candidate_email": "candidate@example.invalid",
        "candidate_phone": "+7 900 000-00-00",
        "nested": {"contact": "private", "skill": "Python"},
        "salary_min_rub": 180000,
    }

    locked = build_event(
        event_type="invitation.sent",
        direction="platform_to_ats",
        employer_id="employer-1",
        aggregate_type="invitation",
        aggregate_id="invitation-1",
        data=data,
        contact_unlocked=False,
        event_id="event-1",
        idempotency_key="event-1",
        occurred_at=datetime(2026, 10, 9, tzinfo=UTC),
    )
    unlocked = build_event(
        event_type="contact.unlocked",
        direction="platform_to_ats",
        employer_id="employer-1",
        aggregate_type="talent_match",
        aggregate_id="match-1",
        data=data,
        contact_unlocked=True,
        event_id="event-2",
        idempotency_key="event-2",
        occurred_at=datetime(2026, 10, 9, tzinfo=UTC),
    )

    assert locked.data == {"nested": {"skill": "Python"}, "salary_min_rub": 180000}
    assert unlocked.data == data
    assert data["candidate_email"] == "candidate@example.invalid"

    with pytest.raises(AtsContractError, match="direction"):
        build_event(
            event_type="invitation.sent",
            direction="ats_to_platform",
            employer_id="employer-1",
            aggregate_type="invitation",
            aggregate_id="invitation-1",
            data={},
            contact_unlocked=False,
        )


def test_signed_webhook_is_tamper_and_replay_resistant():
    event = build_event(
        event_type="application.status_changed",
        direction="ats_to_platform",
        employer_id="employer-1",
        aggregate_type="application",
        aggregate_id="application-1",
        data={"status": "shortlisted"},
        contact_unlocked=False,
        event_id="event-3",
        idempotency_key="delivery-3",
        occurred_at=datetime(2026, 10, 9, tzinfo=UTC),
    )
    payload = serialize_event(event)
    signature = sign_webhook(payload, "employer-secret", timestamp=1_000)
    guard = AtsReplayGuard(ttl_seconds=300)

    received, first = accept_signed_webhook(
        payload,
        signature=signature,
        secret="employer-secret",
        idempotency_key="delivery-3",
        replay_guard=guard,
        now=1_000,
    )
    _, duplicate = accept_signed_webhook(
        payload,
        signature=signature,
        secret="employer-secret",
        idempotency_key="delivery-3",
        replay_guard=guard,
        now=1_001,
    )

    assert received.event_id == "event-3"
    assert first.status == "accepted"
    assert duplicate.status == "duplicate"
    assert verify_webhook_signature(payload, signature, "employer-secret", now=1_000) == 1_000

    with pytest.raises(AtsContractError, match="invalid"):
        verify_webhook_signature(payload + b"tampered", signature, "employer-secret", now=1_000)
    with pytest.raises(AtsContractError, match="expired"):
        verify_webhook_signature(payload, signature, "employer-secret", now=1_301)


def test_ats_contract_is_available_as_a_typed_port_projection():
    contract = ats_contract()

    assert contract.api_version == "v1"
    assert any(item.event_type == "contact.unlocked" for item in contract.events)
    assert contract.webhook.replay_window_seconds == 300
    assert contract.retry.retryable_statuses == [408, 425, 429, 500, 502, 503, 504]
