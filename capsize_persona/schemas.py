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


class RoomIdentity(BaseModel):
    """Room-identity fields shared by /reply and /should-interject.

    `platform`/`room_type`/`room_key`/`room_display_name`/`speaker_id`
    are all optional and additive: an older caller sending only
    `conversation_key` still works unmodified (it becomes the room's
    `external_key`, with `platform`/`room_type` falling back to
    "unknown") - see `rooms.resolve_room` for the exact fallback.
    `speaker_id` is a stable per-platform participant id (e.g. a
    Discord user id) - distinct from `author`, which is a display name
    and can change.
    """

    conversation_key: str = Field(min_length=1, max_length=255)
    platform: str | None = Field(default=None, max_length=32)
    room_type: str | None = Field(default=None, max_length=32)
    room_key: str | None = Field(default=None, max_length=255)
    room_display_name: str | None = Field(default=None, max_length=255)
    speaker_id: str | None = Field(default=None, max_length=255)


class ReplyRequest(RoomIdentity):
    """Body for POST /personas/{id}/reply."""

    message: str = Field(min_length=1)
    author: str = Field(min_length=1, max_length=120)

    # What the persona calls itself in this reply - e.g. "capsize" on
    # Discord, "Joe" on joecurlee.com. A required, per-call argument
    # rather than a `Persona` field: the same voice under a different
    # name in a different place is still one persona, not two.
    speaker_name: str = Field(min_length=1, max_length=120)

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


class ShouldInterjectRequest(RoomIdentity):
    """Body for POST /personas/{id}/should-interject."""

    message: str = Field(min_length=1)
    author: str = Field(min_length=1, max_length=120)


class ShouldInterjectResponse(BaseModel):
    """What POST /personas/{id}/should-interject returns."""

    interject: bool


class TurnCreate(RoomIdentity):
    """Body for POST /personas/{id}/turns - a direct, known turn.

    For a caller that already knows what was said rather than relying
    on /reply's own generate-and-record flow (e.g. a one-way outgoing
    log of a Bluesky post that actually went out - there's no
    "message" it was replying to).
    """

    speaker: str = Field(min_length=1, max_length=120)
    text: str = Field(min_length=1)
    is_sensitive: bool = False


class RoomOut(BaseModel):
    """What GET /personas/{id}/rooms returns, one row per room."""

    model_config = {"from_attributes": True}

    id: int
    platform: str
    room_type: str
    external_key: str
    display_name: str | None
    created_at: datetime.datetime
    last_active_at: datetime.datetime | None


class TurnOut(BaseModel):
    """What the turns endpoints return for one stored turn."""

    model_config = {"from_attributes": True}

    id: int
    room_id: int
    speaker: str
    text: str
    is_sensitive: bool
    created_at: datetime.datetime


class GenerateRequest(BaseModel):
    """Body for POST /personas/{id}/generate."""

    context: str = Field(min_length=1)
    count: int = Field(gt=0, le=20)

    # See `ReplyRequest.speaker_name` - same per-call argument, same
    # reason: one persona, many names depending on where it's posting.
    speaker_name: str = Field(min_length=1, max_length=120)


class GenerateResponse(BaseModel):
    """What POST /personas/{id}/generate returns."""

    candidates: list[str]


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
