"""List the rooms a persona has a presence in.

"Where is the bot talking, and to whom, at all times" - the direct
answer per Joe's stated goal, one query instead of scattered
per-platform ad hoc keys.
"""

from capsize_memory import Room
from fastapi import APIRouter, Depends

from capsize_persona.auth import require_api_key
from capsize_persona.deps import SessionDep
from capsize_persona.schemas import RoomOut

router = APIRouter(
    prefix="/personas",
    tags=["rooms"],
    dependencies=[Depends(require_api_key)],
)


@router.get("/{persona_id}/rooms", response_model=list[RoomOut])
def list_rooms(persona_id: int, session: SessionDep) -> list[Room]:
    """List every room this persona has a presence in.

    Room keys are namespaced `"{persona_id}:..."` internally (see
    `rooms.resolve_room`) - filtered here by that same prefix, most
    recently active first.
    """
    prefix = f"{persona_id}:%"
    return list(
        session.query(Room)
        .filter(Room.external_key.like(prefix))
        .order_by(Room.last_active_at.desc().nulls_last())
    )
