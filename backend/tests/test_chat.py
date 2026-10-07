from uuid import uuid4

from sqlalchemy import create_engine, text
from test_invitations import _candidate, _employer, _headers, _offer

from app import main


def _verified_candidate(client, private_key, settings, *, sub: str):
    headers = _headers(private_key, settings, sub=sub, role="candidate")
    assert client.patch(
        "/api/v1/candidate/privacy",
        headers=headers,
        json={"processing_consent": True, "publication_consent": True, "discoverable": True},
    ).status_code == 200
    profile = client.patch(
        "/api/v1/candidate/profile",
        headers=headers,
        json={"display_name": "Chat Candidate", "headline": "Backend engineer"},
    )
    assert profile.status_code == 200
    main.assessment_service.family_exposure.clear()
    created = client.post(
        "/api/v1/assessments/attempts",
        headers=headers,
        json={"specialization": "Backend Engineering", "declared_grade": "Middle"},
    )
    assert created.status_code == 200, created.text
    attempt = main.assessment_service.attempts[created.json()["attempt_id"]]
    followups = {
        item.item_id: "retry backoff limit transaction rollback deterministic seed budget p95 latency"
        for item in attempt.items
        if item.progressive
    }
    submitted = client.post(
        f"/api/v1/assessments/attempts/{attempt.attempt_id}/submit",
        headers=headers,
        json={"answers": attempt.answer_keys, "followups": followups},
    )
    assert submitted.status_code == 200, submitted.text
    assert submitted.json()["grade_state"] == "verified"
    return headers, profile.json()["id"]


def _matched_pair(auth_context):
    client, private_key, settings = auth_context
    candidate_headers, candidate_id = _verified_candidate(
        client, private_key, settings, sub=f"chat-candidate-{uuid4().hex}"
    )
    employer_headers = _employer(client, private_key, settings, sub=f"chat-employer-{uuid4().hex}")
    invitation = client.post(
        "/api/v1/employer/invitations",
        headers=employer_headers,
        json=_offer(candidate_id),
    )
    assert invitation.status_code == 201, invitation.text
    pending_id = invitation.json()["id"]
    accepted = client.post(
        f"/api/v1/candidate/invitations/{pending_id}/respond",
        headers=candidate_headers,
        json={"action": "accepted"},
    )
    assert accepted.status_code == 200, accepted.text
    return client, private_key, settings, candidate_headers, employer_headers, accepted.json()["match_id"]


def test_chat_is_unavailable_before_match_and_conversation_is_created_atomically(auth_context):
    client, private_key, settings = auth_context
    candidate_headers, candidate_id = _verified_candidate(
        client, private_key, settings, sub=f"chat-before-candidate-{uuid4().hex}"
    )
    employer_headers = _employer(client, private_key, settings, sub=f"chat-before-employer-{uuid4().hex}")

    assert client.get("/api/v1/chat/conversations", headers=candidate_headers).json() == []
    assert client.get("/api/v1/chat/conversations", headers=employer_headers).json() == []
    unavailable = client.post(
        f"/api/v1/chat/conversations/{uuid4()}/messages",
        headers=candidate_headers,
        json={"body": "cold message"},
    )
    assert unavailable.status_code == 404
    assert unavailable.json()["error"]["code"] == "CONVERSATION_NOT_FOUND"
    employer_unavailable = client.post(
        f"/api/v1/chat/conversations/{uuid4()}/messages",
        headers=employer_headers,
        json={"body": "cold message"},
    )
    assert employer_unavailable.status_code == 404
    assert employer_unavailable.json()["error"]["code"] == "CONVERSATION_NOT_FOUND"

    invitation = client.post(
        "/api/v1/employer/invitations", headers=employer_headers, json=_offer(candidate_id)
    ).json()
    assert client.get("/api/v1/chat/conversations", headers=candidate_headers).json() == []
    assert client.post(
        f"/api/v1/candidate/invitations/{invitation['id']}/respond",
        headers=candidate_headers,
        json={"action": "accepted"},
    ).status_code == 200

    candidate_conversations = client.get("/api/v1/chat/conversations", headers=candidate_headers)
    assert candidate_conversations.status_code == 200
    assert len(candidate_conversations.json()) == 1
    conversation_id = candidate_conversations.json()[0]["id"]
    engine = create_engine(settings.database_url)
    try:
        with engine.connect() as connection:
            assert connection.execute(
                text("SELECT COUNT(*) FROM conversation WHERE match_id = :match_id"),
                {"match_id": candidate_conversations.json()[0]["match_id"]},
            ).scalar_one() == 1
            assert connection.execute(
                text("SELECT COUNT(*) FROM conversation_member WHERE conversation_id = :conversation_id"),
                {"conversation_id": conversation_id},
            ).scalar_one() == 2
    finally:
        engine.dispose()


