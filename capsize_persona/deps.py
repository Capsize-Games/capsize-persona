"""Process-wide FastAPI dependencies: settings and the database session."""

from collections.abc import Generator
from functools import lru_cache
from typing import Annotated

from fastapi import Depends
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from capsize_persona.config import Settings, get_settings
from capsize_persona.db.engine import make_engine, make_session_factory


@lru_cache
def get_engine() -> Engine:
    """Build the process-wide SQLAlchemy engine, once."""
    return make_engine(get_settings().database_url)


@lru_cache
def get_session_factory() -> sessionmaker[Session]:
    """Build the process-wide session factory, once."""
    return make_session_factory(get_engine())


def get_db_session() -> Generator[Session, None, None]:
    """FastAPI dependency: yield one request-scoped session."""
    session = get_session_factory()()
    try:
        yield session
    finally:
        session.close()


SettingsDep = Annotated[Settings, Depends(get_settings)]
SessionDep = Annotated[Session, Depends(get_db_session)]
