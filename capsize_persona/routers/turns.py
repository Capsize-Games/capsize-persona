"""Inspect/clear a room's short-term turn log.

Mirrors routers/memory.py's pattern for MemoryFact, plus one addition
beyond that precedent: turns are naturally reset as a whole
conversation ("forget what we were just talking about") far more
often than an operator wants to delete one row at a time, so a bulk
clear-by-room endpoint exists alongside the single-turn delete.
"""

from capsize_memory import clear_turns as memory_clear_turns
from capsize_memory import delete_turn as memory_delete_turn
from capsize_memory import record_turn as memory_record_turn
from capsize_memory.models import ConversationTurn
from fastapi import APIRouter, Depends, HTTPException, status

from capsize_persona.auth import require_api_key
from capsize_persona.deps import SessionDep
from capsize_persona.models import Persona
from capsize_persona.rooms import resolve_participant, resolve_room
from capsize_persona.schemas import TurnCreate, TurnOut

router = APIRouter(
    prefix="/personas",
    tags=["turns"],
    dependencies=[Depends(require_api_key)],
)


@router.post(
    "/{persona_id}/turns",
    response_model=TurnOut,
    status_code=status.HTTP_201_CREATED,
)
def create_turn(
    persona_id: int, body: TurnCreate, session: SessionDep
) -> ConversationTurn:
    """Record a turn the caller already knows, bypassing /reply.

    For a one-way outgoing log (e.g. a Bluesky post that actually went
    out) - there's no incoming message this is a reply to.
    """
    if session.get(Persona, persona_id) is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Persona not found"
        )
    room = resolve_room(session, persona_id, body)
    participant = resolve_participant(session, room, body, body.speaker)
    turn = memory_record_turn(
        session,
        room.id,
        body.speaker,
        body.text,
        participant_id=participant.id if participant else None,
        is_sensitive=body.is_sensitive,
    )
    session.commit()
    return turn


@router.get(
    "/{persona_id}/rooms/{room_id}/turns", response_model=list[TurnOut]
)
def list_turns(
    persona_id: int, room_id: int, session: SessionDep
) -> list[ConversationTurn]:
    """List a room's stored turns, oldest first, full record."""
    return list(
        session.query(ConversationTurn)
        .filter_by(room_id=room_id)
        .order_by(ConversationTurn.created_at)
    )


@router.delete(
    "/{persona_id}/rooms/{room_id}/turns",
    status_code=status.HTTP_204_NO_CONTENT,
)
def clear_turns(persona_id: int, room_id: int, session: SessionDep) -> None:
    """Clear every turn for a room in one call."""
    memory_clear_turns(session, room_id)
    session.commit()


@router.delete(
    "/{persona_id}/turns/{turn_id}", status_code=status.HTTP_204_NO_CONTENT
)
def delete_turn(persona_id: int, turn_id: int, session: SessionDep) -> None:
    """Remove one stored turn - memory needs to be fixable, not append-only."""
    if not memory_delete_turn(session, turn_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Turn not found"
        )
    session.commit()