def test_matched_parties_exchange_messages_contacts_and_read_state(auth_context):
    client, _private_key, settings, candidate_headers, employer_headers, _ = _matched_pair(auth_context)
    candidate_conversation = client.get("/api/v1/chat/conversations", headers=candidate_headers).json()[0]
    conversation_id = candidate_conversation["id"]

    initial = client.get(
        f"/api/v1/chat/conversations/{conversation_id}", headers=candidate_headers
    )
    assert initial.status_code == 200
    assert initial.json()["messages"] == []
    assert initial.json()["unread_count"] == 0

    sent = client.post(
        f"/api/v1/chat/conversations/{conversation_id}/messages",
        headers=candidate_headers,
        json={"body": "Здравствуйте, готов обсудить команду."},
    )
    assert sent.status_code == 201, sent.text
    assert sent.json()["sender_is_current"] is True

    employer_view = client.get(
        f"/api/v1/chat/conversations/{conversation_id}", headers=employer_headers
    )
    assert employer_view.status_code == 200
    assert employer_view.json()["unread_count"] == 1
    assert employer_view.json()["messages"][0]["body"] == "Здравствуйте, готов обсудить команду."
    employer_list = client.get("/api/v1/chat/conversations", headers=employer_headers).json()[0]
    assert employer_list["unread_count"] == 1

    read = client.post(f"/api/v1/chat/conversations/{conversation_id}/read", headers=employer_headers)
    assert read.status_code == 200
    assert read.json() == {"conversation_id": conversation_id, "marked_count": 1, "unread_count": 0}
    assert client.get(
        f"/api/v1/chat/conversations/{conversation_id}", headers=employer_headers
    ).json()["unread_count"] == 0

    contact = client.post(
        f"/api/v1/chat/conversations/{conversation_id}/contacts",
        headers=candidate_headers,
        json={"contact_type": "telegram", "contact_value": "@synthetic_candidate"},
    )
    assert contact.status_code == 201
    assert contact.json()["is_current"] is True
    other_side_contacts = client.get(
        f"/api/v1/chat/conversations/{conversation_id}", headers=employer_headers
    ).json()["contacts"]
    assert other_side_contacts == [
        {
            "id": contact.json()["id"],
            "is_current": False,
            "contact_type": "telegram",
            "contact_value": "@synthetic_candidate",
            "created_at": contact.json()["created_at"],
        }
    ]

    report = client.post(
        f"/api/v1/chat/conversations/{conversation_id}/reports",
        headers=employer_headers,
        json={"reason": "other", "details": "Synthetic test report"},
    )
    assert report.status_code == 201
    assert report.json()["status"] == "open"
    engine = create_engine(settings.database_url)
    try:
        with engine.connect() as connection:
            audit_details = connection.execute(
                text(
                    "SELECT details FROM audit_event WHERE event_type = 'conversation_reported' "
                    "ORDER BY occurred_at DESC LIMIT 1"
                )
            ).scalar_one()
        assert "Synthetic test report" not in audit_details
        assert "Здравствуйте" not in audit_details
    finally:
        engine.dispose()


def test_chat_membership_denies_outsider_and_invalid_message_is_safe(auth_context):
    client, private_key, settings, candidate_headers, employer_headers, _ = _matched_pair(auth_context)
    conversation_id = client.get("/api/v1/chat/conversations", headers=candidate_headers).json()[0]["id"]
    outsider_headers, _ = _candidate(
        client, private_key, settings, sub=f"chat-outsider-{uuid4().hex}", verified=False
    )

    assert client.get(
        f"/api/v1/chat/conversations/{conversation_id}", headers=outsider_headers
    ).status_code == 404
    assert client.post(
        f"/api/v1/chat/conversations/{conversation_id}/messages",
        headers=outsider_headers,
        json={"body": "intrusion"},
    ).status_code == 404
    invalid = client.post(
        f"/api/v1/chat/conversations/{conversation_id}/messages",
        headers=employer_headers,
        json={"body": "   "},
    )
    assert invalid.status_code == 422
    assert invalid.json()["error"]["code"] == "MESSAGE_BODY_REQUIRED"
