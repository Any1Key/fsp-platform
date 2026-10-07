import json
from uuid import uuid4

import pytest
from test_employer_tasks import _content, _employer_task_stage
from test_invitations import _candidate, _employer

from app import main
from app.local_ai import (
    DisabledLocalAiAdapter,
    EmployerTaskDraftContext,
    LocalAiDraftResult,
    LocalHttpAiAdapter,
    validate_task_draft,
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


def _draft():
    return {
        "title": "Bounded retry policy",
        "instructions": "Implement a bounded retry policy for a REST client.",
        "target_skills": ["python", "rest-apis"],
        "expected_grade": "middle",
        "estimated_minutes": 45,
        "deadline_hours": 72,
        "rubric": [
            {"name": "Correctness", "points": 70, "description": "Works as specified."},
            {"name": "Explanation", "points": 30, "description": "Explains trade-offs."},
        ],
        "difficulty_rationale": "The task tests the required skill and the preferred API skill.",
    }


def _context():
    return EmployerTaskDraftContext(
        team="Platform engineering",
        role="Backend engineer",
        specialization="backend-engineering",
        grade="middle",
        required_skills=("python",),
        preferred_skills=("rest-apis",),
    )


@pytest.mark.asyncio
async def test_disabled_local_ai_adapter_is_deterministic_and_does_not_emit_a_draft():
    context = _context()

    first = await DisabledLocalAiAdapter().propose_task_draft(context)
    second = await DisabledLocalAiAdapter().propose_task_draft(context)

    assert first == second
    assert first.status == "disabled"
    assert first.source == "disabled"
    assert first.reason == "local_ai_disabled"
    assert first.draft is None


def test_task_draft_validation_enforces_current_need_and_grade():
    validated = validate_task_draft(_draft(), _context())

    assert validated["target_skills"] == ["python", "rest-apis"]
    assert validated["difficulty_rationale"].startswith("The task tests")

    invalid_skill = {**_draft(), "target_skills": ["python", "unknown-skill"]}
    with pytest.raises(ValueError, match="draft_skill_outside_need"):
        validate_task_draft(invalid_skill, _context())

    invalid_grade = {**_draft(), "expected_grade": "senior"}
    with pytest.raises(ValueError, match="draft_grade_mismatch"):
        validate_task_draft(invalid_grade, _context())


@pytest.mark.asyncio
async def test_local_http_adapter_validates_json_response(monkeypatch):
    captured = {}

    class Response:
        def raise_for_status(self):
            return None

        def json(self):
            return {"choices": [{"message": {"content": json.dumps(_draft())}}]}

    class Client:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, traceback):
            return False

        async def post(self, url, json):
            captured["url"] = url
            captured["payload"] = json
            return Response()

    monkeypatch.setattr("app.local_ai.httpx.AsyncClient", lambda timeout: Client())
    result = await LocalHttpAiAdapter("http://local-ai:11434", "test-model", 3).propose_task_draft(
        _context()
    )

    assert result.status == "completed"
    assert result.source == "local"
    assert result.draft["expected_grade"] == "middle"
    assert captured["url"] == "http://local-ai:11434/v1/chat/completions"
    assert captured["payload"]["response_format"] == {"type": "json_object"}


@pytest.mark.asyncio
async def test_local_http_adapter_rejects_malformed_json(monkeypatch):
    class Response:
        def raise_for_status(self):
            return None

        def json(self):
            return {"choices": [{"message": {"content": "{not-json"}}]}

    class Client:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, traceback):
            return False

        async def post(self, url, json):
            del url, json
            return Response()

    monkeypatch.setattr("app.local_ai.httpx.AsyncClient", lambda timeout: Client())
    result = await LocalHttpAiAdapter("http://local-ai:11434", "test-model", 3).propose_task_draft(
        _context()
    )

    assert result == LocalAiDraftResult(
        status="failed", source="local", reason="local_ai_invalid_or_unavailable"
    )


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
        "feedback_history": [],
    }


