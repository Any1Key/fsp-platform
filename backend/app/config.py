"""Application settings loaded at the infrastructure boundary."""

from functools import lru_cache

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

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the process-wide immutable-by-convention settings instance."""

    return Settings()
