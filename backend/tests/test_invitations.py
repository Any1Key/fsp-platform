from datetime import UTC, datetime, timedelta
from uuid import uuid4

import jwt
from sqlalchemy import create_engine, text

from app import main


def _valid_followup(item) -> str:
    responses = {
        "api-2": "bounded retry uses backoff and a limit",
        "sql-2": "transaction makes the migration atomic and rollback keeps it reversible",
        "test-2": "find the nondeterministic source and fix the seed for reproducibility",
        "arch-2": "measure the budget and latency at p95 before scaling",
    }
    return responses.get(item.family_id, "the explanation follows the constraint in the task")


def _headers(private_key, settings, *, sub: str, role: str):
    now = datetime.now(UTC)
    token = jwt.encode(
        {
            "iss": settings.keycloak_issuer,
            "aud": settings.keycloak_client_id,
            "sub": sub,
            "email": f"{sub}@team.ru" if role == "candidate" else f"{sub}@company.ru",
            "email_verified": True,
            "realm_access": {"roles": [role]},
            "iat": int(now.timestamp()),
            "exp": int((now + timedelta(minutes=5)).timestamp()),
        },
        private_key,
        algorithm="RS256",
        headers={"kid": "static"},
    )
    return {"Authorization": f"Bearer {token}"}


def _candidate(client, private_key, settings, *, sub: str, verified: bool = True):
    headers = _headers(private_key, settings, sub=sub, role="candidate")
    assert client.patch(
        "/api/v1/candidate/privacy",
        headers=headers,
        json={"processing_consent": True, "publication_consent": True, "discoverable": True},
    ).status_code == 200
    profile = client.patch(
        "/api/v1/candidate/profile",
        headers=headers,
        json={"display_name": "Visible Candidate", "headline": "Backend engineer"},
    )
    assert profile.status_code == 200
    if not verified:
        return headers, profile.json()["id"]
    main.assessment_service.family_exposure.clear()
    created = client.post(
        "/api/v1/assessments/attempts",
        headers=headers,
        json={"specialization": "Backend Engineering", "declared_grade": "Middle"},
    )
    assert created.status_code == 200
    attempt = main.assessment_service.attempts[created.json()["attempt_id"]]
    submitted = client.post(
        f"/api/v1/assessments/attempts/{attempt.attempt_id}/submit",
        headers=headers,
        json={
            "answers": attempt.answer_keys,
            "followups": {
                item.item_id: _valid_followup(item)
                for item in attempt.items
                if item.progressive
            },
        },
    )
    assert submitted.status_code == 200
    assert submitted.json()["grade_state"] == "verified"
    return headers, profile.json()["id"]


def _employer(client, private_key, settings, *, sub: str):
    headers = _headers(private_key, settings, sub=sub, role="employer")
    company = client.patch(
        "/api/v1/employer/company",
        headers=headers,
        json={
            "name": "Northstar Labs",
            "public_contact_method": "talent@northstar.ru",
        },
    )
    assert company.status_code == 200
    return headers


def _offer(candidate_id: str):
    return {
        "candidate_profile_id": candidate_id,
        "salary_min_rub": 180000,
        "salary_max_rub": 260000,
        "offer_description": "Build evidence-led platform services with the core team.",
    }


