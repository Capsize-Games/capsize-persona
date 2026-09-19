"""POST /personas/{id}/should-interject - the ambient-posture decision.

Cheap, separate from /reply: an opted-in channel's ordinary chatter
runs through this on every message, not the full voice-generation
call - see capsize_voice.classify's module docstring for why.
"""

from capsize_memory import recent_turns as memory_turns
from fastapi import APIRouter, Depends, HTTPException, status

from capsize_persona.auth import require_api_key
from capsize_persona.deps import SessionDep, SettingsDep
from capsize_persona.generation import should_interject as generate_decision
from capsize_persona.models import Persona
from capsize_persona.rooms import resolve_room
from capsize_persona.schemas import (
    ShouldInterjectRequest,
    ShouldInterjectResponse,
)

router = APIRouter(
    prefix="/personas",
    tags=["should-interject"],
    dependencies=[Depends(require_api_key)],
)


@router.post(
    "/{persona_id}/should-interject", response_model=ShouldInterjectResponse
)
def should_interject(
    persona_id: int,
    body: ShouldInterjectRequest,
    session: SessionDep,
    settings: SettingsDep,
) -> ShouldInterjectResponse:
    """Decide whether the persona should reply to an ambient message."""
    if session.get(Persona, persona_id) is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Persona not found"
        )
    room = resolve_room(session, persona_id, body)
    # This endpoint only ever runs for ambient channel messages, never
    # a DM (those always force a reply, bypassing this entirely) - so
    # the destination is inherently public. Never fold in anything
    # learned somewhere private.
    turns = memory_turns(
        session, room.id, settings.history_turns, include_sensitive=False
    )
    session.commit()
    interject = generate_decision(settings, body.message, body.author, turns)
    return ShouldInterjectResponse(interject=interject)
