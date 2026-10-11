"""Application settings loaded at the infrastructure boundary."""

from functools import lru_cache
from urllib.parse import urlsplit

from pydantic import Field, field_validator
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
    local_ai_enabled: bool = False
    local_ai_base_url: str = "http://local-ai:11434"
    local_ai_model: str = ""
    local_ai_timeout_seconds: float = Field(default=60.0, gt=0, le=300)
    local_ai_rate_limit_per_minute: int = Field(default=5, ge=1, le=60)
    local_ai_max_active_jobs_per_company: int = Field(default=1, ge=1, le=10)

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.cors_allowed_origins.split(",") if origin.strip()]

    @field_validator("cors_allowed_origins")
    @classmethod
    def validate_cors_allowed_origins(cls, value: str) -> str:
        """Keep browser access explicit and limited to origin-only URLs."""

        origins = [origin.strip().rstrip("/") for origin in value.split(",") if origin.strip()]
        if not origins:
            raise ValueError("cors_allowed_origins must contain at least one explicit origin")
        for origin in origins:
            parsed = urlsplit(origin)
            if (
                origin == "*"
                or "*" in origin
                or parsed.scheme not in {"http", "https"}
                or not parsed.netloc
                or parsed.path not in {"", "/"}
                or parsed.query
                or parsed.fragment
                or parsed.username
                or parsed.password
            ):
                raise ValueError(f"invalid explicit CORS origin: {origin}")
        return ",".join(origins)

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the process-wide immutable-by-convention settings instance."""

    return Settings()
