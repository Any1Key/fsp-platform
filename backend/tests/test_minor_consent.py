from datetime import UTC, datetime, timedelta

import jwt
from sqlalchemy import create_engine, text

from app import main


def _token(private_key, settings, *, email="candidate@team.ru", role="candidate", **overrides):
    now = datetime.now(UTC)
    claims = {
        "iss": settings.keycloak_issuer,
        "aud": settings.keycloak_client_id,
        "sub": "kc-minor-candidate",
        "email": email,
        "email_verified": True,
        "realm_access": {"roles": [role]},
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=5)).timestamp()),
    }
    claims.update(overrides)
    return jwt.encode(claims, private_key, algorithm="RS256", headers={"kid": "static"})


def _headers(private_key, settings, **overrides):
    return {"Authorization": f"Bearer {_token(private_key, settings, **overrides)}"}


def _grant_processing_consent(client, headers):
    response = client.patch(
        "/api/v1/candidate/privacy",
        headers=headers,
        json={"processing_consent": True},
    )
    assert response.status_code == 200


def _set_minor_dob(client, headers):
    response = client.patch(
        "/api/v1/candidate/protected-profile",
        headers=headers,
        json={"date_of_birth": "2010-10-07"},
    )
    assert response.status_code == 200
    assert response.json()["minor_state"] == "minor"


def _pdf_file(name="guardian-consent.pdf", body=b"%PDF-1.7\nsynthetic consent\n"):
    return {"document": (name, body, "application/pdf")}


def test_minor_can_upload_private_document_and_publication_requires_it(auth_context, monkeypatch, tmp_path):
    client, private_key, settings = auth_context
    private_settings = settings.model_copy(update={"private_storage_dir": str(tmp_path / "private")})
    monkeypatch.setattr(main, "get_settings", lambda: private_settings)
    headers = _headers(private_key, private_settings)
    _grant_processing_consent(client, headers)
    _set_minor_dob(client, headers)

    initial = client.get("/api/v1/candidate/minor-consent-document", headers=headers)
    assert initial.status_code == 200
    assert initial.json()["required"] is True
    assert initial.json()["document"] is None

    blocked_publication = client.patch(
        "/api/v1/candidate/privacy",
        headers=headers,
        json={"publication_consent": True},
    )
    assert blocked_publication.status_code == 409
    assert blocked_publication.json()["error"]["code"] == "MINOR_CONSENT_DOCUMENT_REQUIRED"

    uploaded = client.post(
        "/api/v1/candidate/minor-consent-document",
        headers=headers,
        files=_pdf_file(),
    )
    assert uploaded.status_code == 201
    document = uploaded.json()["document"]
    assert document["original_filename"] == "guardian-consent.pdf"
    assert document["status"] == "submitted"
    assert document["content_type"] == "application/pdf"
    assert "storage_key" not in document
    assert "sha256" not in document

    stored_files = list((tmp_path / "private").glob("*.pdf"))
    assert len(stored_files) == 1
    assert stored_files[0].read_bytes() == b"%PDF-1.7\nsynthetic consent\n"
    assert stored_files[0].stat().st_mode & 0o777 == 0o600

    published = client.patch(
        "/api/v1/candidate/privacy",
        headers=headers,
        json={"publication_consent": True, "discoverable": True},
    )
    assert published.status_code == 200
    assert published.json()["publication_consent"] is True
    assert published.json()["discoverable"] is True


