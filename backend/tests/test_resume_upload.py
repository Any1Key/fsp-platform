from datetime import UTC, datetime, timedelta

import jwt
from sqlalchemy import create_engine, text

from app import main
from app import resume as resume_module
from app.resume_parser import parse_resume_pdf, parse_resume_text


def _token(private_key, settings, *, email="candidate@team.ru", role="candidate", **overrides):
    now = datetime.now(UTC)
    claims = {
        "iss": settings.keycloak_issuer,
        "aud": settings.keycloak_client_id,
        "sub": "kc-candidate-1",
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


def _resume_file(filename="resume.pdf", body=b"%PDF-1.7\nsynthetic resume\n", content_type="application/pdf"):
    return {"resume": (filename, body, content_type)}


def _text_pdf(*lines: str) -> bytes:
    stream = "BT /F1 12 Tf 72 720 Td " + " ".join(
        f"({line}) Tj 0 -18 Td" for line in lines
    ) + " ET"
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 5 0 R >> >> /Contents 4 0 R >>",
        f"<< /Length {len(stream.encode())} >>\nstream\n{stream}\nendstream".encode(),
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    pdf = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for index, obj in enumerate(objects, 1):
        offsets.append(len(pdf))
        pdf += f"{index} 0 obj\n".encode() + obj + b"\nendobj\n"
    xref = len(pdf)
    pdf += f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n".encode()
    for offset in offsets[1:]:
        pdf += f"{offset:010d} 00000 n \n".encode()
    pdf += f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode()
    return bytes(pdf)


def test_candidate_can_upload_and_read_safe_resume_metadata(auth_context, monkeypatch, tmp_path):
    client, private_key, settings = auth_context
    private_settings = settings.model_copy(update={"private_storage_dir": str(tmp_path / "private")})
    monkeypatch.setattr(main, "get_settings", lambda: private_settings)
    headers = _headers(private_key, private_settings)

    initial = client.get("/api/v1/candidate/resume", headers=headers)
    assert initial.status_code == 200
    assert initial.json() == {"document": None, "extraction": None}

    blocked = client.post(
        "/api/v1/candidate/resume", headers=headers, files=_resume_file()
    )
    assert blocked.status_code == 409
    assert blocked.json()["error"]["code"] == "PROCESSING_CONSENT_REQUIRED"

    _grant_processing_consent(client, headers)
    uploaded = client.post(
        "/api/v1/candidate/resume",
        headers=headers,
        files=_resume_file("../resume-final.pdf"),
    )
    assert uploaded.status_code == 201
    document = uploaded.json()["document"]
    assert document["original_filename"] == "resume-final.pdf"
    assert document["content_type"] == "application/pdf"
    assert document["status"] == "uploaded"
    assert "storage_key" not in document
    assert "sha256" not in document
    assert uploaded.json()["extraction"]["status"] == "unsupported"
    assert uploaded.json()["extraction"]["text_available"] is False

    stored_files = list((tmp_path / "private").glob("*.pdf"))
    assert len(stored_files) == 1
    assert stored_files[0].read_bytes() == b"%PDF-1.7\nsynthetic resume\n"
    assert stored_files[0].stat().st_mode & 0o777 == 0o600

    reloaded = client.get("/api/v1/candidate/resume", headers=headers)
    assert reloaded.status_code == 200
    assert reloaded.json()["document"]["id"] == document["id"]


def test_resume_validation_and_role_boundary_leave_no_partial_file(auth_context, monkeypatch, tmp_path):
    client, private_key, settings = auth_context
    private_settings = settings.model_copy(
        update={"private_storage_dir": str(tmp_path / "private"), "resume_max_bytes": 8}
    )
    monkeypatch.setattr(main, "get_settings", lambda: private_settings)
    headers = _headers(private_key, private_settings)
    _grant_processing_consent(client, headers)

    invalid_uploads = (
        ("resume.txt", b"%PDF-1.7", "application/pdf", "RESUME_INVALID_FILENAME"),
        ("resume.pdf", b"%PDF-1.7", "text/plain", "RESUME_INVALID_TYPE"),
        ("resume.pdf", b"not-pdf", "application/pdf", "RESUME_INVALID_PDF"),
        ("resume.pdf", b"%PDF-1.7-too-large", "application/pdf", "RESUME_TOO_LARGE"),
    )
    for filename, body, content_type, code in invalid_uploads:
        response = client.post(
            "/api/v1/candidate/resume",
            headers=headers,
            files=_resume_file(filename, body, content_type),
        )
        assert response.status_code == 422
        assert response.json()["error"]["code"] == code

    assert not (tmp_path / "private").exists()
    assert client.get("/api/v1/candidate/resume", headers=headers).json() == {
        "document": None,
        "extraction": None,
    }

    employer_headers = _headers(
        private_key,
        private_settings,
        sub="kc-resume-employer",
        email="employer@company.ru",
        role="employer",
    )
    for method in ("get", "post"):
        response = getattr(client, method)(
            "/api/v1/candidate/resume",
            headers=employer_headers,
            **({"files": _resume_file()} if method == "post" else {}),
        )
        assert response.status_code == 403
        assert response.json()["error"]["code"] == "ROLE_REQUIRED"


def test_resume_replacement_is_self_scoped_and_audited(auth_context, monkeypatch, tmp_path):
    client, private_key, settings = auth_context
    private_settings = settings.model_copy(update={"private_storage_dir": str(tmp_path / "private")})
    monkeypatch.setattr(main, "get_settings", lambda: private_settings)
    headers = _headers(private_key, private_settings)
    _grant_processing_consent(client, headers)

    first = client.post(
        "/api/v1/candidate/resume",
        headers=headers,
        files=_resume_file(body=b"%PDF-1.7\nfirst"),
    )
    second = client.post(
        "/api/v1/candidate/resume",
        headers=headers,
        files=_resume_file("resume-v2.pdf", b"%PDF-1.7\nsecond"),
    )
    assert first.status_code == second.status_code == 201
    assert first.json()["document"]["id"] != second.json()["document"]["id"]
    assert second.json()["document"]["original_filename"] == "resume-v2.pdf"
    assert len(list((tmp_path / "private").glob("*.pdf"))) == 2

    engine = create_engine(private_settings.database_url)
    try:
        with engine.connect() as connection:
            rows = connection.execute(
                text("SELECT id, status FROM resume_document ORDER BY uploaded_at, id")
            ).all()
            audit = connection.execute(
                text(
                    "SELECT event_type, details FROM audit_event "
                    "WHERE event_type LIKE 'resume_document_%'"
                )
            ).all()
    finally:
        engine.dispose()
    statuses = {row[0]: row[1] for row in rows}
    assert statuses[first.json()["document"]["id"]] == "replaced"
    assert statuses[second.json()["document"]["id"]] == "uploaded"
    assert [event[0] for event in audit].count("resume_document_uploaded") == 2
    assert [event[0] for event in audit].count("resume_document_replaced") == 1
    assert all("resume-v2" not in event[1] for event in audit)
    assert all("candidate@team.ru" not in event[1] for event in audit)

    other_headers = _headers(
        private_key,
        private_settings,
        sub="kc-other-resume-candidate",
        email="other@team.ru",
    )
    other_status = client.get("/api/v1/candidate/resume", headers=other_headers)
    assert other_status.status_code == 200
    assert other_status.json() == {"document": None, "extraction": None}


def test_parser_returns_declared_fields_with_provenance():
    parsed = parse_resume_text(
        """Alex Ivanov
Backend Engineer
alex@example.com +7 900 123-45-67
Grade: Middle

Skills
Python, FastAPI, PostgreSQL, Docker

Experience
Backend Engineer at Acme | 2022-03 - present

Soft Skills
Communication, mentoring
"""
    )
    fields = parsed["fields"]
    assert fields["full_name"]["value"] == "Alex Ivanov"
    assert fields["headline"]["value"] == "Backend Engineer"
    assert fields["declared_grade"]["value"] == "Middle"
    assert {item["value"] for item in fields["skills"]} == {"Python", "FastAPI", "PostgreSQL", "Docker"}
    assert fields["experience"][0]["company"] == "Acme"
    assert fields["experience"][0]["ended_on"] == "present"
    assert fields["contacts"]["emails"] == ["alex@example.com"]
    assert fields["soft_skills"][0]["value"] == "communication"


def test_parser_extracts_text_from_pdf_bytes():
    parsed = parse_resume_pdf(
        _text_pdf(
            "Alex Ivanov",
            "Backend Engineer",
            "alex@example.com",
            "Skills",
            "Python, FastAPI",
        )
    )
    assert parsed["text_available"] is True
    assert parsed["fields"]["full_name"]["value"] == "Alex Ivanov"
    assert {item["value"] for item in parsed["fields"]["skills"]} == {"Python", "FastAPI"}


def test_resume_review_is_explicit_and_profile_scoped(auth_context, monkeypatch, tmp_path):
    client, private_key, settings = auth_context
    private_settings = settings.model_copy(update={"private_storage_dir": str(tmp_path / "private")})
    monkeypatch.setattr(main, "get_settings", lambda: private_settings)
    headers = _headers(private_key, private_settings)
    _grant_processing_consent(client, headers)
    parsed = parse_resume_text("Alex Ivanov\nBackend Engineer\nalex@example.com\nSkills\nPython")
    monkeypatch.setattr(resume_module, "parse_resume_pdf", lambda content: parsed)

    uploaded = client.post(
        "/api/v1/candidate/resume", headers=headers, files=_resume_file()
    )
    assert uploaded.status_code == 201
    document_id = uploaded.json()["document"]["id"]
    extraction = uploaded.json()["extraction"]
    assert extraction["status"] == "needs_review"
    assert extraction["fields"]["full_name"]["value"] == "Alex Ivanov"
    assert client.get("/api/v1/candidate/profile", headers=headers).json()["display_name"] is None

    rejected = client.patch(
        f"/api/v1/candidate/resume/{document_id}/review",
        headers=headers,
        json={"accepted": False},
    )
    assert rejected.status_code == 200
    assert rejected.json()["extraction"]["status"] == "rejected"
    assert client.get("/api/v1/candidate/profile", headers=headers).json()["display_name"] is None

    uploaded_again = client.post(
        "/api/v1/candidate/resume", headers=headers, files=_resume_file("second.pdf")
    )
    second_id = uploaded_again.json()["document"]["id"]
    accepted = client.patch(
        f"/api/v1/candidate/resume/{second_id}/review",
        headers=headers,
        json={
            "accepted": True,
            "display_name": "Alex I.",
            "headline": "Backend Engineer",
            "summary": "Reviewed from resume",
            "skills": ["Python"],
            "experience": [],
        },
    )
    assert accepted.status_code == 200
    assert accepted.json()["extraction"]["status"] == "accepted"
    profile = client.get("/api/v1/candidate/profile", headers=headers).json()
    assert profile["display_name"] == "Alex I."
    assert profile["skills"] == ["Python"]
    assert profile["summary"] == "Reviewed from resume"
    assert "email" not in profile


def test_resume_review_cannot_cross_candidate_or_employer_boundary(auth_context, monkeypatch, tmp_path):
    client, private_key, settings = auth_context
    private_settings = settings.model_copy(update={"private_storage_dir": str(tmp_path / "private")})
    monkeypatch.setattr(main, "get_settings", lambda: private_settings)
    monkeypatch.setattr(resume_module, "parse_resume_pdf", lambda content: parse_resume_text("Alex"))
    candidate_headers = _headers(private_key, private_settings)
    _grant_processing_consent(client, candidate_headers)
    uploaded = client.post("/api/v1/candidate/resume", headers=candidate_headers, files=_resume_file())
    document_id = uploaded.json()["document"]["id"]
    other_headers = _headers(private_key, private_settings, sub="kc-other-resume-review", email="other@team.ru")
    other_review = client.patch(
        f"/api/v1/candidate/resume/{document_id}/review",
        headers=other_headers,
        json={"accepted": True, "display_name": "Nope"},
    )
    assert other_review.status_code == 404
    employer_headers = _headers(
        private_key, private_settings, sub="kc-resume-review-employer", email="employer@company.ru", role="employer"
    )
    employer_review = client.patch(
        f"/api/v1/candidate/resume/{document_id}/review",
        headers=employer_headers,
        json={"accepted": False},
    )
    assert employer_review.status_code == 403
