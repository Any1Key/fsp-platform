from pathlib import Path
from types import SimpleNamespace

import pytest
from alembic.config import Config
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from alembic import command
from app import main
from app.auth import OIDCVerifier
from app.config import Settings
from app.db import get_db_session


class StaticJwksClient:
    def __init__(self, public_key):
        self.public_key = public_key

    def get_signing_key_from_jwt(self, token: str):
        del token
        return SimpleNamespace(key=self.public_key)


def _upgrade(database_url: str) -> None:
    config = Config(str(Path(__file__).parents[1] / "alembic.ini"))
    config.set_main_option("sqlalchemy.url", database_url)
    command.upgrade(config, "head")


@pytest.fixture()
def auth_context(tmp_path, monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    database_url = f"sqlite:///{tmp_path / 'auth.sqlite'}"
    _upgrade(database_url)
    engine = create_engine(database_url)
    factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    settings = Settings(
        database_url=database_url,
        keycloak_issuer="https://keycloak.test/realms/fsp",
        keycloak_client_id="fsp-web",
    )
    monkeypatch.setattr(
        main,
        "auth_verifier",
        OIDCVerifier(settings, jwks_client=StaticJwksClient(private_key.public_key())),
    )

    def override_get_db_session():
        with factory() as session:
            yield session

    main.app.dependency_overrides[get_db_session] = override_get_db_session
    with TestClient(main.app) as client:
        yield client, private_key, settings
    main.app.dependency_overrides.clear()
    engine.dispose()
