"""Pydantic request/response models for the HTTP API."""

import datetime

from capsize_voice import CategoryData
from pydantic import BaseModel, Field


class PersonaCreate(BaseModel):
    """Body for POST /personas."""

    name: str = Field(min_length=1, max_length=120)
    style_guide: str = Field(min_length=1)
    exemplars: list[str] = Field(min_length=1)
    safety_categories: list[CategoryData] = Field(default_factory=list)
    safety_threshold: float = 1.0


class PersonaUpdate(BaseModel):
    """Body for PATCH /personas/{id}. All fields optional."""

    style_guide: str | None = Field(default=None, min_length=1)
    exemplars: list[str] | None = Field(default=None, min_length=1)
    safety_categories: list[CategoryData] | None = None
    safety_threshold: float | None = None


class PersonaOut(BaseModel):
    """What the API returns for a persona."""

    id: int
    name: str
    style_guide: str
    exemplars: list[str]
    safety_categories: list[CategoryData]
    safety_threshold: float
    created_at: datetime.datetime
    updated_at: datetime.datetime


class ReplyRequest(BaseModel):
    """Body for POST /personas/{id}/reply."""

    conversation_key: str = Field(min_length=1, max_length=255)
    message: str = Field(min_length=1)
    author: str = Field(min_length=1, max_length=120)

    # True when the caller knows this turn happened somewhere not
    # visible to everyone (e.g. a private Discord channel) - flags any
    # fact extracted from it as `MemoryFact.is_sensitive`.
    source_is_private: bool = False


class ReplyResponse(BaseModel):
    """What POST /personas/{id}/reply returns."""

    reply_text: str | None
    status: str
    safety_score: float | None
    attempts: int


class MemoryFactCreate(BaseModel):
    """Body for POST /personas/{id}/memory - a direct, known fact.

    For a caller that already knows a fact rather than relying on
    `/reply`'s own extraction (e.g. an AIRunner tool call telling the
    persona something outright).
    """

    conversation_key: str = Field(min_length=1, max_length=255)
    fact_text: str = Field(min_length=1, max_length=500)
    is_sensitive: bool = False


class MemoryFactOut(BaseModel):
    """What the memory endpoints return for one stored fact."""

    model_config = {"from_attributes": True}

    id: int
    conversation_key: str
    fact_text: str
    is_sensitive: bool
    created_at: datetime.datetime
