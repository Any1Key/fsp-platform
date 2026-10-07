from uuid import uuid4

from test_invitations import _candidate, _employer


def _need():
    return {
        "team": "Platform engineering",
        "role": "Backend engineer",
        "specialization": "backend-engineering",
        "grade": "middle",
        "required_skills": ["python"],
        "preferred_skills": ["rest-apis"],
    }


def _content(title="Bounded retry task"):
    return {
        "title": title,
        "instructions": "Implement a bounded retry policy and explain the failure mode.",
        "target_skills": ["python", "rest-apis"],
        "expected_grade": "middle",
        "estimated_minutes": 30,
        "deadline_hours": 72,
        "rubric": [
            {"name": "Correctness", "points": 60, "description": "Handles retry limits."},
            {"name": "Explanation", "points": 40, "description": "Explains trade-offs."},
        ],
    }


def _employer_task_stage(client, headers):
    assert client.post("/api/v1/employer/hiring-need", headers=headers, json=_need()).status_code == 201
    pipeline = client.get("/api/v1/employer/hiring-pipeline", headers=headers)
    assert pipeline.status_code == 200
    configured = client.put(
        "/api/v1/employer/hiring-pipeline",
        headers=headers,
        json={
            "stages": [
                {
                    "stage_type": "platform_review",
                    "title": "Evidence review",
                    "required": True,
                    "estimated_minutes": 15,
                },
                {
                    "stage_type": "employer_task",
                    "title": "Backend exercise",
                    "required": True,
                    "estimated_minutes": 45,
                },
                {
                    "stage_type": "final_decision",
                    "title": "Decision",
                    "required": True,
                    "estimated_minutes": 10,
                },
            ]
        },
    )
    assert configured.status_code == 200, configured.text
    return configured.json()["stages"][1]["id"]


def test_employer_authors_draft_publishes_and_versions_task(auth_context):
    client, private_key, settings = auth_context
    employer = _employer(client, private_key, settings, sub=f"task-owner-{uuid4().hex}")
    stage_id = _employer_task_stage(client, employer)

    created = client.post(
        "/api/v1/employer/tasks",
        headers=employer,
        json={**_content(), "pipeline_stage_id": stage_id},
    )
    assert created.status_code == 201, created.text
    draft = created.json()
    assert draft["status"] == "draft"
    assert draft["current_version"]["version_number"] == 1
    assert draft["current_version"]["rubric"][0]["points"] == 60
    assert draft["current_version"]["target_skills"] == ["python", "rest-apis"]

    edited = client.patch(
        f"/api/v1/employer/tasks/{draft['id']}/draft",
        headers=employer,
        json=_content("Bounded retry task — reviewed"),
    )
    assert edited.status_code == 200, edited.text
    assert edited.json()["current_version"]["title"] == "Bounded retry task — reviewed"

    published = client.post(
        f"/api/v1/employer/tasks/{draft['id']}/publish", headers=employer
    )
    assert published.status_code == 200, published.text
    published_body = published.json()
    assert published_body["status"] == "published"
    assert [(item["version_number"], item["status"]) for item in published_body["versions"]] == [
        (1, "published")
    ]

    next_version = client.post(
        f"/api/v1/employer/tasks/{draft['id']}/versions",
        headers=employer,
        json=_content("Bounded retry task — v2"),
    )
    assert next_version.status_code == 200, next_version.text
    assert next_version.json()["status"] == "draft"
    assert next_version.json()["current_version"]["version_number"] == 2

    republish = client.post(
        f"/api/v1/employer/tasks/{draft['id']}/publish", headers=employer
    )
    assert republish.status_code == 200, republish.text
    assert [(item["version_number"], item["status"]) for item in republish.json()["versions"]] == [
        (1, "retired"),
        (2, "published"),
    ]
    listed = client.get("/api/v1/employer/tasks", headers=employer)
    assert listed.status_code == 200
    assert listed.json()[0]["current_version"]["title"] == "Bounded retry task — v2"


def test_task_authoring_validates_stage_skills_and_role_ownership(auth_context):
    client, private_key, settings = auth_context
    employer = _employer(client, private_key, settings, sub=f"task-validation-{uuid4().hex}")
    stage_id = _employer_task_stage(client, employer)

    invalid_skill = client.post(
        "/api/v1/employer/tasks",
        headers=employer,
        json={**_content(), "pipeline_stage_id": stage_id, "target_skills": ["not-a-skill"]},
    )
    assert invalid_skill.status_code == 422
    assert invalid_skill.json()["error"]["code"] == "EMPLOYER_TASK_SKILL_NOT_AVAILABLE"
    assert client.get("/api/v1/employer/tasks", headers=employer).json() == []

    candidate = _candidate(
        client, private_key, settings, sub=f"task-candidate-{uuid4().hex}", verified=False
    )[0]
    denied = client.get("/api/v1/employer/tasks", headers=candidate)
    assert denied.status_code == 403
    assert denied.json()["error"]["code"] == "ROLE_REQUIRED"

    other = _employer(client, private_key, settings, sub=f"task-other-{uuid4().hex}")
    assert client.post("/api/v1/employer/hiring-need", headers=other, json=_need()).status_code == 201
    other_pipeline = client.get("/api/v1/employer/hiring-pipeline", headers=other).json()
    wrong_stage = client.post(
        "/api/v1/employer/tasks",
        headers=other,
        json={**_content(), "pipeline_stage_id": stage_id},
    )
    assert wrong_stage.status_code == 422
    assert wrong_stage.json()["error"]["code"] == "EMPLOYER_TASK_STAGE_NOT_FOUND"
    assert other_pipeline["stages"][0]["stage_type"] == "platform_review"


def test_task_publishing_requires_a_draft_and_global_assessment_is_not_involved(auth_context):
    client, private_key, settings = auth_context
    employer = _employer(client, private_key, settings, sub=f"task-publish-{uuid4().hex}")
    stage_id = _employer_task_stage(client, employer)
    created = client.post(
        "/api/v1/employer/tasks",
        headers=employer,
        json={**_content(), "pipeline_stage_id": stage_id},
    )
    task_id = created.json()["id"]
    assert client.post(f"/api/v1/employer/tasks/{task_id}/publish", headers=employer).status_code == 200
    second_publish = client.post(
        f"/api/v1/employer/tasks/{task_id}/publish", headers=employer
    )
    assert second_publish.status_code == 409
    assert second_publish.json()["error"]["code"] == "EMPLOYER_TASK_DRAFT_REQUIRED"
