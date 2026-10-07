from pathlib import Path

from alembic.config import Config
from sqlalchemy import create_engine, inspect, text

from alembic import command


def _alembic_config(database_url: str) -> Config:
    config = Config(str(Path(__file__).parents[1] / "alembic.ini"))
    config.set_main_option("sqlalchemy.url", database_url)
    return config


def test_initial_migration_creates_and_removes_foundation_schema(tmp_path, monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    database = tmp_path / "foundation.sqlite"
    url = f"sqlite:///{database}"
    config = _alembic_config(url)

    command.upgrade(config, "head")
    engine = create_engine(url)
    try:
        tables = set(inspect(engine).get_table_names())
        assert {
            "user_identity",
            "candidate_profile",
            "specialization",
            "grade",
            "skill",
            "specialization_skill",
            "assessment_blueprint",
            "question_family",
            "question_template",
            "question_variant",
            "assessment_attempt",
            "assessment_attempt_item",
            "assessment_answer",
            "assessment_result",
            "audit_event",
            "privacy_request",
            "fsp_link",
            "fsp_achievement",
            "hiring_pipeline",
            "pipeline_stage",
            "employer_task",
            "employer_task_version",
            "employer_task_example",
            "task_assignment",
            "task_submission",
            "employer_evaluation",
            "alembic_version",
        } <= tables
        assert {
            column["name"]
            for column in inspect(engine).get_columns("candidate_profile")
        } >= {"display_name", "headline", "location", "date_of_birth"}

        foreign_keys = inspect(engine).get_foreign_keys("assessment_attempt_item")
        assert {key["referred_table"] for key in foreign_keys} == {
            "assessment_attempt",
            "question_family",
            "question_template",
            "question_variant",
        }
        taxonomy_foreign_keys = inspect(engine).get_foreign_keys("specialization_skill")
        assert {key["referred_table"] for key in taxonomy_foreign_keys} == {
            "specialization",
            "skill",
        }
        assert {
            column["name"]
            for column in inspect(engine).get_columns("fsp_achievement")
        } >= {
            "canonical_specialization_slug",
            "canonical_skill_slugs",
            "result_score",
            "result_label",
        }
        assert "pipeline_snapshot" in {
            column["name"] for column in inspect(engine).get_columns("invitation")
        }
        assignment_foreign_keys = inspect(engine).get_foreign_keys("task_assignment")
        assert {key["referred_table"] for key in assignment_foreign_keys} >= {
            "talent_match",
            "candidate_profile",
            "employer_task",
            "employer_task_version",
            "pipeline_stage",
        }
        evaluation_foreign_keys = inspect(engine).get_foreign_keys("employer_evaluation")
        assert {key["referred_table"] for key in evaluation_foreign_keys} == {
            "task_assignment",
            "user_identity",
        }
        example_foreign_keys = inspect(engine).get_foreign_keys("employer_task_example")
        assert {key["referred_table"] for key in example_foreign_keys} == {
            "employer_task_version",
            "company",
            "user_identity",
        }

        with engine.begin() as connection:
            connection.execute(
                text(
                    "INSERT INTO user_identity "
                    "(id, keycloak_sub, email, role) VALUES "
                    "('identity-1', 'kc-1', 'candidate@example.ru', 'candidate')"
                )
            )
            connection.execute(
                text(
                    "INSERT INTO candidate_profile (id, identity_id) "
                    "VALUES ('candidate-1', 'identity-1')"
                )
            )
            connection.execute(
                text(
                    "INSERT INTO specialization (id, slug, name) VALUES "
                    "('specialization-1', 'backend', 'Backend engineering')"
                )
            )
            connection.execute(
                text(
                    "INSERT INTO assessment_blueprint "
                    "(id, specialization_id, version, name, configuration) "
                    "VALUES ('blueprint-1', 'specialization-1', 1, 'test', '{}')"
                )
            )
    finally:
        engine.dispose()

    command.downgrade(config, "base")
    engine = create_engine(url)
    try:
        assert inspect(engine).get_table_names() == ["alembic_version"]
    finally:
        engine.dispose()