def test_upload_validates_consent_minor_state_and_pdf_without_partial_storage(
    auth_context, monkeypatch, tmp_path
):
    client, private_key, settings = auth_context
    private_settings = settings.model_copy(
        update={"private_storage_dir": str(tmp_path / "private"), "minor_consent_document_max_bytes": 8}
    )
    monkeypatch.setattr(main, "get_settings", lambda: private_settings)
    headers = _headers(private_key, private_settings)

    no_dob = client.post(
        "/api/v1/candidate/minor-consent-document", headers=headers, files=_pdf_file()
    )
    assert no_dob.status_code == 409
    assert no_dob.json()["error"]["code"] == "MINOR_DOCUMENT_ONLY_FOR_MINOR"

    _grant_processing_consent(client, headers)
    _set_minor_dob(client, headers)
    invalid_type = client.post(
        "/api/v1/candidate/minor-consent-document",
        headers=headers,
        files={"document": ("guardian.pdf", b"%PDF-1.7", "text/plain")},
    )
    assert invalid_type.status_code == 422
    assert invalid_type.json()["error"]["code"] == "MINOR_DOCUMENT_INVALID_TYPE"

    oversized = client.post(
        "/api/v1/candidate/minor-consent-document",
        headers=headers,
        files=_pdf_file(body=b"%PDF-1.7-too-large"),
    )
    assert oversized.status_code == 422
    assert oversized.json()["error"]["code"] == "MINOR_DOCUMENT_TOO_LARGE"

    bad_signature = client.post(
        "/api/v1/candidate/minor-consent-document",
        headers=headers,
        files=_pdf_file(body=b"not-pdf"),
    )
    assert bad_signature.status_code == 422
    assert bad_signature.json()["error"]["code"] == "MINOR_DOCUMENT_INVALID_PDF"
    assert not (tmp_path / "private").exists()


def test_upload_replaces_current_document_and_is_self_scoped(auth_context, monkeypatch, tmp_path):
    client, private_key, settings = auth_context
    private_settings = settings.model_copy(update={"private_storage_dir": str(tmp_path / "private")})
    monkeypatch.setattr(main, "get_settings", lambda: private_settings)
    candidate_headers = _headers(private_key, private_settings)
    _grant_processing_consent(client, candidate_headers)
    _set_minor_dob(client, candidate_headers)

    first = client.post(
        "/api/v1/candidate/minor-consent-document",
        headers=candidate_headers,
        files=_pdf_file(body=b"%PDF-1.7\nfirst"),
    )
    first_storage_file = next((tmp_path / "private").glob("*.pdf"))
    second = client.post(
        "/api/v1/candidate/minor-consent-document",
        headers=candidate_headers,
        files=_pdf_file("guardian-consent-v2.pdf", b"%PDF-1.7\nsecond"),
    )
    assert first.status_code == second.status_code == 201
    assert first.json()["document"]["id"] != second.json()["document"]["id"]
    assert second.json()["document"]["original_filename"] == "guardian-consent-v2.pdf"
    assert not first_storage_file.exists()
    second_storage_files = list((tmp_path / "private").glob("*.pdf"))
    assert len(second_storage_files) == 1
    assert second_storage_files[0].read_bytes() == b"%PDF-1.7\nsecond"

    engine = create_engine(private_settings.database_url)
    try:
        with engine.connect() as connection:
            rows = connection.execute(
                text(
                    "SELECT id, status FROM minor_consent_document "
                    "ORDER BY uploaded_at, id"
                )
            ).all()
            audit = connection.execute(
                text(
                    "SELECT event_type, details FROM audit_event "
                    "WHERE event_type = 'minor_consent_document_uploaded'"
                )
            ).all()
    finally:
        engine.dispose()
    statuses = {row[0]: row[1] for row in rows}
    assert statuses[first.json()["document"]["id"]] == "replaced"
    assert statuses[second.json()["document"]["id"]] == "submitted"
    assert len(audit) == 2
    assert all("guardian-consent" not in event[1] for event in audit)
    assert all("candidate@team.ru" not in event[1] for event in audit)

    other_headers = _headers(
        private_key,
        private_settings,
        sub="kc-other-minor-candidate",
        email="other@team.ru",
    )
    other_status = client.get(
        "/api/v1/candidate/minor-consent-document", headers=other_headers
    )
    assert other_status.status_code == 200
    assert other_status.json()["document"] is None

    employer_headers = _headers(
        private_key,
        private_settings,
        sub="kc-minor-employer",
        email="employer@company.ru",
        role="employer",
    )
    for method in ("get", "post"):
        response = getattr(client, method)(
            "/api/v1/candidate/minor-consent-document",
            headers=employer_headers,
            **({"files": _pdf_file()} if method == "post" else {}),
        )
        assert response.status_code == 403
        assert response.json()["error"]["code"] == "ROLE_REQUIRED"


