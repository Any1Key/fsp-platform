from uuid import uuid4

from sqlalchemy import create_engine, text
from test_invitations import _candidate, _employer, _headers, _offer


def test_employer_trust_separates_verified_evidence_from_advisory_heuristics(auth_context):
    client, private_key, settings = auth_context
    employer = _headers(
        private_key,
        settings,
        sub=f"trust-signals-{uuid4().hex}",
        role="employer",
    )

    initial = client.get("/api/v1/employer/trust", headers=employer)
    assert initial.status_code == 200
    profile = initial.json()
    assert profile["badge"] == "verified_email"
    assert profile["state"] == "normal"
    assert profile["outbound_used"] == 0
    assert profile["outbound_limit"] == 20
    assert {signal["category"] for signal in profile["signals"]} == {"verified", "heuristic"}
    assert all("@" not in signal["explanation"] for signal in profile["signals"])

    updated = client.patch(
        "/api/v1/employer/company",
        headers=employer,
        json={"name": "Trust Demo", "website": "https://different.example.ru"},
    )
    assert updated.status_code == 200
    after_one_heuristic = client.get("/api/v1/employer/trust", headers=employer).json()
    assert after_one_heuristic["state"] == "normal"
    website_signal = next(
        signal
        for signal in after_one_heuristic["signals"]
        if signal["key"] == "website_consistency"
    )
    assert website_signal["status"] == "attention"


def test_candidate_report_is_scoped_idempotent_and_reviewer_resolvable(auth_context):
    client, private_key, settings = auth_context
    candidate, candidate_id = _candidate(
        client, private_key, settings, sub=f"trust-reporter-{uuid4().hex}"
    )
    employer = _employer(client, private_key, settings, sub=f"trust-owner-{uuid4().hex}")
    invitation = client.post(
        "/api/v1/employer/invitations",
        headers=employer,
        json={**_offer(candidate_id), "offer_description": "Please pay a fee to continue"},
    ).json()
    offer_signal = next(
        signal
        for signal in invitation["employer_trust"]["signals"]
        if signal["key"] == "offer_anomaly"
    )
    assert offer_signal["status"] == "attention"

    report = client.post(
        f"/api/v1/candidate/invitations/{invitation['id']}/report",
        headers=candidate,
        json={"reason": "fee_request", "details": "Synthetic report detail"},
    )
    assert report.status_code == 201
    assert report.json()["status"] == "open"
    repeated = client.post(
        f"/api/v1/candidate/invitations/{invitation['id']}/report",
        headers=candidate,
        json={"reason": "spam"},
    )
    assert repeated.status_code == 201
    assert repeated.json()["id"] == report.json()["id"]

    trust = client.get("/api/v1/employer/trust", headers=employer)
    assert trust.status_code == 200
    assert trust.json()["state"] == "review"
    assert trust.json()["open_report_count"] == 1
    assert trust.json()["outbound_limit"] == 3

    reviewer = _headers(
        private_key,
        settings,
        sub=f"trust-reviewer-{uuid4().hex}",
        role="reviewer",
    )
    queue = client.get("/api/v1/reviewer/trust/reports", headers=reviewer)
    assert queue.status_code == 200
    assert queue.json()[0]["company_name"] == "Northstar Labs"
    assert queue.json()[0]["details"] == "Synthetic report detail"
    assert client.get("/api/v1/reviewer/trust/reports", headers=candidate).status_code == 403

    resolved = client.patch(
        f"/api/v1/reviewer/trust/reports/{report.json()['id']}",
        headers=reviewer,
        json={"status": "closed"},
    )
    assert resolved.status_code == 200
    assert resolved.json()["status"] == "closed"
    assert client.get("/api/v1/employer/trust", headers=employer).json()["state"] == "normal"

    engine = create_engine(settings.database_url)
    with engine.connect() as connection:
        audit_details = connection.execute(
            text("SELECT details FROM audit_event WHERE event_type = 'employer_trust_reported'")
        ).scalar_one()
    engine.dispose()
    assert "Synthetic report detail" not in audit_details
    assert report.json()["id"] in audit_details


def test_open_report_lowers_outbound_limit_without_changing_salary_or_match_rules(auth_context):
    client, private_key, settings = auth_context
    reporter, reporter_id = _candidate(
        client, private_key, settings, sub=f"trust-limit-reporter-{uuid4().hex}"
    )
    employer = _employer(client, private_key, settings, sub=f"trust-limit-owner-{uuid4().hex}")
    first = client.post("/api/v1/employer/invitations", headers=employer, json=_offer(reporter_id))
    assert first.status_code == 201
    assert (
        client.post(
            f"/api/v1/candidate/invitations/{first.json()['id']}/report",
            headers=reporter,
            json={"reason": "fake_vacancy"},
        ).status_code
        == 201
    )

    for index in range(2):
        _, candidate_id = _candidate(
            client, private_key, settings, sub=f"trust-limit-target-{index}-{uuid4().hex}"
        )
        created = client.post(
            "/api/v1/employer/invitations",
            headers=employer,
            json={**_offer(candidate_id), "offer_description": f"Offer {index}"},
        )
        assert created.status_code == 201

    _, fourth_candidate_id = _candidate(
        client, private_key, settings, sub=f"trust-limit-fourth-{uuid4().hex}"
    )
    limited = client.post(
        "/api/v1/employer/invitations",
        headers=employer,
        json={**_offer(fourth_candidate_id), "offer_description": "Offer four"},
    )
    assert limited.status_code == 429
    assert limited.json()["error"]["code"] == "EMPLOYER_INVITATION_RATE_LIMITED"


def test_other_candidate_cannot_report_an_invitation(auth_context):
    client, private_key, settings = auth_context
    _, candidate_id = _candidate(client, private_key, settings, sub=f"trust-target-{uuid4().hex}")
    other_candidate, _ = _candidate(client, private_key, settings, sub=f"trust-other-{uuid4().hex}")
    employer = _employer(client, private_key, settings, sub=f"trust-scope-owner-{uuid4().hex}")
    invitation = client.post(
        "/api/v1/employer/invitations", headers=employer, json=_offer(candidate_id)
    ).json()

    denied = client.post(
        f"/api/v1/candidate/invitations/{invitation['id']}/report",
        headers=other_candidate,
        json={"reason": "spam"},
    )
    assert denied.status_code == 404
    assert denied.json()["error"]["code"] == "INVITATION_NOT_FOUND"