def test_employer_can_approve_edit_or_reject_a_draft_and_history_is_scoped(auth_context, monkeypatch):
    client, private_key, settings = auth_context
    employer = _employer(client, private_key, settings, sub=f"local-ai-feedback-{uuid4().hex}")
    created_need = client.post("/api/v1/employer/hiring-need", headers=employer, json=_need())
    assert created_need.status_code == 201, created_need.text

    class DraftAdapter:
        async def propose_task_draft(self, context):
            del context
            return LocalAiDraftResult(status="completed", source="local", draft=_draft())

    monkeypatch.setattr(main, "local_ai_port", DraftAdapter())
    suggestion = client.post("/api/v1/employer/tasks/draft-suggestion", headers=employer)
    assert suggestion.status_code == 200, suggestion.text
    generated = suggestion.json()["draft"]

    approved = client.post(
        "/api/v1/employer/tasks/draft-suggestion/feedback",
        headers=employer,
        json={"decision": "approved", "draft": generated, "feedback_note": "Good baseline."},
    )
    assert approved.status_code == 201, approved.text
    assert approved.json()["decision"] == "approved"
    assert approved.json()["reviewed_draft"]["title"] == "Bounded retry policy"
    assert approved.json()["feedback_note"] == "Good baseline."

    edited_draft = {**generated, "title": "Reviewed bounded retry policy"}
    edited = client.post(
        "/api/v1/employer/tasks/draft-suggestion/feedback",
        headers=employer,
        json={"decision": "edited", "draft": edited_draft},
    )
    assert edited.status_code == 201, edited.text
    assert edited.json()["reviewed_draft"]["title"] == "Reviewed bounded retry policy"

    rejected = client.post(
        "/api/v1/employer/tasks/draft-suggestion/feedback",
        headers=employer,
        json={"decision": "rejected", "feedback_note": "Too narrow for this team."},
    )
    assert rejected.status_code == 201, rejected.text
    assert rejected.json()["reviewed_draft"] is None

    history = client.get(
        "/api/v1/employer/tasks/draft-suggestion/feedback", headers=employer
    )
    assert history.status_code == 200, history.text
    assert [item["decision"] for item in history.json()] == ["rejected", "edited", "approved"]

    suggestion_after_feedback = client.post(
        "/api/v1/employer/tasks/draft-suggestion", headers=employer
    )
    assert suggestion_after_feedback.status_code == 200
    assert [item["decision"] for item in suggestion_after_feedback.json()["feedback_history"]] == [
        "rejected",
        "edited",
        "approved",
    ]

    other = _employer(client, private_key, settings, sub=f"local-ai-feedback-other-{uuid4().hex}")
    assert client.post("/api/v1/employer/hiring-need", headers=other, json=_need()).status_code == 201
    other_history = client.get(
        "/api/v1/employer/tasks/draft-suggestion/feedback", headers=other
    )
    assert other_history.status_code == 200
    assert other_history.json() == []


def test_draft_feedback_requires_need_validated_content_and_never_publishes(auth_context):
    client, private_key, settings = auth_context
    employer = _employer(client, private_key, settings, sub=f"local-ai-feedback-validation-{uuid4().hex}")
    created_need = client.post("/api/v1/employer/hiring-need", headers=employer, json=_need())
    assert created_need.status_code == 201, created_need.text

    missing_draft = client.post(
        "/api/v1/employer/tasks/draft-suggestion/feedback",
        headers=employer,
        json={"decision": "approved"},
    )
    assert missing_draft.status_code == 422
    assert missing_draft.json()["error"]["code"] == "LOCAL_AI_FEEDBACK_DRAFT_REQUIRED"

    invalid = client.post(
        "/api/v1/employer/tasks/draft-suggestion/feedback",
        headers=employer,
        json={"decision": "edited", "draft": {**_draft(), "expected_grade": "senior"}},
    )
    assert invalid.status_code == 422
    assert invalid.json()["error"]["code"] == "LOCAL_AI_FEEDBACK_DRAFT_INVALID"

    rejected_with_content = client.post(
        "/api/v1/employer/tasks/draft-suggestion/feedback",
        headers=employer,
        json={"decision": "rejected", "draft": _draft()},
    )
    assert rejected_with_content.status_code == 422
    assert rejected_with_content.json()["error"]["code"] == "LOCAL_AI_FEEDBACK_REJECTED_DRAFT_FORBIDDEN"
    assert client.get("/api/v1/employer/tasks", headers=employer).json() == []


def test_draft_suggestion_does_not_expose_an_invalid_adapter_draft(auth_context, monkeypatch):
    client, private_key, settings = auth_context
    employer = _employer(client, private_key, settings, sub="local-ai-invalid-draft")
    created_need = client.post("/api/v1/employer/hiring-need", headers=employer, json=_need())
    assert created_need.status_code == 201, created_need.text

    class InvalidAdapter:
        async def propose_task_draft(self, context):
            del context
            return LocalAiDraftResult(
                status="completed",
                source="local",
                draft={**_draft(), "expected_grade": "senior"},
            )

    monkeypatch.setattr(main, "local_ai_port", InvalidAdapter())
    suggestion = client.post(
        "/api/v1/employer/tasks/draft-suggestion",
        headers=employer,
    )

    assert suggestion.status_code == 200
    assert suggestion.json()["status"] == "failed"
    assert suggestion.json()["reason"] == "local_ai_invalid_draft"
    assert suggestion.json()["draft"] is None


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
            return LocalAiDraftResult(status="completed", source="local", draft=_draft())

    monkeypatch.setattr(main, "local_ai_port", CapturingAdapter())
    suggestion = client.post(
        "/api/v1/employer/tasks/draft-suggestion", headers=employer
    )
    assert suggestion.status_code == 200, suggestion.text
    assert suggestion.json()["status"] == "completed"
    assert suggestion.json()["approved_example_count"] == 5
    assert len(captured["examples"]) == 5
    assert all(example.specialization == "backend-engineering" for example in captured["examples"])
