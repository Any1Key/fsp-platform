"""SQLAlchemy engine and request-scoped session infrastructure."""

from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from .config import Settings, get_settings


def create_database_engine(settings: Settings | None = None) -> Engine:
    """Create the application engine from settings.

    The adapter uses a synchronous SQLAlchemy session because the current
    FastAPI domain services are synchronous. SQLite receives a thread-safe
    configuration for tests; PostgreSQL receives connection health checks and
    bounded pooling.
    """

    resolved = settings or get_settings()
    url = resolved.database_url
    engine_options: dict[str, Any] = {
        "future": True,
        "pool_pre_ping": True,
    }

    if url.startswith("sqlite"):
        engine_options["connect_args"] = {"check_same_thread": False}
        if ":memory:" in url:
            # A single connection keeps an in-memory schema available to the
            # TestClient and the session that created it.
            engine_options["poolclass"] = StaticPool
    else:
        engine_options["pool_size"] = resolved.db_pool_size
        engine_options["max_overflow"] = resolved.db_max_overflow

    return create_engine(url, **engine_options)


engine = create_database_engine()
SessionFactory = sessionmaker(
    bind=engine,
    autoflush=False,
    expire_on_commit=False,
    class_=Session,
)


def get_db_session() -> Iterator[Session]:
    """Yield one session per request and roll back failed requests."""

    session = SessionFactory()
    try:
        yield session
    except BaseException:
        session.rollback()
        raise
    finally:
        session.close()


@contextmanager
def session_scope(factory: sessionmaker = SessionFactory) -> Iterator[Session]:
    """Run service work in an explicit transaction and close the session."""

    session = factory()
    try:
        with session.begin():
            yield session
    finally:
        session.close()
