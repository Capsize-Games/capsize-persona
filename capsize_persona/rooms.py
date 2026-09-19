"""Room/participant resolution shared by /reply and /should-interject.

Both routers accept the same optional room-identity fields
(`RoomIdentity` in schemas.py) - this is the one place that turns
those fields (or their legacy `conversation_key`-only fallback) into
an actual `capsize_memory.Room`/`RoomParticipant`.
"""

from capsize_memory import (
    Room,
    RoomParticipant,
    get_or_create_participant,
    get_or_create_room,
    touch_room,
)
from sqlalchemy.orm import Session

from capsize_persona.schemas import RoomIdentity

_UNKNOWN = "unknown"


def resolve_room(
    session: Session, persona_id: int, body: RoomIdentity
) -> Room:
    """Resolve (or create) the room this request belongs to.

    Falls back to treating `conversation_key` as an opaque room key
    when the newer `platform`/`room_type`/`room_key` fields are
    omitted - an older caller sending only `conversation_key` still
    works unmodified. `capsize_memory.Room` has no notion of "persona"
    at all (deliberately - it's a generic, host-mounted package), so
    `persona_id` is folded into the room key here, at the one call
    site every persona shares this database through: two different
    personas answering in what happens to be the same
    platform/room_type/room_key (e.g. a coincidental key collision, or
    a caller bug) must never merge their conversations.
    """
    platform = body.platform or _UNKNOWN
    room_type = body.room_type or _UNKNOWN
    room_key = f"{persona_id}:{body.room_key or body.conversation_key}"
    room = get_or_create_room(
        session, platform, room_type, room_key, body.room_display_name
    )
    touch_room(session, room.id)
    return room


def resolve_participant(
    session: Session, room: Room, body: RoomIdentity, author: str
) -> RoomParticipant | None:
    """Resolve (or create) the speaker, when a stable id was sent."""
    if not body.speaker_id:
        return None
    return get_or_create_participant(session, room.id, body.speaker_id, author)
