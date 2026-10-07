from uuid import uuid4

from sqlalchemy import create_engine, text
from test_invitations import _employer
from test_task_assignments import _matched_task


def _scores(correctness: int = 60, explanation: int = 30):
    return [
        {"name": "Correctness", "points_awarded": correctness},
        {"name": "Explanation", "points_awarded": explanation},
    ]


def test_employer_grades_submission_and_candidate_sees_only_released_evidence(auth_context):
    client, _private_key, settings, candidate, employer, _task_id, _version_id, assignment = _matched_task(
        auth_context
    )
    dashboard_before = client.get("/api/v1/candidate/dashboard", headers=candidate)
    assert dashboard_before.status_code == 200

    submitted = client.post(
        f"/api/v1/candidate/task-assignments/{assignment['id']}/submissions",
        headers=candidate,
        json={"response_text": "A bounded retry with capped exponential backoff."},
    )
    assert submitted.status_code == 201, submitted.text
    assert submitted.json()["evaluation"] is None

    employer_list = client.get("/api/v1/employer/task-assignments", headers=employer)
    assert employer_list.status_code == 200, employer_list.text
    assert len(employer_list.json()) == 1
    employer_assignment = employer_list.json()[0]
    assert employer_assignment["candidate_display_name"] == "Visible Candidate"
    assert employer_assignment["submissions"][0]["response_text"].startswith("A bounded")
    assert employer_assignment["task"]["rubric"][0]["name"] == "Correctness"

    draft = client.put(
        f"/api/v1/employer/task-assignments/{assignment['id']}/evaluation",
        headers=employer,
        json={
            "rubric_scores": _scores(60, 30),
            "feedback": "Good bounded design; make the cap explicit.",
            "release_to_candidate": False,
        },
    )
    assert draft.status_code == 200, draft.text
    assert draft.json()["evaluation"]["score"] == 90
    assert draft.json()["evaluation"]["status"] == "draft"
    assert client.get("/api/v1/candidate/task-assignments", headers=candidate).json()[0]["evaluation"] is None

    dashboard_after_draft = client.get("/api/v1/candidate/dashboard", headers=candidate)
    assert dashboard_after_draft.json() == dashboard_before.json()

    released = client.put(
        f"/api/v1/employer/task-assignments/{assignment['id']}/evaluation",
        headers=employer,
        json={
            "rubric_scores": _scores(50, 40),
            "feedback": "Strong explanation and clear operational limits.",
            "release_to_candidate": True,
        },
    )
    assert released.status_code == 200, released.text
    assert released.json()["evaluation"]["score"] == 90
    assert released.json()["evaluation"]["status"] == "released"

    candidate_view = client.get("/api/v1/candidate/task-assignments", headers=candidate)
    assert candidate_view.status_code == 200
    evaluation = candidate_view.json()[0]["evaluation"]
    assert evaluation["score"] == 90
    assert evaluation["feedback"].startswith("Strong explanation")
    assert "rubric_scores" not in evaluation
    assert "rubric" not in candidate_view.json()[0]["task"]

    dashboard_after_release = client.get("/api/v1/candidate/dashboard", headers=candidate)
    assert dashboard_after_release.json() == dashboard_before.json()

    engine = create_engine(settings.database_url)
    try:
        with engine.connect() as connection:
            assert connection.execute(
                text("SELECT COUNT(*) FROM employer_evaluation WHERE assignment_id = :id"),
                {"id": assignment["id"]},
            ).scalar_one() == 1
    finally:
        engine.dispose()


def test_evaluation_validates_immutable_rubric_and_is_scoped_to_owner(auth_context):
    client, private_key, settings, candidate, employer, _task_id, _version_id, assignment = _matched_task(
        auth_context
    )
    submitted = client.post(
        f"/api/v1/candidate/task-assignments/{assignment['id']}/submissions",
        headers=candidate,
        json={"response_text": "A response for the employer reviewer."},
    )
    assert submitted.status_code == 201, submitted.text

    invalid = client.put(
        f"/api/v1/employer/task-assignments/{assignment['id']}/evaluation",
        headers=employer,
        json={"rubric_scores": [{"name": "Correctness", "points_awarded": 61}]},
    )
    assert invalid.status_code == 422
    assert invalid.json()["error"]["code"] == "EMPLOYER_EVALUATION_RUBRIC_MISMATCH"

    outsider = _employer(client, private_key, settings, sub=f"evaluation-outsider-{uuid4().hex}")
    assert client.get("/api/v1/employer/task-assignments", headers=outsider).json() == []
    denied = client.put(
        f"/api/v1/employer/task-assignments/{assignment['id']}/evaluation",
        headers=outsider,
        json={"rubric_scores": _scores(), "release_to_candidate": True},
    )
    assert denied.status_code == 404
    assert denied.json()["error"]["code"] == "EMPLOYER_TASK_ASSIGNMENT_NOT_FOUND"

    candidate_denied = client.get("/api/v1/employer/task-assignments", headers=candidate)
    assert candidate_denied.status_code == 403
    assert candidate_denied.json()["error"]["code"] == "ROLE_REQUIRED"


def test_evaluation_requires_a_candidate_submission(auth_context):
    client, _private_key, _settings, _candidate_headers, employer, _task_id, _version_id, assignment = _matched_task(
        auth_context
    )
    response = client.put(
        f"/api/v1/employer/task-assignments/{assignment['id']}/evaluation",
        headers=employer,
        json={"rubric_scores": _scores()},
    )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "EMPLOYER_EVALUATION_SUBMISSION_REQUIRED"
