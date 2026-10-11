from datetime import UTC, datetime, timedelta
from uuid import uuid4

import jwt
import pytest

from app.assessments import (
    AssessmentError,
    AssessmentService,
    _submission_similarity,
    form_assessment_from_descriptions,
    public_attempt,
)


def _valid_followup(item) -> str:
    responses = {
        "api-2": "bounded retry uses backoff and a limit",
        "sql-2": "transaction makes the migration atomic and rollback keeps it reversible",
        "test-2": "find the nondeterministic source and fix the seed for reproducibility",
        "arch-2": "measure the budget and latency at p95 before scaling",
    }
    return responses.get(item.family_id, "the explanation follows the constraint in the task")


def test_forms_are_unique_and_keep_same_competency_shape() -> None:
    service = AssessmentService(now=datetime(2026, 10, 6, tzinfo=UTC))
    first = service.create_attempt("candidate-a", "Backend Engineering", "Middle")
    service.now += timedelta(days=91)
    second = service.create_attempt("candidate-a", "Backend Engineering", "Middle")

    assert first.attempt_id != second.attempt_id
    assert {item.domain for item in first.items} == {item.domain for item in second.items}
    assert {item.artifact for item in first.items}.isdisjoint({item.artifact for item in second.items})
    assert any(a.prompt != b.prompt for a, b in zip(first.items, second.items))


def test_retest_is_locked_and_failed_declared_grade_is_not_downgraded() -> None:
    service = AssessmentService(now=datetime(2026, 10, 6, tzinfo=UTC))
    attempt = service.create_attempt("candidate-b", "Backend Engineering", "Senior")
    result = service.submit(attempt.attempt_id, {item.item_id: 9 for item in attempt.items})

    assert result.grade_state == "not_confirmed"
    assert result.declared_grade == "Senior"
    with pytest.raises(AssessmentError, match="retest_locked"):
        service.create_attempt("candidate-b", "Backend Engineering", "Senior")


def test_failed_declared_grade_offers_one_lower_assessment_without_downgrading() -> None:
    service = AssessmentService(now=datetime(2026, 10, 6, tzinfo=UTC))
    attempt = service.create_attempt("candidate-lower", "Backend Engineering", "Senior")
    result = service.submit(attempt.attempt_id, {item.item_id: 9 for item in attempt.items})

    assert result.declared_grade == "Senior"
    assert result.grade_state == "not_confirmed"
    assert service.grade_offers(result) == [{"grade": "Middle", "reason": "lower_grade_after_unconfirmed_result"}]
    lower = service.create_attempt("candidate-lower", "Backend Engineering", "Middle")
    assert lower.declared_grade == "Middle"


def test_strong_result_offers_one_higher_assessment() -> None:
    service = AssessmentService(now=datetime(2026, 10, 6, tzinfo=UTC))
    attempt = service.create_attempt("candidate-higher", "Backend Engineering", "Junior")
    result = service.submit(attempt.attempt_id, attempt.answer_keys.copy())

    assert result.grade_state == "verified"
    assert service.grade_offers(result) == [{"grade": "Middle", "reason": "higher_grade_after_strong_result"}]
    higher = service.create_attempt("candidate-higher", "Backend Engineering", "Middle")
    assert higher.declared_grade == "Middle"


def test_assessment_formation_uses_several_hiring_descriptions_deterministically() -> None:
    formation = form_assessment_from_descriptions(
        [
            "Backend API engineer: REST endpoints and PostgreSQL",
            "Platform engineer: secure services and automated tests",
        ]
    )

    assert formation.source_count == 2
    assert formation.source_domains == (
        "api_fundamentals",
        "sql_data",
        "testing_debugging",
        "security_operations",
    )
    assert {"api-1", "sql-1", "test-1", "sec-1"}.issubset(formation.family_ids)


def test_progressive_followup_and_integrity_signal_are_advisory() -> None:
    service = AssessmentService(now=datetime(2026, 10, 6, tzinfo=UTC))
    attempt = service.create_attempt("candidate-c", "Backend Engineering", "Middle")
    answers = attempt.answer_keys.copy()
    followups = {item.item_id: _valid_followup(item) for item in attempt.items if item.progressive}
    result = service.submit(attempt.attempt_id, answers, followups, telemetry={"paste_chars": 2000})

    assert result.score > 70
    assert result.grade_state == "verified"
    assert result.integrity_signals == ["large_paste_review"]


def test_rotated_form_normalizes_progressive_followup_weight() -> None:
    # This seed rotates the form to three progressive items. A correct answer
    # and valid rationale for every item must remain a verified result.
    service = AssessmentService(
        now=datetime(2026, 10, 6, tzinfo=UTC),
        seed_factory=lambda: "00000003" + "00" * 12,
    )
    attempt = service.create_attempt("rotated-form", "Backend Engineering", "Middle")
    progressive = [item for item in attempt.items if item.progressive]
    assert len(progressive) == 3

    result = service.submit(
        attempt.attempt_id,
        attempt.answer_keys.copy(),
        {item.item_id: _valid_followup(item) for item in progressive},
    )

    assert result.score == 100
    assert result.grade_state == "verified"


