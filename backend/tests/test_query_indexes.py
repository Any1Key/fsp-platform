from pathlib import Path

from alembic.config import Config
from sqlalchemy import create_engine, inspect

from alembic import command

AUDITED_INDEXES = {
    "ix_candidate_profile_discoverable_updated": (
        "candidate_profile",
        ("is_discoverable", "updated_at", "id"),
    ),
    "ix_hiring_need_skill_need_preference": (
        "hiring_need_skill",
        ("hiring_need_id", "preference", "skill_id"),
    ),
    "ix_match_candidate": ("talent_match", ("candidate_profile_id", "created_at")),
    "ix_invitation_employer_candidate_status": (
        "invitation",
        ("employer_identity_id", "candidate_profile_id", "status"),
    ),
    "ix_invitation_company_created": ("invitation", ("company_id", "created_at")),
    "ix_conversation_contact_conversation_created": (
        "conversation_contact_exchange",
        ("conversation_id", "created_at", "id"),
    ),
    "ix_employer_trust_report_status_created": (
        "employer_trust_report",
        ("status", "created_at", "id"),
    ),
}


def test_audited_query_paths_have_leading_column_coverage(tmp_path: Path, monkeypatch):
    # Alembic's env.py deliberately gives DATABASE_URL precedence over the
    # configured URL.  Keep this isolated schema contract on its temporary
    # SQLite database even when the suite runs inside Compose.
    monkeypatch.delenv("DATABASE_URL", raising=False)
    database_url = f"sqlite:///{tmp_path / 'query-indexes.sqlite'}"
    config = Config(str(Path(__file__).parents[1] / "alembic.ini"))
    config.set_main_option("sqlalchemy.url", database_url)
    command.upgrade(config, "head")
    engine = create_engine(database_url)
    try:
        database = inspect(engine)
        for index_name, (table, columns) in AUDITED_INDEXES.items():
            matching = [item for item in database.get_indexes(table) if item["name"] == index_name]
            assert len(matching) == 1
            assert tuple(matching[0]["column_names"]) == columns
    finally:
        engine.dispose()
