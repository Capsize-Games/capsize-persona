"""Generate a safety-gated reply in a persona's voice, informed by memory.

Ported and generalized from social-manager's `discord_bot.generate_safe_
reply` - the same generate -> score -> regenerate-on-flag loop, now the
one shared implementation instead of being duplicated per consumer, and
now folding a conversation's remembered facts into the prompt first.
"""

import json
from dataclasses import dataclass

from capsize_voice import (
    GenerationError,
    SafetyCategory,
    extract_facts,
    generate_reply,
    is_flagged,
    load_categories,
    score_text,
)

from capsize_persona.config import Settings
from capsize_persona.models import Persona

MAX_ATTEMPTS = 3

STATUS_SENT = "sent"
STATUS_SUPPRESSED = "suppressed"
STATUS_FAILED = "failed"


@dataclass(frozen=True)
class ReplyResult:
    """The outcome of `generate_safe_reply`."""

    text: str | None
    status: str
    safety_score: float | None
    attempts: int


@dataclass(frozen=True)
class _VoiceContext:
    api_key: str
    model: str
    extra_body: dict[str, object] | None
    style_guide: str
    exemplars: list[str]
    categories: list[SafetyCategory]
    threshold: float


def _fold_memory(style_guide: str, facts: list[str]) -> str:
    if not facts:
        return style_guide
    known = "\n".join(f"- {f}" for f in facts)
    return f"{style_guide}\n\nKnown context about this conversation:\n{known}"


def _extra_body(provider_order: list[str]) -> dict[str, object] | None:
    if not provider_order:
        return None
    return {"provider": {"order": provider_order, "allow_fallbacks": False}}


def _build_context(
    settings: Settings, persona: Persona, facts: list[str]
) -> _VoiceContext:
    return _VoiceContext(
        settings.openrouter_api_key,
        settings.generation_model,
        _extra_body(settings.generation_provider_order),
        _fold_memory(persona.style_guide, facts),
        json.loads(persona.exemplars_json),
        load_categories(json.loads(persona.safety_categories_json)),
        persona.safety_threshold,
    )


def _attempt_reply(
    ctx: _VoiceContext, message: str, author: str
) -> tuple[str | None, float]:
    """One generate+score attempt. `None` text means it was flagged."""
    reply = generate_reply(
        ctx.api_key,
        ctx.style_guide,
        ctx.exemplars,
        message,
        author,
        model=ctx.model,
        extra_body=ctx.extra_body,
    )
    score = score_text(reply, ctx.categories)
    if is_flagged(score, ctx.threshold):
        return None, score.total
    return reply, score.total


def _run_attempts(
    ctx: _VoiceContext, message: str, author: str
) -> ReplyResult:
    last_score: float | None = None
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            reply, last_score = _attempt_reply(ctx, message, author)
        except GenerationError:
            return ReplyResult(None, STATUS_FAILED, None, attempt)
        if reply is not None:
            return ReplyResult(reply, STATUS_SENT, last_score, attempt)
    return ReplyResult(None, STATUS_SUPPRESSED, last_score, MAX_ATTEMPTS)


def generate_safe_reply(
    settings: Settings,
    persona: Persona,
    facts: list[str],
    message: str,
    author: str,
) -> ReplyResult:
    """Generate a reply, regenerating if the safety scorer flags it.

    Suppresses (returns no text) if every attempt up to `MAX_ATTEMPTS`
    is flagged.
    """
    ctx = _build_context(settings, persona, facts)
    return _run_attempts(ctx, message, author)


def extract_new_facts(
    settings: Settings, message: str, author: str, existing_facts: list[str]
) -> list[str]:
    """Return new durable facts learned from `message`, best-effort.

    Never raises: a failed extraction just means nothing new was
    remembered this turn, not that the reply itself should fail.
    """
    try:
        return extract_facts(
            settings.openrouter_api_key,
            message,
            author,
            existing_facts,
            model=settings.generation_model,
            extra_body=_extra_body(settings.generation_provider_order),
        )
    except GenerationError:
        return []