def test_canonical_review_is_delayed_then_released_after_configured_window() -> None:
    started = datetime(2026, 10, 6, tzinfo=UTC)
    service = AssessmentService(now=started, canonical_exposure_window=timedelta(days=7))
    attempt = service.create_attempt("canonical-window", "Backend Engineering", "Middle")
    result = service.submit(
        attempt.attempt_id,
        attempt.answer_keys.copy(),
        {item.item_id: _valid_followup(item) for item in attempt.items if item.progressive},
    )

    delayed = service.canonical_review(result)
    assert delayed is not None
    assert delayed["status"] == "delayed"
    assert delayed["available_at"] == started + timedelta(days=7)
    assert "correct_option" not in delayed
    assert "explanation" not in delayed
    score_before_release = result.score
    assert result.grade_state == "verified"

    service.now = started + timedelta(days=8)
    available = service.canonical_review(result)
    assert available is not None
    assert available["status"] == "available"
    assert len(available["items"]) == len(result.items)
    assert all("correct_option" in item and item["explanation"] for item in available["items"])
    assert result.score == score_before_release
    assert result.grade_state == "verified"
    assert service.public_attempt(result)["canonical_review"] == available


def test_retirement_releases_only_when_every_family_version_is_retired() -> None:
    service = AssessmentService(
        now=datetime(2026, 10, 6, tzinfo=UTC),
        canonical_exposure_window=timedelta(days=90),
    )
    attempt = service.create_attempt("canonical-retirement", "Backend Engineering", "Middle")
    result = service.submit(attempt.attempt_id, attempt.answer_keys.copy())
    families = {(item.family_id, item.family_version) for item in result.items}

    family_id, version = next(iter(families))
    service.retire_family(family_id, version)
    assert service.canonical_review(result)["status"] == "delayed"

    for family_id, version in families:
        service.retire_family(family_id, version)
    available = service.canonical_review(result)
    assert available["status"] == "available"
    assert len(available["items"]) == len(result.items)


def test_hidden_deterministic_checks_score_rationale_without_exposing_rubric(monkeypatch) -> None:
    monkeypatch.setattr("app.assessments.secrets.token_hex", lambda _: "00" * 16)
    service = AssessmentService(now=datetime(2026, 10, 6, tzinfo=UTC))
    valid_attempt = service.create_attempt("hidden-check-valid", "Backend Engineering", "Middle")
    hidden_items = [item for item in valid_attempt.items if item.item_id in valid_attempt.hidden_checks]

    assert hidden_items
    public = public_attempt(valid_attempt)
    assert "hidden_checks" not in public
    assert all("required_concepts" not in item for item in public["items"])

    valid_followups = {item.item_id: _valid_followup(item) for item in valid_attempt.items if item.progressive}
    valid_result = service.submit(
        valid_attempt.attempt_id,
        valid_attempt.answer_keys.copy(),
        valid_followups,
    )
    assert "hidden_check_review" not in valid_result.integrity_signals

    service.now += timedelta(days=91)
    invalid_attempt = service.create_attempt("hidden-check-invalid", "Backend Engineering", "Middle")
    invalid_followups = {
        item.item_id: "I selected this option because it seemed reasonable."
        for item in invalid_attempt.items
        if item.progressive
    }
    invalid_result = service.submit(
        invalid_attempt.attempt_id,
        invalid_attempt.answer_keys.copy(),
        invalid_followups,
    )
    assert invalid_result.score < valid_result.score
    assert invalid_result.grade_state == "verified"
    assert invalid_result.integrity_signals == ["hidden_check_review"]


def test_similarity_signal_is_advisory_and_scoped_to_same_family(monkeypatch) -> None:
    monkeypatch.setattr("app.assessments.secrets.token_hex", lambda _: "00" * 16)
    service = AssessmentService(now=datetime(2026, 10, 6, tzinfo=UTC))
    first = service.create_attempt("similarity-a", "Backend Engineering", "Middle")
    second = service.create_attempt("similarity-b", "Backend Engineering", "Middle")
    shared_families = {
        item.family_id
        for item in first.items
        if item.progressive
    } & {
        item.family_id
        for item in second.items
        if item.progressive
    }
    assert shared_families
    first_item = next(item for item in first.items if item.family_id in shared_families)
    second_item = next(item for item in second.items if item.family_id == first_item.family_id)
    shared_response = "bounded retry uses backoff and a limit for safe recovery"

    first_result = service.submit(
        first.attempt_id,
        first.answer_keys.copy(),
        {first_item.item_id: shared_response},
    )
    second_result = service.submit(
        second.attempt_id,
        second.answer_keys.copy(),
        {second_item.item_id: shared_response},
    )

    assert "cross_submission_similarity_review" not in first_result.integrity_signals
    assert "cross_submission_similarity_review" in second_result.integrity_signals
    assert second_result.score == first_result.score
    assert second_result.grade_state == first_result.grade_state
    assert second_result.integrity_evidence == [
        {
            "signal": "cross_submission_similarity_review",
            "modality": "text",
            "scope": "progressive_response",
            "item_id": second_item.item_id,
            "similarity": 1.0,
        }
    ]
    assert "similarity-a" not in str(second_result.integrity_evidence)
    assert shared_response not in str(second_result.integrity_evidence)
    public = public_attempt(second_result)
    assert public["integrity_evidence"] == second_result.integrity_evidence
    assert "submitted_followups" not in public


