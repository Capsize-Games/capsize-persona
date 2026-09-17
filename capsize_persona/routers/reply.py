"""POST /personas/{id}/reply - the actual "what should I say" endpoint."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from capsize_persona.auth import require_api_key
from capsize_persona.config import Settings
from capsize_persona.deps import SessionDep, SettingsDep
from capsize_persona.generation import (
    STATUS_SENT,
    ReplyResult,
    extract_new_facts,
    generate_safe_reply,
)
from capsize_persona.models import MemoryFact, Persona
from capsize_persona.schemas import ReplyRequest, ReplyResponse

router = APIRouter(
    prefix="/personas",
    tags=["reply"],
    dependencies=[Depends(require_api_key)],
)


def _facts_for(
    session: Session, persona_id: int, conversation_key: str
) -> list[str]:
    rows = (
        session.query(MemoryFact)
        .filter_by(persona_id=persona_id, conversation_key=conversation_key)
        .order_by(MemoryFact.created_at)
        .all()
    )
    return [row.fact_text for row in rows]


def _remember(
    session: Session,
    persona_id: int,
    conversation_key: str,
    facts: list[str],
    is_sensitive: bool,
) -> None:
    for fact in facts:
        session.add(
            MemoryFact(
                persona_id=persona_id,
                conversation_key=conversation_key,
                fact_text=fact,
                is_sensitive=is_sensitive,
            )
        )
    session.commit()


def _maybe_remember(
    session: Session,
    settings: Settings,
    persona_id: int,
    body: ReplyRequest,
    existing: list[str],
) -> None:
    new_facts = extract_new_facts(
        settings, body.message, body.author, existing
    )
    _remember(
        session,
        persona_id,
        body.conversation_key,
        new_facts,
        body.source_is_private,
    )


def _generate(
    settings: Settings,
    persona: Persona,
    existing: list[str],
    body: ReplyRequest,
) -> ReplyResult:
    return generate_safe_reply(
        settings,
        persona,
        existing,
        body.message,
        body.author,
        body.speaker_name,
    )


def _run_reply(
    session: Session,
    settings: Settings,
    persona: Persona,
    body: ReplyRequest,
) -> ReplyResponse:
    existing = _facts_for(session, persona.id, body.conversation_key)
    result = _generate(settings, persona, existing, body)
    if result.status == STATUS_SENT:
        _maybe_remember(session, settings, persona.id, body, existing)
    return ReplyResponse(
        reply_text=result.text,
        status=result.status,
        safety_score=result.safety_score,
        attempts=result.attempts,
    )


@router.post("/{persona_id}/reply", response_model=ReplyResponse)
def reply(
    persona_id: int,
    body: ReplyRequest,
    session: SessionDep,
    settings: SettingsDep,
) -> ReplyResponse:
    """Generate a voice-matched, safety-gated, memory-informed reply."""
    persona = session.get(Persona, persona_id)
    if persona is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Persona not found"
        )
    return _run_reply(session, settings, persona, body)
