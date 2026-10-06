from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.orm import sessionmaker

from app.config import Settings
from app.db import create_database_engine, get_db_session, session_scope
from app.main import app


def test_session_scope_commits_and_rolls_back(tmp_path: Path) -> None:
    database_url = f"sqlite:///{tmp_path / 'sessions.sqlite'}"
    engine = create_database_engine(Settings(database_url=database_url))
    factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    try:
        with engine.begin() as connection:
            connection.execute(text("CREATE TABLE probe (id INTEGER PRIMARY KEY, value TEXT NOT NULL)"))

        with session_scope(factory) as session:
            session.execute(text("INSERT INTO probe (id, value) VALUES (1, 'committed')"))

        with pytest.raises(RuntimeError, match="force rollback"), session_scope(factory) as session:
            session.execute(text("INSERT INTO probe (id, value) VALUES (2, 'rolled back')"))
            raise RuntimeError("force rollback")

        with engine.connect() as connection:
            values = connection.execute(text("SELECT id, value FROM probe ORDER BY id")).all()
        assert values == [(1, "committed")]
    finally:
        engine.dispose()


def test_readiness_uses_a_real_database_session() -> None:
    engine = create_database_engine(Settings(database_url="sqlite+pysqlite:///:memory:"))
    factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

    def override_get_db_session():
        with factory() as session:
            yield session

    app.dependency_overrides[get_db_session] = override_get_db_session
    try:
        response = TestClient(app).get("/health/ready")
    finally:
        app.dependency_overrides.clear()
        engine.dispose()

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "ok"}