def test_similarity_normalizes_code_and_ignores_short_or_dissimilar_text() -> None:
    code_match = _submission_similarity(
        "def total(first, second): # candidate A\n    return first + second + 1",
        "def total(left, right): # candidate B\n    return left + right + 1",
    )

    assert code_match is not None
    assert code_match.modality == "code"
    assert code_match.similarity >= 0.86
    assert _submission_similarity("same words", "same words") is None
    assert (
        _submission_similarity(
            "retry with bounded backoff and a limit",
            "transaction rollback protects the schema migration",
        )
        is None
    )


def _headers(private_key, settings, *, sub: str, role: str = "candidate"):
    now = datetime.now(UTC)
    token = jwt.encode(
        {
            "iss": settings.keycloak_issuer,
            "aud": settings.keycloak_client_id,
            "sub": sub,
            "email": f"{sub}@team.ru",
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


def test_api_does_not_expose_answer_keys_and_scores_submission(auth_context) -> None:
    client, private_key, settings = auth_context
    headers = _headers(private_key, settings, sub=f"api-candidate-{uuid4().hex}")
    response = client.post(
        "/api/v1/assessments/attempts",
        headers=headers,
        json={
            "industry": "IT / Software Development",
            "specialization": "Backend Engineering",
            "declared_grade": "Junior",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["industry"] == "IT / Software Development"
    assert "answer_keys" not in body
    assert "hidden_checks" not in body
    assert all("correct_option" not in item for item in body["items"])

    # The test uses the domain service's private key only to model a completed
    # client submission; the public API never returns it.
    from app.main import assessment_service

    attempt = assessment_service.attempts[body["attempt_id"]]
    submit = client.post(
        f"/api/v1/assessments/attempts/{body['attempt_id']}/submit",
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
    assert submit.status_code == 200
    assert submit.json()["score"] is not None
    assert submit.json()["grade_state"] in {"verified", "not_confirmed"}
    assert "hidden_check_review" not in submit.json()["integrity_signals"]
    assert submit.json()["integrity_evidence"] == []
    assert submit.json()["canonical_review"]["status"] == "delayed"
    assert "correct_option" not in submit.json()["canonical_review"]
    assert "explanation" not in submit.json()["canonical_review"]


def test_api_assessment_is_self_scoped_and_rejects_identity_override(auth_context) -> None:
    client, private_key, settings = auth_context
    candidate_a = f"assessment-a-{uuid4().hex}"
    candidate_b = f"assessment-b-{uuid4().hex}"
    headers_a = _headers(private_key, settings, sub=candidate_a)
    headers_b = _headers(private_key, settings, sub=candidate_b)

    created = client.post(
        "/api/v1/assessments/attempts",
        headers=headers_a,
        json={"specialization": "Backend Engineering", "declared_grade": "Middle"},
    )
    assert created.status_code == 200
    attempt_id = created.json()["attempt_id"]

    override = client.post(
        "/api/v1/assessments/attempts",
        headers=headers_a,
        json={
            "candidate_id": candidate_b,
            "specialization": "Backend Engineering",
            "declared_grade": "Middle",
        },
    )
    assert override.status_code == 422
    assert override.json()["error"]["code"] == "VALIDATION_ERROR"

    for method, url, kwargs in (
        (client.get, f"/api/v1/assessments/attempts/{attempt_id}", {"headers": headers_b}),
        (
            client.post,
            f"/api/v1/assessments/attempts/{attempt_id}/submit",
            {"headers": headers_b, "json": {"answers": {}}},
        ),
    ):
        response = method(url, **kwargs)
        assert response.status_code == 404
        assert response.json()["error"]["code"] == "ASSESSMENT_ATTEMPT_NOT_FOUND"

    employer_headers = _headers(private_key, settings, sub=f"assessment-employer-{uuid4().hex}", role="employer")
    denied = client.get(f"/api/v1/assessments/attempts/{attempt_id}", headers=employer_headers)
    assert denied.status_code == 403
    assert denied.json()["error"]["code"] == "ROLE_REQUIRED"

    anonymous = client.post(
        "/api/v1/assessments/attempts",
        json={"specialization": "Backend Engineering", "declared_grade": "Junior"},
    )
    assert anonymous.status_code == 401
    assert anonymous.json()["error"]["code"] == "AUTHORIZATION_REQUIRED"
