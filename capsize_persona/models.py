"""ORM models."""

import datetime

from sqlalchemy import Boolean, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from capsize_persona.db.base import Base, UtcDateTime

__all__ = ["MemoryFact", "Persona"]


def _utcnow() -> datetime.datetime:
    return datetime.datetime.now(datetime.UTC)


class Persona(Base):
    """A voice + safety-policy configuration a caller can talk through.

    `exemplars_json`/`safety_categories_json` hold JSON-encoded
    `list[str]`/`list[CategoryData]` rather than child tables - both are
    small, always read and written as a whole, and never queried by
    individual entry, so a normalized table would add joins with no
    real benefit.
    """

    __tablename__ = "personas"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120), unique=True)
    style_guide: Mapped[str] = mapped_column(Text)
    exemplars_json: Mapped[str] = mapped_column(Text)
    safety_categories_json: Mapped[str] = mapped_column(Text)
    safety_threshold: Mapped[float] = mapped_column(Float, default=1.0)

    created_at: Mapped[datetime.datetime] = mapped_column(
        UtcDateTime, default=_utcnow
    )
    updated_at: Mapped[datetime.datetime] = mapped_column(
        UtcDateTime, default=_utcnow, onupdate=_utcnow
    )


class MemoryFact(Base):
    """One durable fact learned about a conversation partner.

    Scoped by `conversation_key`, an opaque caller-supplied identifier
    (e.g. "discord:guild123:user456") - this service has no opinion on
    what a conversation is, only that facts learned in one don't leak
    into another.
    """

    __tablename__ = "memory_facts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    persona_id: Mapped[int] = mapped_column(ForeignKey("personas.id"))
    conversation_key: Mapped[str] = mapped_column(String(255), index=True)
    fact_text: Mapped[str] = mapped_column(String(500))

    # Set when the caller flags the turn this was learned from as
    # having happened somewhere not visible to everyone (e.g. a
    # private Discord channel) - a note for whoever reviews memory
    # later, not a storage restriction this service enforces itself.
    is_sensitive: Mapped[bool] = mapped_column(Boolean, default=False)

    created_at: Mapped[datetime.datetime] = mapped_column(
        UtcDateTime, default=_utcnow
    )
