from datetime import UTC, datetime, timedelta

import jwt


def _headers(private_key, settings, *, sub, email, role):
    now = datetime.now(UTC)
    token = jwt.encode(
        {
            "iss": settings.keycloak_issuer,
            "aud": settings.keycloak_client_id,
            "sub": sub,
            "email": email,
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


def _vacancy_payload(**changes):
    payload = {
        "title": "Platform engineer",
        "description": "Build reliable services for a verified talent platform.",
        "location": "Москва",
        "work_mode": "hybrid",
        "employment_type": "full_time",
        "salary_min_rub": 180000,
        "salary_max_rub": 260000,
        "specialization": "backend-engineering",
        "grade": "middle",
    }
    payload.update(changes)
    return payload


def test_candidate_can_browse_apply_and_read_own_application_status(auth_context):
    client, private_key, settings = auth_context
    employer = _headers(
        private_key,
        settings,
        sub="kc-application-employer",
        email="hiring@applications.ru",
        role="employer",
    )
    candidate = _headers(
        private_key,
        settings,
        sub="kc-application-candidate",
        email="candidate@applications.ru",
        role="candidate",
    )

    company = client.patch(
        "/api/v1/employer/company",
        headers=employer,
        json={
            "name": "Evidence Systems",
            "public_contact_method": "hiring@evidence-systems.ru",
        },
    )
    assert company.status_code == 200
    created = client.post(
        "/api/v1/employer/vacancies",
        headers=employer,
        json=_vacancy_payload(),
    )
    assert created.status_code == 201
    vacancy_id = created.json()["id"]
    assert client.post(
        f"/api/v1/employer/vacancies/{vacancy_id}/publish",
        headers=employer,
    ).status_code == 200

    listed = client.get("/api/v1/candidate/vacancies", headers=candidate)
    assert listed.status_code == 200
    vacancy = listed.json()[0]
    assert vacancy["id"] == vacancy_id
    assert vacancy["company_name"] == "Evidence Systems"
    assert vacancy["application_id"] is None
    assert "public_contact_method" not in vacancy

    blocked = client.post(
        f"/api/v1/candidate/vacancies/{vacancy_id}/applications",
        headers=candidate,
    )
    assert blocked.status_code == 409
    assert blocked.json()["error"]["code"] == "PROCESSING_CONSENT_REQUIRED"

    consent = client.patch(
        "/api/v1/candidate/privacy",
        headers=candidate,
        json={"processing_consent": True},
    )
    assert consent.status_code == 200
    application = client.post(
        f"/api/v1/candidate/vacancies/{vacancy_id}/applications",
        headers=candidate,
    )
    assert application.status_code == 201, application.text
    application_body = application.json()
    assert application_body["status"] == "submitted"
    assert application_body["vacancy"]["id"] == vacancy_id
    assert [item["status"] for item in application_body["status_history"]] == ["submitted"]

    listed_after_apply = client.get("/api/v1/candidate/vacancies", headers=candidate)
    assert listed_after_apply.json()[0]["application_id"] == application_body["id"]
    assert listed_after_apply.json()[0]["application_status"] == "submitted"

    applications = client.get("/api/v1/candidate/applications", headers=candidate)
    assert applications.status_code == 200
    assert len(applications.json()) == 1
    assert applications.json()[0]["id"] == application_body["id"]
    assert applications.json()[0]["vacancy"]["salary_max_rub"] == 260000
    assert client.get("/api/v1/chat/conversations", headers=candidate).json() == []

    duplicate = client.post(
        f"/api/v1/candidate/vacancies/{vacancy_id}/applications",
        headers=candidate,
    )
    assert duplicate.status_code == 409
    assert duplicate.json()["error"]["code"] == "APPLICATION_EXISTS"


def test_candidate_vacancy_listing_is_published_only_and_application_is_role_scoped(auth_context):
    client, private_key, settings = auth_context
    employer = _headers(
        private_key,
        settings,
        sub="kc-application-lifecycle-employer",
        email="owner@lifecycle.ru",
        role="employer",
    )
    candidate = _headers(
        private_key,
        settings,
        sub="kc-application-lifecycle-candidate",
        email="candidate@lifecycle.ru",
        role="candidate",
    )

    draft = client.post(
        "/api/v1/employer/vacancies",
        headers=employer,
        json=_vacancy_payload(title="Draft only"),
    )
    assert draft.status_code == 201
    draft_id = draft.json()["id"]

    published = client.post(
        "/api/v1/employer/vacancies",
        headers=employer,
        json=_vacancy_payload(title="Will close"),
    )
    published_id = published.json()["id"]
    assert client.post(
        f"/api/v1/employer/vacancies/{published_id}/publish",
        headers=employer,
    ).status_code == 200
    assert client.delete(
        f"/api/v1/employer/vacancies/{published_id}",
        headers=employer,
    ).status_code == 200

    listed = client.get("/api/v1/candidate/vacancies", headers=candidate)
    assert listed.status_code == 200
    assert listed.json() == []

    consent = client.patch(
        "/api/v1/candidate/privacy",
        headers=candidate,
        json={"processing_consent": True},
    )
    assert consent.status_code == 200
    for vacancy_id in (draft_id, published_id):
        response = client.post(
            f"/api/v1/candidate/vacancies/{vacancy_id}/applications",
            headers=candidate,
        )
        assert response.status_code == 409
        assert response.json()["error"]["code"] == "VACANCY_NOT_PUBLISHED"

    employer_denied = client.get("/api/v1/candidate/applications", headers=employer)
    assert employer_denied.status_code == 403
    assert employer_denied.json()["error"]["code"] == "ROLE_REQUIRED"


def test_candidate_applications_are_isolated_between_candidates(auth_context):
    client, private_key, settings = auth_context
    employer = _headers(
        private_key,
        settings,
        sub="kc-application-isolation-employer",
        email="owner@isolation.ru",
        role="employer",
    )
    first = _headers(
        private_key,
        settings,
        sub="kc-application-isolation-first",
        email="first@isolation.ru",
        role="candidate",
    )
    second = _headers(
        private_key,
        settings,
        sub="kc-application-isolation-second",
        email="second@isolation.ru",
        role="candidate",
    )
    created = client.post(
        "/api/v1/employer/vacancies",
        headers=employer,
        json=_vacancy_payload(),
    )
    vacancy_id = created.json()["id"]
    assert client.post(
        f"/api/v1/employer/vacancies/{vacancy_id}/publish",
        headers=employer,
    ).status_code == 200
    for headers in (first, second):
        assert client.patch(
            "/api/v1/candidate/privacy",
            headers=headers,
            json={"processing_consent": True},
        ).status_code == 200

    assert client.post(
        f"/api/v1/candidate/vacancies/{vacancy_id}/applications",
        headers=first,
    ).status_code == 201
    assert client.get("/api/v1/candidate/applications", headers=first).json()
    assert client.get("/api/v1/candidate/applications", headers=second).json() == []
    second_listing = client.get("/api/v1/candidate/vacancies", headers=second).json()
    assert second_listing[0]["application_id"] is None


def test_employer_accepting_application_creates_match_and_unlocks_chat(auth_context):
    client, private_key, settings = auth_context
    employer = _headers(
        private_key,
        settings,
        sub="kc-application-match-employer",
        email="owner@application-match.ru",
        role="employer",
    )
    outsider = _headers(
        private_key,
        settings,
        sub="kc-application-match-outsider",
        email="other@application-match.ru",
        role="employer",
    )
    candidate = _headers(
        private_key,
        settings,
        sub="kc-application-match-candidate",
        email="candidate@application-match.ru",
        role="candidate",
    )

    company = client.patch(
        "/api/v1/employer/company",
        headers=employer,
        json={
            "name": "Application Match Labs",
            "public_contact_method": "team@application-match.ru",
        },
    )
    assert company.status_code == 200
    vacancy = client.post(
        "/api/v1/employer/vacancies",
        headers=employer,
        json=_vacancy_payload(title="Application match backend engineer"),
    )
    assert vacancy.status_code == 201
    vacancy_id = vacancy.json()["id"]
    assert client.post(
        f"/api/v1/employer/vacancies/{vacancy_id}/publish", headers=employer
    ).status_code == 200
    assert client.patch(
        "/api/v1/candidate/privacy",
        headers=candidate,
        json={"processing_consent": True},
    ).status_code == 200
    application = client.post(
        f"/api/v1/candidate/vacancies/{vacancy_id}/applications", headers=candidate
    )
    assert application.status_code == 201
    application_id = application.json()["id"]
    assert client.get("/api/v1/chat/conversations", headers=candidate).json() == []

    incoming = client.get("/api/v1/employer/applications", headers=employer)
    assert incoming.status_code == 200
    assert len(incoming.json()) == 1
    assert incoming.json()[0]["id"] == application_id
    assert incoming.json()[0]["status"] == "submitted"
    assert incoming.json()[0]["candidate"]["display_name"] == "Кандидат"
    assert "public_contact_method" not in incoming.json()[0]
    assert client.get("/api/v1/employer/applications", headers=outsider).json() == []
    assert client.put(
        f"/api/v1/employer/applications/{application_id}",
        headers=outsider,
        json={"status": "accepted"},
    ).status_code == 404

    reviewing = client.put(
        f"/api/v1/employer/applications/{application_id}",
        headers=employer,
        json={"status": "reviewing"},
    )
    assert reviewing.status_code == 200
    accepted = client.put(
        f"/api/v1/employer/applications/{application_id}",
        headers=employer,
        json={"status": "accepted"},
    )
    assert accepted.status_code == 200, accepted.text
    accepted_body = accepted.json()
    assert accepted_body["status"] == "accepted"
    assert accepted_body["match_id"]

    candidate_application = client.get(
        "/api/v1/candidate/applications", headers=candidate
    ).json()[0]
    assert candidate_application["status"] == "accepted"
    assert candidate_application["match_id"] == accepted_body["match_id"]
    assert [item["status"] for item in candidate_application["status_history"]] == [
        "submitted",
        "reviewing",
        "accepted",
    ]
    candidate_conversations = client.get(
        "/api/v1/chat/conversations", headers=candidate
    )
    employer_conversations = client.get(
        "/api/v1/chat/conversations", headers=employer
    )
    assert candidate_conversations.status_code == 200
    assert employer_conversations.status_code == 200
    assert len(candidate_conversations.json()) == 1
    assert len(employer_conversations.json()) == 1

    repeated = client.put(
        f"/api/v1/employer/applications/{application_id}",
        headers=employer,
        json={"status": "accepted"},
    )
    assert repeated.status_code == 200
    assert repeated.json()["match_id"] == accepted_body["match_id"]
    assert len(client.get("/api/v1/chat/conversations", headers=employer).json()) == 1
    assert client.get("/api/v1/employer/invitations", headers=employer).json() == []
    assert client.get("/api/v1/candidate/invitations", headers=candidate).json() == []

    terminal = client.put(
        f"/api/v1/employer/applications/{application_id}",
        headers=employer,
        json={"status": "rejected"},
    )
    assert terminal.status_code == 409
    assert terminal.json()["error"]["code"] == "APPLICATION_NOT_PENDING"
