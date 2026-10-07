from uuid import uuid4

from test_invitations import _candidate, _employer, _offer


def _need():
    return {
        "team": "Platform engineering",
        "role": "Backend engineer",
        "specialization": "backend-engineering",
        "grade": "middle",
        "required_skills": ["python"],
        "preferred_skills": ["rest-apis"],
    }


def test_employer_can_build_and_reorder_owned_hiring_pipeline(auth_context):
    client, private_key, settings = auth_context
    employer = _employer(client, private_key, settings, sub=f"pipeline-owner-{uuid4().hex}")
    assert client.post("/api/v1/employer/hiring-need", headers=employer, json=_need()).status_code == 201

    default = client.get("/api/v1/employer/hiring-pipeline", headers=employer)
    assert default.status_code == 200
    assert [stage["stage_type"] for stage in default.json()["stages"]] == [
        "platform_review",
        "final_decision",
    ]

    configured = client.put(
        "/api/v1/employer/hiring-pipeline",
        headers=employer,
        json={
            "stages": [
                {
                    "stage_type": "platform_review",
                    "title": "Verified evidence review",
                    "required": True,
                    "estimated_minutes": 15,
                },
                {
                    "stage_type": "interview",
                    "title": "System design conversation",
                    "required": False,
                    "estimated_minutes": 60,
                },
                {
                    "stage_type": "final_decision",
                    "title": "Hiring decision",
                    "required": True,
                    "estimated_minutes": 10,
                },
            ]
        },
    )
    assert configured.status_code == 200, configured.text
    body = configured.json()
    assert [stage["position"] for stage in body["stages"]] == [0, 1, 2]
    assert [stage["stage_type"] for stage in body["stages"]] == [
        "platform_review",
        "interview",
        "final_decision",
    ]
    assert body["stages"][1]["required"] is False

    reloaded = client.get("/api/v1/employer/hiring-pipeline", headers=employer)
    assert [stage["title"] for stage in reloaded.json()["stages"]] == [
        "Verified evidence review",
        "System design conversation",
        "Hiring decision",
    ]


def test_pipeline_rejects_invalid_boundary_without_partial_write_and_is_role_scoped(auth_context):
    client, private_key, settings = auth_context
    employer = _employer(client, private_key, settings, sub=f"pipeline-validation-{uuid4().hex}")
    assert client.post("/api/v1/employer/hiring-need", headers=employer, json=_need()).status_code == 201
    initial = client.get("/api/v1/employer/hiring-pipeline", headers=employer).json()

    invalid = client.put(
        "/api/v1/employer/hiring-pipeline",
        headers=employer,
        json={
            "stages": [
                {
                    "stage_type": "interview",
                    "title": "Interview",
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
    assert invalid.status_code == 422
    assert invalid.json()["error"]["code"] == "HIRING_PIPELINE_PLATFORM_REVIEW_REQUIRED"
    assert client.get("/api/v1/employer/hiring-pipeline", headers=employer).json()["id"] == initial["id"]
    assert [stage["stage_type"] for stage in client.get("/api/v1/employer/hiring-pipeline", headers=employer).json()["stages"]] == [
        "platform_review",
        "final_decision",
    ]

    candidate = _candidate(client, private_key, settings, sub=f"pipeline-candidate-{uuid4().hex}", verified=False)[0]
    denied = client.get("/api/v1/employer/hiring-pipeline", headers=candidate)
    assert denied.status_code == 403
    assert denied.json()["error"]["code"] == "ROLE_REQUIRED"


def test_new_invitation_contains_safe_pipeline_snapshot_for_candidate(auth_context):
    client, private_key, settings = auth_context
    candidate_headers, candidate_id = _candidate(
        client, private_key, settings, sub=f"pipeline-preview-candidate-{uuid4().hex}"
    )
    employer = _employer(client, private_key, settings, sub=f"pipeline-preview-employer-{uuid4().hex}")
    assert client.post("/api/v1/employer/hiring-need", headers=employer, json=_need()).status_code == 201
    assert client.get("/api/v1/employer/hiring-pipeline", headers=employer).status_code == 200
    saved = client.put(
        "/api/v1/employer/hiring-pipeline",
        headers=employer,
        json={
            "stages": [
                {"stage_type": "platform_review", "title": "Evidence review", "required": True, "estimated_minutes": 15},
                {"stage_type": "questionnaire", "title": "Team questionnaire", "required": False, "estimated_minutes": 20},
                {"stage_type": "final_decision", "title": "Decision", "required": True, "estimated_minutes": 10},
            ]
        },
    )
    assert saved.status_code == 200

    invitation = client.post(
        "/api/v1/employer/invitations", headers=employer, json=_offer(candidate_id)
    )
    assert invitation.status_code == 201, invitation.text
    stages = invitation.json()["pipeline_stages"]
    assert [stage["title"] for stage in stages] == ["Evidence review", "Team questionnaire", "Decision"]
    assert set(stages[1]) == {"stage_type", "title", "required", "estimated_minutes"}

    incoming = client.get("/api/v1/candidate/invitations", headers=candidate_headers)
    assert incoming.status_code == 200
    assert incoming.json()[0]["pipeline_stages"] == stages
