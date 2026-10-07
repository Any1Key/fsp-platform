from uuid import uuid4

from sqlalchemy import create_engine, text
from test_employer_tasks import _content, _employer_task_stage
from test_invitations import _candidate, _employer, _offer


def _published_task(client, employer_headers):
    stage_id = _employer_task_stage(client, employer_headers)
    created = client.post(
        "/api/v1/employer/tasks",
        headers=employer_headers,
        json={**_content("Bounded retry assignment"), "pipeline_stage_id": stage_id},
    )
    assert created.status_code == 201, created.text
    published = client.post(
        f"/api/v1/employer/tasks/{created.json()['id']}/publish",
        headers=employer_headers,
    )
    assert published.status_code == 200, published.text
    return created.json()["id"], published.json()["current_version"]["id"]


def _matched_task(auth_context):
    client, private_key, settings = auth_context
    employer = _employer(client, private_key, settings, sub=f"assignment-employer-{uuid4().hex}")
    task_id, version_id = _published_task(client, employer)
    candidate, candidate_id = _candidate(
        client,
        private_key,
        settings,
        sub=f"assignment-candidate-{uuid4().hex}",
    )
    invitation = client.post(
        "/api/v1/employer/invitations",
        headers=employer,
        json=_offer(candidate_id),
    )
    assert invitation.status_code == 201, invitation.text
    before_match = client.get("/api/v1/candidate/task-assignments", headers=candidate)
    assert before_match.status_code == 200
    assert before_match.json() == []
    accepted = client.post(
        f"/api/v1/candidate/invitations/{invitation.json()['id']}/respond",
        headers=candidate,
        json={"action": "accepted"},
    )
    assert accepted.status_code == 200, accepted.text
    assignments = client.get("/api/v1/candidate/task-assignments", headers=candidate)
    assert assignments.status_code == 200, assignments.text
    assert len(assignments.json()) == 1
    return client, private_key, settings, candidate, employer, task_id, version_id, assignments.json()[0]


def test_match_assigns_published_version_and_candidate_can_submit_history(auth_context):
    client, _private_key, settings, candidate, _employer, task_id, version_id, assignment = _matched_task(
        auth_context
    )
    assert assignment["task_id"] == task_id
    assert assignment["task_version_id"] == version_id
    assert assignment["status"] == "assigned"
    assert assignment["stage_title"] == "Backend exercise"
    assert assignment["task"]["instructions"]
    assert "rubric" not in assignment["task"]
    assert assignment["submissions"] == []

    first = client.post(
        f"/api/v1/candidate/task-assignments/{assignment['id']}/submissions",
        headers=candidate,
        json={"response_text": "The retry budget is bounded and the final failure is observable."},
    )
    assert first.status_code == 201, first.text
    assert first.json()["status"] == "submitted"
    assert first.json()["submissions"][0]["attempt_number"] == 1

    second = client.post(
        f"/api/v1/candidate/task-assignments/{assignment['id']}/submissions",
        headers=candidate,
        json={"response_text": "Revision: use exponential backoff, a hard cap, and metrics."},
    )
    assert second.status_code == 201, second.text
    assert [item["attempt_number"] for item in second.json()["submissions"]] == [1, 2]
    assert second.json()["submissions"][0]["response_text"].startswith("The retry")

    engine = create_engine(settings.database_url)
    try:
        with engine.connect() as connection:
            assert connection.execute(
                text("SELECT COUNT(*) FROM task_assignment WHERE task_id = :task_id"),
                {"task_id": task_id},
            ).scalar_one() == 1
            assert connection.execute(
                text("SELECT COUNT(*) FROM task_submission WHERE assignment_id = :assignment_id"),
                {"assignment_id": assignment["id"]},
            ).scalar_one() == 2
    finally:
        engine.dispose()


def test_assignment_preserves_version_and_is_scoped_to_matched_candidate(auth_context):
    client, private_key, settings, candidate, employer, task_id, version_id, assignment = _matched_task(
        auth_context
    )
    next_version = client.post(
        f"/api/v1/employer/tasks/{task_id}/versions",
        headers=employer,
        json=_content("Bounded retry assignment v2"),
    )
    assert next_version.status_code == 200, next_version.text
    published_v2 = client.post(
        f"/api/v1/employer/tasks/{task_id}/publish", headers=employer
    )
    assert published_v2.status_code == 200, published_v2.text

    refreshed = client.get("/api/v1/candidate/task-assignments", headers=candidate)
    assert refreshed.status_code == 200
    assert refreshed.json()[0]["task_version_id"] == version_id
    assert refreshed.json()[0]["task"]["title"] == "Bounded retry assignment"

    outsider, _ = _candidate(
        client,
        private_key,
        settings,
        sub=f"assignment-outsider-{uuid4().hex}",
        verified=False,
    )
    assert client.get("/api/v1/candidate/task-assignments", headers=outsider).json() == []
    denied = client.post(
        f"/api/v1/candidate/task-assignments/{assignment['id']}/submissions",
        headers=outsider,
        json={"response_text": "unauthorized"},
    )
    assert denied.status_code == 404
    assert denied.json()["error"]["code"] == "TASK_ASSIGNMENT_NOT_FOUND"

    employer_denied = client.get("/api/v1/candidate/task-assignments", headers=employer)
    assert employer_denied.status_code == 403
    assert employer_denied.json()["error"]["code"] == "ROLE_REQUIRED"


def test_expired_assignment_cannot_accept_a_submission(auth_context):
    client, _private_key, settings, candidate, _employer_headers, _task_id, _version_id, assignment = _matched_task(
        auth_context
    )
    engine = create_engine(settings.database_url)
    try:
        with engine.begin() as connection:
            connection.execute(
                text("UPDATE task_assignment SET due_at = CURRENT_TIMESTAMP WHERE id = :id"),
                {"id": assignment["id"]},
            )
    finally:
        engine.dispose()

    expired = client.post(
        f"/api/v1/candidate/task-assignments/{assignment['id']}/submissions",
        headers=candidate,
        json={"response_text": "too late"},
    )
    assert expired.status_code == 409
    assert expired.json()["error"]["code"] == "TASK_ASSIGNMENT_DEADLINE_PASSED"
    assert client.get("/api/v1/candidate/task-assignments", headers=candidate).json()[0]["status"] == "expired"
