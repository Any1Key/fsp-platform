"""Application settings loaded at the infrastructure boundary."""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime settings shared by the API and database adapter.

    The SQLite default keeps imports and unit tests safe when Compose-provided
    environment variables are absent. Deployments must provide PostgreSQL via
    ``DATABASE_URL``.
    """

    app_env: str = "development"
    database_url: str = "sqlite+pysqlite:///:memory:"
    db_pool_size: int = 5
    db_max_overflow: int = 10
    keycloak_issuer: str = "http://localhost:8081/realms/fsp"
    keycloak_jwks_url: str = "http://keycloak:8080/realms/fsp/protocol/openid-connect/certs"
    keycloak_client_id: str = "fsp-web"
    keycloak_jwks_cache_seconds: int = 300
    require_verified_email: bool = True
    privacy_policy_version: str = "2026-10-06"
    adult_age_years: int = Field(default=18, ge=1, le=100)
    minor_consent_document_policy_version: str = "2026-10-06"
    minor_consent_document_max_bytes: int = Field(default=10 * 1024 * 1024, ge=1)
    resume_max_bytes: int = Field(default=10 * 1024 * 1024, ge=1)
    canonical_exposure_window_days: int = Field(default=90, ge=1, le=3650)
    private_storage_dir: str = "/var/lib/fsp/private"
    cors_allowed_origins: str = "http://localhost:3000,http://127.0.0.1:3000"

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.cors_allowed_origins.split(",") if origin.strip()]

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the process-wide immutable-by-convention settings instance."""

    return Settings()
