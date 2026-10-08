import importlib.util
from pathlib import Path
from types import SimpleNamespace

from alembic.config import Config
from sqlalchemy import create_engine, inspect, text

from alembic import command


def _load_application_acceptance_migration():
    path = Path(__file__).parents[1] / "alembic/versions/20261008_0024_application_acceptance.py"
    spec = importlib.util.spec_from_file_location("application_acceptance_migration", path)
    assert spec and spec.loader
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    return migration


def _alembic_config(database_url: str) -> Config:
    config = Config(str(Path(__file__).parents[1] / "alembic.ini"))
    config.set_main_option("sqlalchemy.url", database_url)
    return config


def test_application_acceptance_postgresql_path_preserves_foreign_key_dependencies(
    monkeypatch,
):
    migration = _load_application_acceptance_migration()
    operations = []

    class FakeOperations:
        def get_bind(self):
            return SimpleNamespace(dialect=SimpleNamespace(name="postgresql"))

        def drop_constraint(self, name, *, table_name, type_):
            operations.append(("drop", name, table_name, type_))

        def create_check_constraint(self, name, table_name, expression):
            operations.append(("create", name, table_name, expression))

        def batch_alter_table(self, *args, **kwargs):
            raise AssertionError("PostgreSQL migrations must not recreate FK-referenced tables")

    monkeypatch.setattr(migration, "op", FakeOperations())

    migration._replace_status_check(
        "application",
        "ck_application_status",
        "status IN ('submitted', 'accepted')",
    )

    assert operations == [
        ("drop", "ck_application_status", "application", "check"),
        ("create", "ck_application_status", "application", "status IN ('submitted', 'accepted')"),
    ]


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
            "employer_task_draft_feedback",
            "employer_task_draft_job",
            "task_assignment",
            "task_submission",
            "employer_evaluation",
            "vacancy",
            "application",
            "application_status_history",
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
        feedback_foreign_keys = inspect(engine).get_foreign_keys("employer_task_draft_feedback")
        assert {key["referred_table"] for key in feedback_foreign_keys} == {
            "hiring_need",
            "company",
            "user_identity",
        }
        job_foreign_keys = inspect(engine).get_foreign_keys("employer_task_draft_job")
        assert {key["referred_table"] for key in job_foreign_keys} == {
            "hiring_need",
            "company",
            "user_identity",
        }
        vacancy_foreign_keys = inspect(engine).get_foreign_keys("vacancy")
        assert {key["referred_table"] for key in vacancy_foreign_keys} == {
            "company",
            "specialization",
            "grade",
        }
        application_foreign_keys = inspect(engine).get_foreign_keys("application")
        assert {key["referred_table"] for key in application_foreign_keys} == {
            "vacancy",
            "candidate_profile",
        }
        application_history_foreign_keys = inspect(engine).get_foreign_keys(
            "application_status_history"
        )
        assert {key["referred_table"] for key in application_history_foreign_keys} == {
            "application"
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
