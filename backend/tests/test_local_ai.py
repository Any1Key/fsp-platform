from uuid import uuid4

import pytest
from test_employer_tasks import _content, _employer_task_stage
from test_invitations import _candidate, _employer

from app import main
from app.local_ai import (
    DisabledLocalAiAdapter,
    EmployerTaskDraftContext,
    LocalAiDraftResult,
)


def _need():
    return {
        "team": "Platform engineering",
        "role": "Backend engineer",
        "specialization": "backend-engineering",
        "grade": "middle",
        "required_skills": ["python"],
        "preferred_skills": ["rest-apis"],
    }


@pytest.mark.asyncio
async def test_disabled_local_ai_adapter_is_deterministic_and_does_not_emit_a_draft():
    context = EmployerTaskDraftContext(
        team="Platform engineering",
        role="Backend engineer",
        specialization="backend-engineering",
        grade="middle",
        required_skills=("python",),
        preferred_skills=("rest-apis",),
    )

    first = await DisabledLocalAiAdapter().propose_task_draft(context)
    second = await DisabledLocalAiAdapter().propose_task_draft(context)

    assert first == second
    assert first.status == "disabled"
    assert first.source == "disabled"
    assert first.reason == "local_ai_disabled"
    assert first.draft is None


def test_employer_task_draft_suggestion_exposes_ai_off_fallback(auth_context):
    client, private_key, settings = auth_context
    employer = _employer(client, private_key, settings, sub="local-ai-employer")

    missing_need = client.post(
        "/api/v1/employer/tasks/draft-suggestion",
        headers=employer,
    )
    assert missing_need.status_code == 404
    assert missing_need.json()["error"]["code"] == "HIRING_NEED_NOT_FOUND"

    created_need = client.post("/api/v1/employer/hiring-need", headers=employer, json=_need())
    assert created_need.status_code == 201, created_need.text
    suggestion = client.post(
        "/api/v1/employer/tasks/draft-suggestion",
        headers=employer,
    )
    assert suggestion.status_code == 200, suggestion.text
    assert suggestion.json() == {
        "status": "disabled",
        "source": "disabled",
        "reason": "local_ai_disabled",
        "draft": None,
        "approved_example_count": 0,
        "approved_examples": [],
    }


def test_candidate_cannot_probe_employer_task_draft_assistance(auth_context):
    client, private_key, settings = auth_context
    candidate, _ = _candidate(
        client,
        private_key,
        settings,
        sub="local-ai-candidate",
        verified=False,
    )

    response = client.post(
        "/api/v1/employer/tasks/draft-suggestion",
        headers=candidate,
    )

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "ROLE_REQUIRED"


def test_published_task_is_retrieved_as_bounded_employer_scoped_memory(auth_context):
    client, private_key, settings = auth_context
    employer = _employer(client, private_key, settings, sub=f"memory-owner-{uuid4().hex}")
    stage_id = _employer_task_stage(client, employer)
    created = client.post(
        "/api/v1/employer/tasks",
        headers=employer,
        json={**_content("Approved retry example"), "pipeline_stage_id": stage_id},
    )
    assert created.status_code == 201, created.text
    task_id = created.json()["id"]

    before_publish = client.post(
        "/api/v1/employer/tasks/draft-suggestion", headers=employer
    )
    assert before_publish.status_code == 200
    assert before_publish.json()["approved_example_count"] == 0

    published = client.post(f"/api/v1/employer/tasks/{task_id}/publish", headers=employer)
    assert published.status_code == 200, published.text

    suggestion = client.post(
        "/api/v1/employer/tasks/draft-suggestion", headers=employer
    )
    assert suggestion.status_code == 200, suggestion.text
    body = suggestion.json()
    assert body["status"] == "disabled"
    assert body["approved_example_count"] == 1
    assert body["approved_examples"][0]["title"] == "Approved retry example"
    assert body["approved_examples"][0]["matched_required_skills"] == ["python"]


def test_approved_task_memory_does_not_cross_company_boundaries(auth_context):
    client, private_key, settings = auth_context
    owner = _employer(client, private_key, settings, sub=f"memory-owner-{uuid4().hex}")
    owner_stage = _employer_task_stage(client, owner)
    created = client.post(
        "/api/v1/employer/tasks",
        headers=owner,
        json={**_content("Private approved example"), "pipeline_stage_id": owner_stage},
    )
    assert created.status_code == 201
    assert client.post(
        f"/api/v1/employer/tasks/{created.json()['id']}/publish", headers=owner
    ).status_code == 200

    other = _employer(client, private_key, settings, sub=f"memory-other-{uuid4().hex}")
    assert client.post("/api/v1/employer/hiring-need", headers=other, json=_need()).status_code == 201
    other_suggestion = client.post(
        "/api/v1/employer/tasks/draft-suggestion", headers=other
    )
    assert other_suggestion.status_code == 200
    assert other_suggestion.json()["approved_examples"] == []


def test_retrieval_is_bounded_and_passes_examples_to_the_adapter(auth_context, monkeypatch):
    client, private_key, settings = auth_context
    employer = _employer(client, private_key, settings, sub=f"memory-bounded-{uuid4().hex}")
    stage_id = _employer_task_stage(client, employer)
    for index in range(6):
        created = client.post(
            "/api/v1/employer/tasks",
            headers=employer,
            json={**_content(f"Approved example {index}"), "pipeline_stage_id": stage_id},
        )
        assert created.status_code == 201
        assert client.post(
            f"/api/v1/employer/tasks/{created.json()['id']}/publish", headers=employer
        ).status_code == 200

    captured = {}

    class CapturingAdapter:
        async def propose_task_draft(self, context):
            captured["examples"] = context.approved_examples
            return LocalAiDraftResult(status="completed", source="local", draft={})

    monkeypatch.setattr(main, "local_ai_port", CapturingAdapter())
    suggestion = client.post(
        "/api/v1/employer/tasks/draft-suggestion", headers=employer
    )
    assert suggestion.status_code == 200, suggestion.text
    assert suggestion.json()["status"] == "completed"
    assert suggestion.json()["approved_example_count"] == 5
    assert len(captured["examples"]) == 5
    assert all(example.specialization == "backend-engineering" for example in captured["examples"])
