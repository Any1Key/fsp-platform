from datetime import UTC, datetime, timedelta
from hashlib import sha256
from uuid import uuid4

import jwt
from sqlalchemy import text

from app import main
from app.db import get_db_session
from app.fsp import (
    FspAchievement,
    FspRankingNeed,
    SyntheticFspRegistryAdapter,
    calculate_fsp_contribution,
    calculate_fsp_contribution_for_candidate,
    map_achievement,
    map_recency,
)


def _headers(private_key, settings, *, sub: str, role: str = "candidate"):
    now = datetime.now(UTC)
    token = jwt.encode(
        {
            "iss": settings.keycloak_issuer,
            "aud": settings.keycloak_client_id,
            "sub": sub,
            "email": f"{sub}@team.ru" if role == "candidate" else f"{sub}@company.ru",
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


def _grant_processing_consent(client, headers):
    response = client.patch(
        "/api/v1/candidate/privacy",
        headers=headers,
        json={"processing_consent": True},
    )
    assert response.status_code == 200


def test_synthetic_adapter_is_deterministic_and_supports_no_history():
    registry = SyntheticFspRegistryAdapter()

    participant = registry.verify_link(" fsp-demo-001 ")
    assert participant is not None
    assert participant.participant_id == "FSP-DEMO-001"
    assert registry.get_participant("FSP-DEMO-001") == participant
    assert [item.achievement_id for item in registry.list_achievements("FSP-DEMO-001")] == [
        "synthetic-achievement-001",
        "synthetic-achievement-002",
    ]
    assert registry.verify_link("FSP-DEMO-NONE") is not None
    assert registry.list_achievements("FSP-DEMO-NONE") == ()
    assert registry.verify_link("unknown") is None


def test_fsp_mapping_normalizes_taxonomy_result_and_unknown_disciplines():
    mapped = map_achievement(
        FspAchievement(
            achievement_id="achievement",
            event_name="Backend event",
            event_date=datetime(2026, 1, 1, tzinfo=UTC).date(),
            discipline=" Backend Engineering ",
            level="national",
            achievement_type="finalist",
            placement="2",
            result="Finalist",
            verification="fixture",
            mapping_version="fixture-1",
        )
    )
    assert mapped.specialization_slug == "backend-engineering"
    assert mapped.skill_slugs == ("python", "sql", "rest-apis", "git")
    assert mapped.result_score == 90
    assert mapped.result_label == "prize"

    unknown = map_achievement(
        FspAchievement(
            achievement_id="unknown",
            event_name="Unknown event",
            event_date=datetime(2026, 1, 1, tzinfo=UTC).date(),
            discipline="Unmapped discipline",
            level="local",
            achievement_type="participation",
            placement=None,
            result=None,
            verification="fixture",
            mapping_version="fixture-1",
        )
    )
    assert unknown.specialization_slug is None
    assert unknown.skill_slugs == ()
    assert unknown.result_score == 40
    assert unknown.result_label == "participant"


def test_fsp_recency_is_bounded_and_future_dates_are_not_rewarded():
    as_of = datetime(2026, 10, 7, tzinfo=UTC).date()
    assert map_recency(as_of, as_of=as_of).score == 100
    assert map_recency(as_of, as_of=as_of).label == "recent"
    assert map_recency(as_of - timedelta(days=366), as_of=as_of).label == "aging"
    assert map_recency(as_of - timedelta(days=1096), as_of=as_of).label == "stale"
    future = map_recency(as_of + timedelta(days=1), as_of=as_of)
    assert future.score == 0
    assert future.label == "future"


def test_fsp_contribution_is_relevant_explainable_and_bounded():
    registry = SyntheticFspRegistryAdapter()
    achievements = registry.list_achievements("FSP-DEMO-001")
    need = FspRankingNeed(
        specialization_slug="backend-engineering",
        required_skill_slugs=("python", "rest-apis"),
        preferred_skill_slugs=("docker",),
    )

    contribution = calculate_fsp_contribution(
        achievements,
        need,
        as_of=datetime(2026, 10, 7, tzinfo=UTC).date(),
    )

    assert 0 < contribution.score <= contribution.max_score == 10.0
    assert contribution.history_status == "has_history"
    assert contribution.relevant_achievement_count == 2
    assert contribution.contributing_achievement_ids == (
        "synthetic-achievement-001",
        "synthetic-achievement-002",
    )
    assert contribution.matched_specialization is True
    assert contribution.matched_skill_slugs == ("python", "rest-apis")
    assert contribution.component_scores["uncapped_normalized"] > 0
    assert any("relevant FSP achievement" in reason for reason in contribution.reasons)

    unrelated = calculate_fsp_contribution(
        achievements,
        FspRankingNeed(specialization_slug="mobile-engineering", required_skill_slugs=("swift",)),
        as_of=datetime(2026, 10, 7, tzinfo=UTC).date(),
    )
    assert unrelated.score == 0
    assert unrelated.history_status == "has_history"
    assert unrelated.relevant_achievement_count == 0


def test_fsp_no_history_is_zero_and_many_achievements_cannot_exceed_cap():
    need = FspRankingNeed(specialization_slug="backend-engineering")
    empty = calculate_fsp_contribution((), need)
    assert empty.score == 0
    assert empty.max_score == 10.0
    assert empty.history_status == "no_history"
    assert empty.reasons == ("No FSP history; no bonus or penalty.",)

    achievement = FspAchievement(
        achievement_id="perfect",
        event_name="Perfect event",
        event_date=datetime(2026, 10, 1, tzinfo=UTC).date(),
        discipline="Backend Engineering",
        level="national",
        achievement_type="win",
        placement="1",
        result="Winner",
        verification="verified registry record",
        mapping_version="fixture-1",
    )
    capped = calculate_fsp_contribution(
        (achievement,) * 20,
        need,
        as_of=datetime(2026, 10, 7, tzinfo=UTC).date(),
    )
    assert capped.score <= 10.0
    assert capped.component_scores["uncapped_normalized"] == 1.0


def test_persisted_fsp_snapshot_can_be_scored_for_a_candidate(auth_context):
    client, private_key, settings = auth_context
    subject = f"fsp-ranking-{uuid4().hex}"
    headers = _headers(private_key, settings, sub=subject)
    _grant_processing_consent(client, headers)
    linked = client.post(
        "/api/v1/candidate/fsp-link",
        headers=headers,
        json={"fsp_id": "FSP-DEMO-001"},
    )
    assert linked.status_code == 201

    db_dependency = main.app.dependency_overrides[get_db_session]
    db_generator = db_dependency()
    db = next(db_generator)
    try:
        profile_id = db.execute(
            text(
                "SELECT cp.id FROM candidate_profile cp "
                "JOIN user_identity ui ON ui.id = cp.identity_id "
                "WHERE ui.keycloak_sub = :subject"
            ),
            {"subject": subject},
        ).scalar_one()
        contribution = calculate_fsp_contribution_for_candidate(
            db,
            profile_id,
            FspRankingNeed(specialization_slug="backend-engineering", required_skill_slugs=("python",)),
            as_of=datetime(2026, 10, 7, tzinfo=UTC).date(),
        )
    finally:
        db_generator.close()

    assert contribution.score > 0
    assert contribution.history_status == "has_history"
    assert contribution.contributing_achievement_ids


def test_candidate_fsp_link_requires_consent_and_exposes_achievements(auth_context):
    client, private_key, settings = auth_context
    headers = _headers(private_key, settings, sub=f"fsp-{uuid4().hex}")

    initial = client.get("/api/v1/candidate/fsp", headers=headers)
    assert initial.status_code == 200
    assert initial.json()["status"] == "not_linked"
    assert initial.json()["history_status"] == "no_history"
    assert initial.json()["achievements"] == []

    blocked = client.post(
        "/api/v1/candidate/fsp-link",
        headers=headers,
        json={"fsp_id": "FSP-DEMO-001"},
    )
    assert blocked.status_code == 409
    assert blocked.json()["error"]["code"] == "PROCESSING_CONSENT_REQUIRED"

    _grant_processing_consent(client, headers)
    unknown = client.post(
        "/api/v1/candidate/fsp-link",
        headers=headers,
        json={"fsp_id": "FSP-UNKNOWN"},
    )
    assert unknown.status_code == 404
    assert unknown.json()["error"]["code"] == "FSP_PARTICIPANT_NOT_FOUND"

    linked = client.post(
        "/api/v1/candidate/fsp-link",
        headers=headers,
        json={"fsp_id": " fsp-demo-001 "},
    )
    assert linked.status_code == 201
    body = linked.json()
    assert body["status"] == "linked"
    assert body["provider"] == "synthetic"
    assert body["participant_id"] == "FSP-DEMO-001"
    assert body["history_status"] == "has_history"
    assert len(body["achievements"]) == 2
    assert body["achievements"][0]["verification"] == "synthetic registry fixture"
    assert body["achievements"][0]["mapped_specialization"] == "backend-engineering"
    assert body["achievements"][0]["mapped_skills"] == ["python", "sql", "rest-apis", "git"]
    assert body["achievements"][0]["result_score"] == 90
    assert body["achievements"][0]["result_label"] == "prize"
    assert body["achievements"][0]["recency_label"] in {"recent", "aging", "old", "stale"}

    reloaded = client.get("/api/v1/candidate/fsp", headers=headers)
    assert reloaded.status_code == 200
    assert reloaded.json()["participant_id"] == "FSP-DEMO-001"
    assert [item["id"] for item in reloaded.json()["achievements"]] == [
        "synthetic-achievement-001",
        "synthetic-achievement-002",
    ]


def test_keycloak_fsp_identity_bridge_is_safe_candidate_scoped_and_explicit(auth_context):
    client, private_key, settings = auth_context
    subject = f"fsp-bridge-{uuid4().hex}"
    headers = _headers(private_key, settings, sub=subject)

    unlinked = client.get("/api/v1/candidate/fsp/integration", headers=headers)
    assert unlinked.status_code == 200
    unlinked_body = unlinked.json()
    assert unlinked_body["bridge_version"] == "keycloak-fsp-explicit-link-2026-10"
    assert unlinked_body["binding_mode"] == "explicit_candidate_link"
    assert unlinked_body["registry_adapter"] == "FspRegistryPort"
    assert unlinked_body["keycloak"] == {
        "provider": "keycloak",
        "issuer": settings.keycloak_issuer,
        "subject_fingerprint": sha256(subject.encode()).hexdigest()[:16],
    }
    assert "subject" not in unlinked_body["keycloak"]
    assert unlinked_body["fsp"] == {
        "provider": None,
        "participant_id": None,
        "status": "not_linked",
        "history_status": "no_history",
    }

    _grant_processing_consent(client, headers)
    linked = client.post(
        "/api/v1/candidate/fsp-link",
        headers=headers,
        json={"fsp_id": "FSP-DEMO-001"},
    )
    assert linked.status_code == 201

    bridge = client.get("/api/v1/candidate/fsp/integration", headers=headers)
    assert bridge.status_code == 200
    bridge_body = bridge.json()
    assert bridge_body["keycloak"]["subject_fingerprint"] == sha256(subject.encode()).hexdigest()[:16]
    assert bridge_body["fsp"] == {
        "provider": "synthetic",
        "participant_id": "FSP-DEMO-001",
        "status": "linked",
        "history_status": "has_history",
    }

    other_headers = _headers(private_key, settings, sub=f"fsp-bridge-other-{uuid4().hex}")
    other = client.get("/api/v1/candidate/fsp/integration", headers=other_headers)
    assert other.status_code == 200
    assert other.json()["fsp"]["participant_id"] is None
    assert other.json()["keycloak"]["subject_fingerprint"] != bridge_body["keycloak"]["subject_fingerprint"]

    employer_headers = _headers(
        private_key,
        settings,
        sub=f"fsp-bridge-employer-{uuid4().hex}",
        role="employer",
    )
    denied = client.get("/api/v1/candidate/fsp/integration", headers=employer_headers)
    assert denied.status_code == 403
    assert denied.json()["error"]["code"] == "ROLE_REQUIRED"


def test_candidate_can_replace_with_no_history_and_unlink(auth_context):
    client, private_key, settings = auth_context
    headers = _headers(private_key, settings, sub=f"fsp-empty-{uuid4().hex}")
    _grant_processing_consent(client, headers)

    linked = client.post(
        "/api/v1/candidate/fsp-link",
        headers=headers,
        json={"fsp_id": "FSP-DEMO-001"},
    )
    assert linked.status_code == 201

    empty = client.post(
        "/api/v1/candidate/fsp-link",
        headers=headers,
        json={"fsp_id": "FSP-DEMO-NONE"},
    )
    assert empty.status_code == 201
    assert empty.json()["status"] == "linked"
    assert empty.json()["history_status"] == "no_history"
    assert empty.json()["achievements"] == []

    removed = client.delete("/api/v1/candidate/fsp-link", headers=headers)
    assert removed.status_code == 204
    no_link = client.get("/api/v1/candidate/fsp", headers=headers)
    assert no_link.json()["status"] == "not_linked"
    assert no_link.json()["history_status"] == "no_history"


def test_fsp_is_candidate_scoped_and_employer_denied(auth_context):
    client, private_key, settings = auth_context
    candidate_headers = _headers(private_key, settings, sub=f"fsp-owner-{uuid4().hex}")
    other_headers = _headers(private_key, settings, sub=f"fsp-other-{uuid4().hex}")
    employer_headers = _headers(
        private_key,
        settings,
        sub=f"fsp-employer-{uuid4().hex}",
        role="employer",
    )
    _grant_processing_consent(client, candidate_headers)
    linked = client.post(
        "/api/v1/candidate/fsp-link",
        headers=candidate_headers,
        json={"fsp_id": "FSP-DEMO-001"},
    )
    assert linked.status_code == 201

    other = client.get("/api/v1/candidate/fsp", headers=other_headers)
    assert other.status_code == 200
    assert other.json()["status"] == "not_linked"

    denied = client.get("/api/v1/candidate/fsp", headers=employer_headers)
    assert denied.status_code == 403
    assert denied.json()["error"]["code"] == "ROLE_REQUIRED"
