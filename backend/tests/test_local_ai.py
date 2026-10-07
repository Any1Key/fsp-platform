import pytest
from test_invitations import _candidate, _employer

from app.local_ai import DisabledLocalAiAdapter, EmployerTaskDraftContext


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
