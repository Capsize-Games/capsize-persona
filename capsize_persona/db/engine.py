"""SQLAlchemy engine/session setup."""

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker


def make_engine(database_url: str) -> Engine:
    """Create the engine, enabling the SQLite foreign-key pragma."""
    connect_args = (
        {"check_same_thread": False}
        if database_url.startswith("sqlite")
        else {}
    )
    return create_engine(database_url, connect_args=connect_args)


def make_session_factory(engine: Engine) -> sessionmaker[Session]:
    """Build a session factory bound to `engine`."""
    return sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
