"""SQLAlchemy engine/session setup, shared with the rest of the fleet.

Re-exported from `capsize-commons`. The shared implementation additionally
turns on `PRAGMA foreign_keys` for SQLite (SQLite defaults it off, so
`ON DELETE CASCADE` would otherwise be inert) and enables `pool_pre_ping`.
"""

from __future__ import annotations

from capsize_commons.db import make_engine, make_session_factory

__all__ = ["make_engine", "make_session_factory"]
