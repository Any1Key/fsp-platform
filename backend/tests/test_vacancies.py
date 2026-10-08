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


def _payload(**changes):
    payload = {
        "title": "Backend platform engineer",
        "description": "Build reliable services for the FSP talent platform.",
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


def test_employer_can_create_read_update_publish_and_close_vacancy(auth_context):
    client, private_key, settings = auth_context
    employer = _headers(
        private_key,
        settings,
        sub="kc-vacancy-owner",
        email="hiring@vacancy-company.ru",
        role="employer",
    )

    assert client.get("/api/v1/employer/vacancies", headers=employer).json() == []

    created = client.post(
        "/api/v1/employer/vacancies",
        headers=employer,
        json=_payload(),
    )
    assert created.status_code == 201, created.text
    body = created.json()
    vacancy_id = body["id"]
    assert body["status"] == "draft"
    assert body["salary_min_rub"] == 180000
    assert body["salary_max_rub"] == 260000
    assert body["specialization"] == {"slug": "backend-engineering", "name": "Backend Engineering"}
    assert body["grade"] == {"slug": "middle", "name": "Middle"}
    assert body["published_at"] is None

    updated = client.patch(
        f"/api/v1/employer/vacancies/{vacancy_id}",
        headers=employer,
        json={"description": "Own the platform API and delivery workflows.", "salary_max_rub": 280000},
    )
    assert updated.status_code == 200, updated.text
    assert updated.json()["title"] == "Backend platform engineer"
    assert updated.json()["description"] == "Own the platform API and delivery workflows."
    assert updated.json()["salary_max_rub"] == 280000

    published = client.post(
        f"/api/v1/employer/vacancies/{vacancy_id}/publish",
        headers=employer,
    )
    assert published.status_code == 200, published.text
    assert published.json()["status"] == "published"
    assert published.json()["published_at"] is not None

    listed = client.get("/api/v1/employer/vacancies", headers=employer)
    assert listed.status_code == 200
    assert [item["id"] for item in listed.json()] == [vacancy_id]

    closed = client.delete(f"/api/v1/employer/vacancies/{vacancy_id}", headers=employer)
    assert closed.status_code == 200, closed.text
    assert closed.json()["status"] == "closed"
    assert client.get(f"/api/v1/employer/vacancies/{vacancy_id}", headers=employer).json()["status"] == "closed"

    cannot_republish = client.post(
        f"/api/v1/employer/vacancies/{vacancy_id}/publish",
        headers=employer,
    )
    assert cannot_republish.status_code == 409
    assert cannot_republish.json()["error"]["code"] == "VACANCY_CLOSED"


def test_vacancy_requires_positive_ordered_salary_without_partial_write(auth_context):
    client, private_key, settings = auth_context
    employer = _headers(
        private_key,
        settings,
        sub="kc-vacancy-salary",
        email="salary@vacancy-company.ru",
        role="employer",
    )

    invalid_order = client.post(
        "/api/v1/employer/vacancies",
        headers=employer,
        json=_payload(salary_min_rub=300000, salary_max_rub=200000),
    )
    assert invalid_order.status_code == 422
    assert invalid_order.json()["error"]["code"] == "VACANCY_SALARY_INVALID"
    assert client.get("/api/v1/employer/vacancies", headers=employer).json() == []

    created = client.post("/api/v1/employer/vacancies", headers=employer, json=_payload())
    vacancy_id = created.json()["id"]
    invalid_update = client.patch(
        f"/api/v1/employer/vacancies/{vacancy_id}",
        headers=employer,
        json={"salary_min_rub": 400000, "salary_max_rub": 100000},
    )
    assert invalid_update.status_code == 422
    assert invalid_update.json()["error"]["code"] == "VACANCY_SALARY_INVALID"
    unchanged = client.get(f"/api/v1/employer/vacancies/{vacancy_id}", headers=employer).json()
    assert unchanged["salary_min_rub"] == 180000
    assert unchanged["salary_max_rub"] == 260000

    null_salary = client.patch(
        f"/api/v1/employer/vacancies/{vacancy_id}",
        headers=employer,
        json={"salary_min_rub": None},
    )
    assert null_salary.status_code == 422
    assert null_salary.json()["error"]["code"] == "VACANCY_SALARY_INVALID"


def test_vacancy_is_company_owned_and_role_protected(auth_context):
    client, private_key, settings = auth_context
    first = _headers(
        private_key,
        settings,
        sub="kc-vacancy-first",
        email="first@vacancy-company.ru",
        role="employer",
    )
    second = _headers(
        private_key,
        settings,
        sub="kc-vacancy-second",
        email="second@vacancy-company.ru",
        role="employer",
    )
    candidate = _headers(
        private_key,
        settings,
        sub="kc-vacancy-candidate",
        email="candidate@vacancy-team.ru",
        role="candidate",
    )
    created = client.post("/api/v1/employer/vacancies", headers=first, json=_payload())
    vacancy_id = created.json()["id"]

    assert client.get(f"/api/v1/employer/vacancies/{vacancy_id}", headers=second).status_code == 404
    assert client.patch(
        f"/api/v1/employer/vacancies/{vacancy_id}",
        headers=second,
        json={"title": "No access"},
    ).status_code == 404
    assert client.get("/api/v1/employer/vacancies", headers=candidate).status_code == 403
    assert client.post("/api/v1/employer/vacancies", headers=candidate, json=_payload()).status_code == 403
