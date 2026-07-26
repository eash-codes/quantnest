"""Database engine and session management.

The engine is configured from ``DATABASE_URL`` and defaults to a local SQLite
file. Moving to PostgreSQL requires only an environment variable change:

    DATABASE_URL=postgresql+psycopg://user:pass@host:5432/quantnest
"""

from __future__ import annotations

import logging
import os
from contextlib import contextmanager
from typing import Iterator, Optional

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from .models import Base

logger = logging.getLogger(__name__)

DEFAULT_DATABASE_URL = "sqlite:///./quantnest.db"

_engine: Optional[Engine] = None
_session_factory: Optional[sessionmaker] = None


def get_database_url() -> str:
    return os.getenv("DATABASE_URL", DEFAULT_DATABASE_URL)


def _configure_sqlite(engine: Engine) -> None:
    """Apply SQLite pragmas needed for correctness under concurrent access."""

    @event.listens_for(engine, "connect")
    def _set_pragmas(dbapi_connection, _connection_record):  # pragma: no cover - driver hook
        cursor = dbapi_connection.cursor()
        # WAL allows readers to proceed during a write.
        cursor.execute("PRAGMA journal_mode=WAL")
        # SQLite does not enforce foreign keys unless asked.
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA busy_timeout=5000")
        cursor.close()


def get_engine() -> Engine:
    """Return the process-wide engine, creating it on first use."""
    global _engine

    if _engine is None:
        url = get_database_url()
        is_sqlite = url.startswith("sqlite")

        _engine = create_engine(
            url,
            echo=os.getenv("SQL_ECHO", "").lower() in {"1", "true", "yes"},
            future=True,
            # check_same_thread=False is required because FastAPI serves
            # requests from a thread pool.
            connect_args={"check_same_thread": False} if is_sqlite else {},
            pool_pre_ping=not is_sqlite,
        )

        if is_sqlite:
            _configure_sqlite(_engine)

        logger.info("Database engine initialised", extra={"dialect": _engine.dialect.name})

    return _engine


def get_session_factory() -> sessionmaker:
    global _session_factory

    if _session_factory is None:
        _session_factory = sessionmaker(
            bind=get_engine(),
            autoflush=False,
            autocommit=False,
            expire_on_commit=False,
            class_=Session,
        )

    return _session_factory


def init_db() -> None:
    """Create any missing tables. Safe to call on every startup."""
    Base.metadata.create_all(bind=get_engine())
    logger.info("Database schema ready")


@contextmanager
def session_scope() -> Iterator[Session]:
    """Transactional scope: commit on success, roll back on failure."""
    session = get_session_factory()()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def reset_engine() -> None:
    """Dispose of the engine and session factory. Used by tests."""
    global _engine, _session_factory

    if _engine is not None:
        _engine.dispose()

    _engine = None
    _session_factory = None
