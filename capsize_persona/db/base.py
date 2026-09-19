"""ORM base and timezone-aware DateTime, shared with the rest of the fleet.

Re-exported from `capsize-commons` so the declarative base and the SQLite
UTC round-trip behaviour are identical across every Capsize service.
"""

from __future__ import annotations

from capsize_commons.db import Base, UtcDateTime

__all__ = ["Base", "UtcDateTime"]
