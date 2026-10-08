from datetime import UTC, datetime, timedelta
from uuid import uuid4

from sqlalchemy import create_engine, text
from test_invitations import _candidate, _employer, _offer


def _match(auth_context):
    client, private_key, settings = auth_context
    candidate, candidate_id = _candidate(
        client, private_key, settings, sub=f"challenge-candidate-{uuid4().hex}"
    )
    employer = _employer(client, private_key, settings, sub=f"challenge-employer-{uuid4().hex}")
    invitation = client.post(
        "/api/v1/employer/invitations", headers=employer, json=_offer(candidate_id)
    )
    assert invitation.status_code == 201, invitation.text
    match_id = invitation.json().get("match_id")
    assert match_id is None
    accepted = client.post(
        f"/api/v1/candidate/invitations/{invitation.json()['id']}/respond",
        headers=candidate,
        json={"action": "accepted"},
    )
    assert accepted.status_code == 200, accepted.text
    return client, private_key, settings, candidate, employer, accepted.json()["match_id"]


def _challenge(match_id: str, **changes):
    payload = {
        "match_id": match_id,
        "title": "Weekly reliability pulse",
        "instructions": "Describe one production failure and the smallest safe mitigation.",
        "target_skill": "python",
        "estimated_minutes": 10,
        "cadence_days": 7,
        "rubric": [
            {"name": "Diagnosis", "points": 60, "description": "Identifies the failure."},
            {"name": "Mitigation", "points": 40, "description": "Keeps the fix bounded."},
        ],
    }
    payload.update(changes)
    return payload


def test_periodic_challenge_runs_end_to_end_and_schedules_next_cycle(auth_context):
    client, _private_key, settings, candidate, employer, match_id = _match(auth_context)
    before = client.get("/api/v1/candidate/dashboard", headers=candidate)
    assert before.status_code == 200

    created = client.post(
        "/api/v1/employer/challenges",
        headers=employer,
        json=_challenge(match_id),
    )
    assert created.status_code == 201, created.text
    assignment = created.json()
    assert assignment["cycle_number"] == 1
    assert assignment["status"] == "assigned"
    assert assignment["challenge"]["estimated_minutes"] == 10
    assert "rubric" not in assignment["challenge"]

    candidate_list = client.get("/api/v1/candidate/challenges", headers=candidate)
    assert candidate_list.status_code == 200
    assert len(candidate_list.json()) == 1
    assert candidate_list.json()[0]["result"] is None

    submitted = client.post(
        f"/api/v1/candidate/challenges/{assignment['id']}/submissions",
        headers=candidate,
        json={"response_text": "Bound the retry budget, emit an alert, and roll back safely."},
    )
    assert submitted.status_code == 201, submitted.text
    assert submitted.json()["status"] == "submitted"

    invalid = client.put(
        f"/api/v1/employer/challenges/{assignment['id']}/result",
        headers=employer,
        json={
            "rubric_scores": [{"name": "Diagnosis", "points_awarded": 61}],
            "release_to_candidate": True,
        },
    )
    assert invalid.status_code == 422
    assert invalid.json()["error"]["code"] == "CHALLENGE_RUBRIC_MISMATCH"

    released = client.put(
        f"/api/v1/employer/challenges/{assignment['id']}/result",
        headers=employer,
        json={
            "rubric_scores": [
                {"name": "Diagnosis", "points_awarded": 55},
                {"name": "Mitigation", "points_awarded": 35},
            ],
            "feedback": "Clear operational limits and a safe rollback.",
            "release_to_candidate": True,
        },
    )
    assert released.status_code == 200, released.text
    assert released.json()["result"]["score"] == 90
    assert released.json()["result"]["rubric_scores"]
    assert released.json()["result"]["evidence_fresh_until"]
    assert released.json()["result"]["freshness"]["status"] == "fresh"
    assert released.json()["result"]["freshness"]["days_remaining"] >= 6

    after = client.get("/api/v1/candidate/dashboard", headers=candidate)
    assert after.status_code == 200
    assert after.json() == before.json()

    candidate_cycles = client.get("/api/v1/candidate/challenges", headers=candidate).json()
    assert [item["cycle_number"] for item in candidate_cycles] == [2, 1]
    assert candidate_cycles[0]["status"] == "scheduled"
    assert candidate_cycles[1]["result"]["score"] == 90
    assert candidate_cycles[1]["result"]["feedback"].startswith("Clear")
    assert "rubric_scores" not in candidate_cycles[1]["result"]
    assert candidate_cycles[1]["result"]["freshness"]["status"] == "fresh"

    scheduled = client.post(
        f"/api/v1/candidate/challenges/{candidate_cycles[0]['id']}/submissions",
        headers=candidate,
        json={"response_text": "Too early"},
    )
    assert scheduled.status_code == 409
    assert scheduled.json()["error"]["code"] == "CHALLENGE_NOT_STARTED"

    employer_cycles = client.get("/api/v1/employer/challenges", headers=employer)
    assert employer_cycles.status_code == 200
    assert len(employer_cycles.json()) == 2
    assert employer_cycles.json()[0]["candidate_display_name"] == "Visible Candidate"

    engine = create_engine(settings.database_url)
    try:
        with engine.connect() as connection:
            assert connection.execute(text("SELECT COUNT(*) FROM challenge_assignment")).scalar_one() == 2
            assert connection.execute(text("SELECT COUNT(*) FROM challenge_result")).scalar_one() == 1
    finally:
        engine.dispose()


