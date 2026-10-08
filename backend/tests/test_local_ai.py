import asyncio
import json
import threading
import time
from uuid import uuid4

import pytest
from test_employer_tasks import _content, _employer_task_stage
from test_invitations import _candidate, _employer

from app import local_ai, main
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


def _poll_suggestion(client, headers, response):
    """Resolve an enabled adapter job through the public polling contract."""

    assert response.status_code == 202, response.text
    body = response.json()
    assert body["job_id"]
    # The job is deliberately asynchronous.  Keep a bounded wait that is
    # longer than the old one-second budget so a busy verification host can
    # schedule the single local-AI worker without making the contract flaky.
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        if body["status"] not in {"queued", "running"}:
            return body
        time.sleep(0.05)
        polled = client.get(
            f"/api/v1/employer/tasks/draft-suggestion/jobs/{body['job_id']}",
            headers=headers,
        )
        assert polled.status_code == 200, polled.text
        body = polled.json()
    raise AssertionError(f"local-AI job did not finish: {body}")


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
        "job_id": None,
        "retry_after_seconds": None,
        "approved_example_count": 0,
        "approved_examples": [],
        "feedback_history": [],
    }


def test_ai_off_fallback_keeps_manual_task_authoring_available_without_queueing(
    auth_context, monkeypatch
):
    client, private_key, settings = auth_context
    employer = _employer(client, private_key, settings, sub=f"local-ai-off-manual-{uuid4().hex}")
    stage_id = _employer_task_stage(client, employer)

    def fail_if_queued(*args, **kwargs):
        del args, kwargs
        raise AssertionError("AI-off mode must not create an async local-AI job")

    monkeypatch.setattr(main, "enqueue_task_draft_job", fail_if_queued)
    suggestion = client.post(
        "/api/v1/employer/tasks/draft-suggestion",
        headers=employer,
    )
    assert suggestion.status_code == 200, suggestion.text
    assert suggestion.json()["status"] == "disabled"
    assert suggestion.json()["draft"] is None
    assert suggestion.json()["job_id"] is None

    created = client.post(
        "/api/v1/employer/tasks",
        headers=employer,
        json={**_content("Manual fallback task"), "pipeline_stage_id": stage_id},
    )
    assert created.status_code == 201, created.text
    task_id = created.json()["id"]
    assert created.json()["status"] == "draft"

    published = client.post(f"/api/v1/employer/tasks/{task_id}/publish", headers=employer)
    assert published.status_code == 200, published.text
    assert published.json()["status"] == "published"
    assert published.json()["current_version"]["title"] == "Manual fallback task"


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
    generated = _poll_suggestion(client, employer, suggestion)["draft"]

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
    suggestion_after_feedback = _poll_suggestion(client, employer, suggestion_after_feedback)
    assert [item["decision"] for item in suggestion_after_feedback["feedback_history"]] == [
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

    suggestion = _poll_suggestion(client, employer, suggestion)
    assert suggestion["status"] == "failed"
    assert suggestion["reason"] == "local_ai_invalid_draft"
    assert suggestion["draft"] is None


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
    suggestion = _poll_suggestion(client, employer, suggestion)
    assert suggestion["status"] == "completed"
    assert suggestion["approved_example_count"] == 5
    assert len(captured["examples"]) == 5
    assert all(example.specialization == "backend-engineering" for example in captured["examples"])


def test_enabled_local_ai_is_rate_limited_and_job_is_company_scoped(auth_context, monkeypatch):
    client, private_key, settings = auth_context
    limited = settings.model_copy(
        update={"local_ai_rate_limit_per_minute": 1, "local_ai_max_active_jobs_per_company": 2}
    )
    monkeypatch.setattr(main, "get_settings", lambda: limited)
    employer = _employer(client, private_key, limited, sub=f"local-ai-rate-{uuid4().hex}")
    assert client.post("/api/v1/employer/hiring-need", headers=employer, json=_need()).status_code == 201

    class FastAdapter:
        async def propose_task_draft(self, context):
            return LocalAiDraftResult(status="completed", source="local", draft=_draft())

    monkeypatch.setattr(main, "local_ai_port", FastAdapter())
    first = client.post("/api/v1/employer/tasks/draft-suggestion", headers=employer)
    assert first.status_code == 202
    second = client.post("/api/v1/employer/tasks/draft-suggestion", headers=employer)
    assert second.status_code == 429
    assert second.headers["retry-after"] == "60"
    completed = _poll_suggestion(client, employer, first)
    assert completed["status"] == "completed"

    other = _employer(client, private_key, settings, sub=f"local-ai-rate-other-{uuid4().hex}")
    assert client.post("/api/v1/employer/hiring-need", headers=other, json=_need()).status_code == 201
    other_job = client.post("/api/v1/employer/tasks/draft-suggestion", headers=other)
    assert other_job.status_code == 202
    assert client.get(
        f"/api/v1/employer/tasks/draft-suggestion/jobs/{first.json()['job_id']}",
        headers=other,
    ).status_code == 404
    _poll_suggestion(client, other, other_job)


def test_enabled_local_ai_timeout_is_a_failed_job_with_manual_fallback(auth_context, monkeypatch):
    client, private_key, settings = auth_context
    short_timeout = settings.model_copy(update={"local_ai_timeout_seconds": 0.01})
    monkeypatch.setattr(main, "get_settings", lambda: short_timeout)
    employer = _employer(client, private_key, short_timeout, sub=f"local-ai-timeout-{uuid4().hex}")
    assert client.post("/api/v1/employer/hiring-need", headers=employer, json=_need()).status_code == 201

    class SlowAdapter:
        async def propose_task_draft(self, context):
            del context
            await asyncio.sleep(0.1)
            return LocalAiDraftResult(status="completed", source="local", draft=_draft())

    monkeypatch.setattr(main, "local_ai_port", SlowAdapter())
    queued = client.post("/api/v1/employer/tasks/draft-suggestion", headers=employer)
    result = _poll_suggestion(client, employer, queued)
    assert result["status"] == "failed"
    assert result["reason"] == "local_ai_timeout"
    assert result["draft"] is None
    assert client.get("/api/v1/employer/tasks", headers=employer).json() == []


def test_local_ai_worker_failure_does_not_leave_job_queued_or_poison_executor(
    auth_context, monkeypatch
):
    client, private_key, settings = auth_context
    employer = _employer(client, private_key, settings, sub=f"local-ai-worker-{uuid4().hex}")
    assert client.post("/api/v1/employer/hiring-need", headers=employer, json=_need()).status_code == 201

    class FastAdapter:
        async def propose_task_draft(self, context):
            del context
            return LocalAiDraftResult(status="completed", source="local", draft=_draft())

    monkeypatch.setattr(main, "local_ai_port", FastAdapter())
    original_runner = local_ai.run_task_draft_job
    runner_failed = threading.Event()

    def crash_runner(*args, **kwargs):
        del args, kwargs
        runner_failed.set()
        raise RuntimeError("simulated worker boundary failure")

    monkeypatch.setattr(local_ai, "run_task_draft_job", crash_runner)
    first = client.post("/api/v1/employer/tasks/draft-suggestion", headers=employer)
    assert first.status_code == 202
    assert runner_failed.wait(timeout=10)

    monkeypatch.setattr(local_ai, "run_task_draft_job", original_runner)
    failed = _poll_suggestion(client, employer, first)
    assert failed["status"] == "failed"
    assert failed["reason"] == "local_ai_job_failed"

    second = client.post("/api/v1/employer/tasks/draft-suggestion", headers=employer)
    completed = _poll_suggestion(client, employer, second)
    assert completed["status"] == "completed"


def test_local_ai_worker_timeout_preserves_timeout_reason(auth_context, monkeypatch):
    client, private_key, settings = auth_context
    employer = _employer(client, private_key, settings, sub=f"local-ai-worker-timeout-{uuid4().hex}")
    assert client.post("/api/v1/employer/hiring-need", headers=employer, json=_need()).status_code == 201

    class FastAdapter:
        async def propose_task_draft(self, context):
            del context
            return LocalAiDraftResult(status="completed", source="local", draft=_draft())

    monkeypatch.setattr(main, "local_ai_port", FastAdapter())

    original_runner = local_ai.run_task_draft_job
    runner_timed_out = threading.Event()

    def timeout_runner(*args, **kwargs):
        del args, kwargs
        runner_timed_out.set()
        raise TimeoutError("simulated worker timeout")

    monkeypatch.setattr(local_ai, "run_task_draft_job", timeout_runner)
    queued = client.post("/api/v1/employer/tasks/draft-suggestion", headers=employer)
    assert queued.status_code == 202
    assert runner_timed_out.wait(timeout=10)

    monkeypatch.setattr(local_ai, "run_task_draft_job", original_runner)
    result = _poll_suggestion(client, employer, queued)
    assert result["status"] == "failed"
    assert result["reason"] == "local_ai_timeout"
