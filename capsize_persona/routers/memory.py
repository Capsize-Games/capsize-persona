"""Inspect/edit a persona's stored memory."""

from fastapi import APIRouter, Depends, HTTPException, status

from capsize_persona.auth import require_api_key
from capsize_persona.deps import SessionDep
from capsize_persona.models import MemoryFact
from capsize_persona.schemas import MemoryFactOut

router = APIRouter(
    prefix="/personas",
    tags=["memory"],
    dependencies=[Depends(require_api_key)],
)


@router.get("/{persona_id}/memory", response_model=list[MemoryFactOut])
def list_memory(
    persona_id: int, conversation_key: str, session: SessionDep
) -> list[MemoryFact]:
    """List facts stored for one persona's conversation."""
    return list(
        session.query(MemoryFact)
        .filter_by(persona_id=persona_id, conversation_key=conversation_key)
        .order_by(MemoryFact.created_at)
    )


@router.delete(
    "/{persona_id}/memory/{fact_id}", status_code=status.HTTP_204_NO_CONTENT
)
def delete_fact(persona_id: int, fact_id: int, session: SessionDep) -> None:
    """Remove a stored fact - memory needs to be fixable, not append-only."""
    fact = session.get(MemoryFact, fact_id)
    if fact is None or fact.persona_id != persona_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Fact not found"
        )
    session.delete(fact)
    session.commit()
