"""POST /personas/{id}/generate - N candidate posts for a review queue."""

from fastapi import APIRouter, Depends, HTTPException, status

from capsize_persona.auth import require_api_key
from capsize_persona.deps import SessionDep, SettingsDep
from capsize_persona.generation import (
    GenerationError,
    generate_post_candidates,
)
from capsize_persona.models import Persona
from capsize_persona.schemas import GenerateRequest, GenerateResponse

router = APIRouter(
    prefix="/personas",
    tags=["generate"],
    dependencies=[Depends(require_api_key)],
)


@router.post("/{persona_id}/generate", response_model=GenerateResponse)
def generate(
    persona_id: int,
    body: GenerateRequest,
    session: SessionDep,
    settings: SettingsDep,
) -> GenerateResponse:
    """Generate `count` candidate posts in this persona's voice."""
    persona = session.get(Persona, persona_id)
    if persona is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Persona not found"
        )
    try:
        candidates = generate_post_candidates(
            settings, persona, body.context, body.count, body.speaker_name
        )
    except GenerationError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)
        ) from exc
    return GenerateResponse(candidates=candidates)
