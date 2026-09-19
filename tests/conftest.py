"""Shared pytest fixtures: an isolated app + database per test."""

from collections.abc import Iterator
from pathlib import Path

import pytest
from capsize_memory.db import Base as MemoryBase
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker

from capsize_persona.app import create_app
from capsize_persona.config import Settings, get_settings
from capsize_persona.db.base import Base
from capsize_persona.db.engine import make_engine, make_session_factory
from capsize_persona.deps import get_db_session

API_KEY = "test-api-key"


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    """A Settings instance for an isolated on-disk test database.

    A temp file rather than `:memory:`: the TestClient runs sync routes
    in a worker thread, and an in-memory SQLite database does not
    reliably survive a connection from a different thread than the one
    that created it.
    """
    db_path = tmp_path / "test.db"
    return Settings(
        database_url=f"sqlite:///{db_path}",
        api_key=API_KEY,
        openrouter_api_key="test-openrouter-key",
        generation_model="test-model",
    )


@pytest.fixture
def session_factory(settings: Settings) -> sessionmaker[Session]:
    """A session factory bound to a fresh in-memory SQLite schema."""
    engine = make_engine(settings.database_url)
    Base.metadata.create_all(engine)
    MemoryBase.metadata.create_all(engine)
    return make_session_factory(engine)


@pytest.fixture
def client(
    settings: Settings, session_factory: sessionmaker[Session]
) -> Iterator[TestClient]:
    """A TestClient wired to the isolated settings/database above."""
    app = create_app()
    app.dependency_overrides[get_settings] = lambda: settings

    def _override_session() -> Iterator[Session]:
        session = session_factory()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db_session] = _override_session
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def api_headers() -> dict[str, str]:
    """Header for the seeded test API key."""
    return {"X-API-Key": API_KEY}