def test_employer_creates_salary_bearing_invitation_and_candidate_sees_only_safe_offer(auth_context):
    client, private_key, settings = auth_context
    candidate_headers, candidate_id = _candidate(
        client, private_key, settings, sub=f"invite-candidate-{uuid4().hex}"
    )
    employer_headers = _employer(client, private_key, settings, sub=f"invite-employer-{uuid4().hex}")

    invalid = client.post(
        "/api/v1/employer/invitations",
        headers=employer_headers,
        json={**_offer(candidate_id), "salary_min_rub": 300000, "salary_max_rub": 200000},
    )
    assert invalid.status_code == 422
    assert invalid.json()["error"]["code"] == "INVITATION_SALARY_INVALID"

    created = client.post(
        "/api/v1/employer/invitations", headers=employer_headers, json=_offer(candidate_id)
    )
    assert created.status_code == 201, created.text
    invitation = created.json()
    assert invitation["status"] == "pending"
    assert invitation["salary_min_rub"] == 180000
    assert invitation["company"] == {
        "id": invitation["company"]["id"],
        "name": "Northstar Labs",
        "contact_method": "talent@northstar.ru",
    }
    assert "email" not in invitation
    assert "phone" not in invitation
    assert "date_of_birth" not in invitation

    incoming = client.get("/api/v1/candidate/invitations", headers=candidate_headers)
    assert incoming.status_code == 200
    assert incoming.json()[0]["id"] == invitation["id"]
    assert incoming.json()[0]["salary_max_rub"] == 260000
    assert incoming.json()[0]["company"]["contact_method"] == "talent@northstar.ru"

    duplicate = client.post(
        "/api/v1/employer/invitations", headers=employer_headers, json=_offer(candidate_id)
    )
    assert duplicate.status_code == 409
    assert duplicate.json()["error"]["code"] == "INVITATION_ALREADY_PENDING"


def test_acceptance_creates_match_and_both_unlock_events_atomically(auth_context):
    client, private_key, settings = auth_context
    candidate_headers, candidate_id = _candidate(
        client, private_key, settings, sub=f"match-candidate-{uuid4().hex}"
    )
    employer_headers = _employer(client, private_key, settings, sub=f"match-employer-{uuid4().hex}")
    created = client.post(
        "/api/v1/employer/invitations", headers=employer_headers, json=_offer(candidate_id)
    )
    invitation_id = created.json()["id"]

    accepted = client.post(
        f"/api/v1/candidate/invitations/{invitation_id}/respond",
        headers=candidate_headers,
        json={"action": "accepted"},
    )
    assert accepted.status_code == 200
    body = accepted.json()
    assert body["status"] == "accepted"
    assert body["match_id"]
    assert body["matched_at"]
    assert body["contact_unlocked_at"]

    employer_view = client.get(
        f"/api/v1/employer/invitations/{invitation_id}", headers=employer_headers
    )
    assert employer_view.status_code == 200
    assert employer_view.json()["status"] == "accepted"
    assert employer_view.json()["match_id"] == body["match_id"]

    idempotent = client.post(
        f"/api/v1/candidate/invitations/{invitation_id}/respond",
        headers=candidate_headers,
        json={"action": "accepted"},
    )
    assert idempotent.status_code == 200
    assert idempotent.json()["match_id"] == body["match_id"]

    engine = create_engine(settings.database_url)
    with engine.connect() as connection:
        event_types = connection.execute(
            text(
                "SELECT event_type FROM domain_event WHERE aggregate_id = :match_id "
                "ORDER BY event_type"
            ),
            {"match_id": body["match_id"]},
        ).scalars().all()
        match_count = connection.execute(
            text("SELECT COUNT(*) FROM talent_match WHERE invitation_id = :invitation_id"),
            {"invitation_id": invitation_id},
        ).scalar_one()
    engine.dispose()
    assert event_types == ["CONTACT_UNLOCKED", "MATCH_CREATED"]
    assert match_count == 1


def test_blind_invitation_keeps_candidate_anonymous_until_acceptance(auth_context):
    client, private_key, settings = auth_context
    candidate_headers, candidate_id = _candidate(
        client, private_key, settings, sub=f"blind-invite-candidate-{uuid4().hex}"
    )
    employer_headers = _employer(client, private_key, settings, sub=f"blind-invite-employer-{uuid4().hex}")
    created = client.post(
        "/api/v1/employer/invitations",
        headers=employer_headers,
        json={**_offer(candidate_id), "blind_discovery": True},
    )

    assert created.status_code == 201
    invitation = created.json()
    assert invitation["blind_discovery"] is True
    assert invitation["candidate"]["display_name"] == "Anonymous candidate"

    employer_list = client.get("/api/v1/employer/invitations", headers=employer_headers)
    assert employer_list.status_code == 200
    assert employer_list.json()[0]["candidate"]["display_name"] == "Anonymous candidate"
    employer_pending_view = client.get(
        f"/api/v1/employer/invitations/{invitation['id']}", headers=employer_headers
    )
    assert employer_pending_view.status_code == 200
    assert employer_pending_view.json()["candidate"]["display_name"] == "Anonymous candidate"

    candidate_list = client.get("/api/v1/candidate/invitations", headers=candidate_headers)
    assert candidate_list.status_code == 200
    assert candidate_list.json()[0]["candidate"]["display_name"] == "Visible Candidate"

    accepted = client.post(
        f"/api/v1/candidate/invitations/{invitation['id']}/respond",
        headers=candidate_headers,
        json={"action": "accepted"},
    )
    assert accepted.status_code == 200
    assert accepted.json()["candidate"]["display_name"] == "Visible Candidate"

    employer_view = client.get(
        f"/api/v1/employer/invitations/{invitation['id']}", headers=employer_headers
    )
    assert employer_view.status_code == 200
    assert employer_view.json()["candidate"]["display_name"] == "Visible Candidate"


