"""CRUD endpoints for personas."""

import json

from fastapi import APIRouter, Depends, HTTPException, status

from capsize_persona.auth import require_api_key
from capsize_persona.deps import SessionDep
from capsize_persona.models import MemoryFact, Persona
from capsize_persona.schemas import PersonaCreate, PersonaOut, PersonaUpdate

router = APIRouter(
    prefix="/personas",
    tags=["personas"],
    dependencies=[Depends(require_api_key)],
)


def _to_out(persona: Persona) -> PersonaOut:
    return PersonaOut(
        id=persona.id,
        name=persona.name,
        style_guide=persona.style_guide,
        exemplars=json.loads(persona.exemplars_json),
        safety_categories=json.loads(persona.safety_categories_json),
        safety_threshold=persona.safety_threshold,
        created_at=persona.created_at,
        updated_at=persona.updated_at,
    )


def _get_or_404(session: SessionDep, persona_id: int) -> Persona:
    persona = session.get(Persona, persona_id)
    if persona is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Persona not found"
        )
    return persona


@router.get("", response_model=list[PersonaOut])
def list_personas(session: SessionDep) -> list[PersonaOut]:
    """List all personas."""
    personas = session.query(Persona).order_by(Persona.name).all()
    return [_to_out(p) for p in personas]


@router.post(
    "", response_model=PersonaOut, status_code=status.HTTP_201_CREATED
)
def create_persona(body: PersonaCreate, session: SessionDep) -> PersonaOut:
    """Create a persona."""
    persona = Persona(
        name=body.name,
        style_guide=body.style_guide,
        exemplars_json=json.dumps(body.exemplars),
        safety_categories_json=json.dumps(body.safety_categories),
        safety_threshold=body.safety_threshold,
    )
    session.add(persona)
    session.commit()
    session.refresh(persona)
    return _to_out(persona)


@router.get("/{persona_id}", response_model=PersonaOut)
def get_persona(persona_id: int, session: SessionDep) -> PersonaOut:
    """Fetch one persona."""
    return _to_out(_get_or_404(session, persona_id))


@router.get("/by-name/{name}", response_model=PersonaOut)
def get_persona_by_name(name: str, session: SessionDep) -> PersonaOut:
    """Fetch one persona by its unique name.

    Callers outside this service (an AIRunner tool call, a Discord
    bot's config) address a persona by its human-readable name, not
    the internal row id.
    """
    persona = session.query(Persona).filter_by(name=name).first()
    if persona is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Persona not found"
        )
    return _to_out(persona)


@router.patch("/{persona_id}", response_model=PersonaOut)
def update_persona(
    persona_id: int, body: PersonaUpdate, session: SessionDep
) -> PersonaOut:
    """Update a persona's voice/safety configuration."""
    persona = _get_or_404(session, persona_id)
    if body.style_guide is not None:
        persona.style_guide = body.style_guide
    if body.exemplars is not None:
        persona.exemplars_json = json.dumps(body.exemplars)
    if body.safety_categories is not None:
        persona.safety_categories_json = json.dumps(body.safety_categories)
    if body.safety_threshold is not None:
        persona.safety_threshold = body.safety_threshold
    session.commit()
    session.refresh(persona)
    return _to_out(persona)


@router.delete("/{persona_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_persona(persona_id: int, session: SessionDep) -> None:
    """Delete a persona and its memory."""
    persona = _get_or_404(session, persona_id)
    session.query(MemoryFact).filter_by(persona_id=persona_id).delete()
    session.delete(persona)
    session.commit()