def test_candidate_can_withdraw_minor_document_and_publication_is_revoked(
    auth_context, monkeypatch, tmp_path
):
    client, private_key, settings = auth_context
    private_settings = settings.model_copy(update={"private_storage_dir": str(tmp_path / "private")})
    monkeypatch.setattr(main, "get_settings", lambda: private_settings)
    headers = _headers(private_key, private_settings)
    _grant_processing_consent(client, headers)
    _set_minor_dob(client, headers)

    uploaded = client.post(
        "/api/v1/candidate/minor-consent-document",
        headers=headers,
        files=_pdf_file(body=b"%PDF-1.7\nwithdraw-me"),
    )
    assert uploaded.status_code == 201
    assert len(list((tmp_path / "private").glob("*.pdf"))) == 1

    published = client.patch(
        "/api/v1/candidate/privacy",
        headers=headers,
        json={"publication_consent": True, "discoverable": True},
    )
    assert published.status_code == 200

    withdrawn = client.delete(
        "/api/v1/candidate/minor-consent-document", headers=headers
    )
    assert withdrawn.status_code == 204
    assert withdrawn.content == b""
    assert not list((tmp_path / "private").glob("*.pdf"))

    state = client.get("/api/v1/candidate/minor-consent-document", headers=headers)
    assert state.status_code == 200
    assert state.json()["required"] is True
    assert state.json()["document"] is None

    privacy = client.get("/api/v1/candidate/privacy", headers=headers)
    assert privacy.status_code == 200
    assert privacy.json()["publication_consent"] is False
    assert privacy.json()["discoverable"] is False

    engine = create_engine(private_settings.database_url)
    try:
        with engine.connect() as connection:
            document = connection.execute(
                text("SELECT status, storage_key FROM minor_consent_document")
            ).one()
            audit = connection.execute(
                text(
                    "SELECT event_type, details FROM audit_event "
                    "WHERE event_type = 'minor_consent_document_deleted'"
                )
            ).all()
    finally:
        engine.dispose()
    assert document[0] == "withdrawn"
    assert document[1].endswith(".pdf")
    assert len(audit) == 1
    assert "withdraw-me" not in audit[0][1]
    assert "sha256" not in audit[0][1]

    # Repeating the candidate-owned withdrawal is idempotent and does not
    # create a second audit event for an already withdrawn document.
    repeated = client.delete("/api/v1/candidate/minor-consent-document", headers=headers)
    assert repeated.status_code == 204

    employer_headers = _headers(
        private_key,
        private_settings,
        sub="kc-minor-withdraw-employer",
        email="employer-withdraw@company.ru",
        role="employer",
    )
    forbidden = client.delete(
        "/api/v1/candidate/minor-consent-document", headers=employer_headers
    )
    assert forbidden.status_code == 403
    assert forbidden.json()["error"]["code"] == "ROLE_REQUIRED"


def test_becoming_minor_revokes_existing_publication_until_document_is_submitted(
    auth_context, monkeypatch, tmp_path
):
    client, private_key, settings = auth_context
    private_settings = settings.model_copy(update={"private_storage_dir": str(tmp_path / "private")})
    monkeypatch.setattr(main, "get_settings", lambda: private_settings)
    headers = _headers(private_key, private_settings)
    _grant_processing_consent(client, headers)
    adult = client.patch(
        "/api/v1/candidate/protected-profile",
        headers=headers,
        json={"date_of_birth": "1990-10-07"},
    )
    assert adult.status_code == 200
    published = client.patch(
        "/api/v1/candidate/privacy",
        headers=headers,
        json={"publication_consent": True, "discoverable": True},
    )
    assert published.status_code == 200

    minor = client.patch(
        "/api/v1/candidate/protected-profile",
        headers=headers,
        json={"date_of_birth": "2010-10-07"},
    )
    assert minor.status_code == 200
    privacy = client.get("/api/v1/candidate/privacy", headers=headers)
    assert privacy.status_code == 200
    assert privacy.json()["publication_consent"] is False
    assert privacy.json()["discoverable"] is False