def test_invitation_transitions_are_scoped_and_decline_does_not_create_match(auth_context):
    client, private_key, settings = auth_context
    candidate_headers, candidate_id = _candidate(
        client, private_key, settings, sub=f"scope-candidate-{uuid4().hex}"
    )
    other_candidate_headers, _ = _candidate(
        client, private_key, settings, sub=f"scope-other-{uuid4().hex}"
    )
    employer_headers = _employer(client, private_key, settings, sub=f"scope-employer-{uuid4().hex}")
    invitation = client.post(
        "/api/v1/employer/invitations", headers=employer_headers, json=_offer(candidate_id)
    ).json()

    denied = client.post(
        f"/api/v1/candidate/invitations/{invitation['id']}/respond",
        headers=other_candidate_headers,
        json={"action": "accepted"},
    )
    assert denied.status_code == 404
    assert denied.json()["error"]["code"] == "INVITATION_NOT_FOUND"

    declined = client.post(
        f"/api/v1/candidate/invitations/{invitation['id']}/respond",
        headers=candidate_headers,
        json={"action": "declined"},
    )
    assert declined.status_code == 200
    assert declined.json()["status"] == "declined"
    assert declined.json()["match_id"] is None

    employer_list = client.get("/api/v1/employer/invitations", headers=employer_headers)
    assert employer_list.status_code == 200
    assert employer_list.json()[0]["status"] == "declined"

    engine = create_engine(settings.database_url)
    with engine.connect() as connection:
        match_count = connection.execute(
            text("SELECT COUNT(*) FROM talent_match WHERE invitation_id = :invitation_id"),
            {"invitation_id": invitation["id"]},
        ).scalar_one()
    engine.dispose()
    assert match_count == 0


def test_invitation_requires_company_contact_and_role_boundaries(auth_context):
    client, private_key, settings = auth_context
    candidate_headers, candidate_id = _candidate(
        client, private_key, settings, sub=f"company-required-{uuid4().hex}"
    )
    employer_headers = _headers(
        private_key, settings, sub=f"no-company-contact-{uuid4().hex}", role="employer"
    )
    missing_company = client.post(
        "/api/v1/employer/invitations", headers=employer_headers, json=_offer(candidate_id)
    )
    assert missing_company.status_code == 422
    assert missing_company.json()["error"]["code"] == "INVITATION_COMPANY_CONTACT_REQUIRED"

    candidate_attempt = client.post(
        "/api/v1/employer/invitations", headers=candidate_headers, json=_offer(candidate_id)
    )
    assert candidate_attempt.status_code == 403
    assert candidate_attempt.json()["error"]["code"] == "ROLE_REQUIRED"


def test_unconfirmed_candidate_remains_private_from_invitation_creation(auth_context):
    client, private_key, settings = auth_context
    _, candidate_id = _candidate(
        client, private_key, settings, sub=f"unconfirmed-invite-{uuid4().hex}", verified=False
    )
    employer_headers = _employer(client, private_key, settings, sub=f"unconfirmed-employer-{uuid4().hex}")
    response = client.post(
        "/api/v1/employer/invitations", headers=employer_headers, json=_offer(candidate_id)
    )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "INVITATION_CANDIDATE_GRADE_NOT_CONFIRMED"