def test_evidence_freshness_transitions_to_stale_without_mutating_score_or_dashboard(auth_context):
    client, _private_key, settings, candidate, employer, match_id = _match(auth_context)
    before = client.get("/api/v1/candidate/dashboard", headers=candidate)
    created = client.post("/api/v1/employer/challenges", headers=employer, json=_challenge(match_id))
    assert created.status_code == 201, created.text
    assignment_id = created.json()["id"]
    submitted = client.post(
        f"/api/v1/candidate/challenges/{assignment_id}/submissions",
        headers=candidate,
        json={"response_text": "Bound the retry budget and added a rollback."},
    )
    assert submitted.status_code == 201, submitted.text
    released = client.put(
        f"/api/v1/employer/challenges/{assignment_id}/result",
        headers=employer,
        json={
            "rubric_scores": [
                {"name": "Diagnosis", "points_awarded": 50},
                {"name": "Mitigation", "points_awarded": 30},
            ],
            "release_to_candidate": True,
        },
    )
    assert released.status_code == 200, released.text
    score = released.json()["result"]["score"]

    engine = create_engine(settings.database_url)
    try:
        with engine.begin() as connection:
            connection.execute(
                text("UPDATE challenge_result SET evidence_fresh_until = :expired"),
                {"expired": datetime.now(UTC) + timedelta(days=2)},
            )
    finally:
        engine.dispose()

    candidate_cycles = client.get("/api/v1/candidate/challenges", headers=candidate)
    assert candidate_cycles.status_code == 200, candidate_cycles.text
    result = next(item["result"] for item in candidate_cycles.json() if item["result"] is not None)
    assert result["score"] == score
    assert result["freshness"]["status"] == "expiring"
    assert 1 <= result["freshness"]["days_remaining"] <= 2

    engine = create_engine(settings.database_url)
    try:
        with engine.begin() as connection:
            connection.execute(
                text("UPDATE challenge_result SET evidence_fresh_until = :expired"),
                {"expired": datetime.now(UTC) - timedelta(minutes=1)},
            )
    finally:
        engine.dispose()

    candidate_cycles = client.get("/api/v1/candidate/challenges", headers=candidate)
    assert candidate_cycles.status_code == 200, candidate_cycles.text
    result = next(item["result"] for item in candidate_cycles.json() if item["result"] is not None)
    assert result["score"] == score
    assert result["freshness"] == {
        "status": "stale",
        "days_remaining": 0,
        "evidence_fresh_until": result["evidence_fresh_until"],
    }
    assert client.get("/api/v1/candidate/dashboard", headers=candidate).json() == before.json()


def test_periodic_challenge_is_match_and_role_scoped(auth_context):
    client, private_key, settings, _candidate_headers, employer, match_id = _match(auth_context)
    outsider_candidate, _ = _candidate(
        client, private_key, settings, sub=f"challenge-outsider-candidate-{uuid4().hex}", verified=False
    )
    outsider_employer = _employer(
        client, private_key, settings, sub=f"challenge-outsider-employer-{uuid4().hex}"
    )
    created = client.post(
        "/api/v1/employer/challenges", headers=employer, json=_challenge(match_id)
    )
    assignment_id = created.json()["id"]

    assert client.get("/api/v1/candidate/challenges", headers=outsider_candidate).json() == []
    assert client.get("/api/v1/employer/challenges", headers=outsider_employer).json() == []
    assert client.post(
        f"/api/v1/candidate/challenges/{assignment_id}/submissions",
        headers=outsider_candidate,
        json={"response_text": "not mine"},
    ).status_code == 404
    assert client.put(
        f"/api/v1/employer/challenges/{assignment_id}/result",
        headers=outsider_employer,
        json={
            "rubric_scores": [
                {"name": "Diagnosis", "points_awarded": 1},
                {"name": "Mitigation", "points_awarded": 1},
            ],
            "release_to_candidate": True,
        },
    ).status_code == 404
    assert client.get("/api/v1/candidate/challenges", headers=employer).status_code == 403


def test_periodic_challenge_rejects_invalid_cadence_without_creating_data(auth_context):
    client, _private_key, _settings, _candidate_headers, employer, match_id = _match(auth_context)
    invalid = client.post(
        "/api/v1/employer/challenges",
        headers=employer,
        json=_challenge(match_id, cadence_days=91),
    )
    assert invalid.status_code == 422
    assert invalid.json()["error"]["code"] == "VALIDATION_ERROR"
    assert client.get("/api/v1/employer/challenges", headers=employer).json() == []
