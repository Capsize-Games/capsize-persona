"""Generate a safety-gated reply in a persona's voice, informed by memory.

Ported and generalized from social-manager's `discord_bot.generate_safe_
reply` - the same generate -> score -> regenerate-on-flag loop, now the
one shared implementation instead of being duplicated per consumer, and
now folding a conversation's remembered facts into the prompt first.
"""

import json
from dataclasses import dataclass

from capsize_memory import Turn
from capsize_voice import (
    GenerationError,
    SafetyCategory,
    extract_facts,
    generate_candidates,
    generate_reply,
    is_flagged,
    load_categories,
    score_text,
)
from capsize_voice import (
    should_interject as _voice_should_interject,
)

from capsize_persona.config import Settings
from capsize_persona.models import Persona

__all__ = [
    "STATUS_SENT",
    "GenerationError",
    "ReplyResult",
    "extract_new_facts",
    "generate_post_candidates",
    "generate_safe_reply",
    "should_interject",
]

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
    recent_turns: list[tuple[str, str]]


def _fold_identity(style_guide: str, speaker_name: str) -> str:
    identity = (
        f"You are {speaker_name}. Always refer to yourself by this "
        "name - never by any other name, even one that appears "
        "below in the style guide or in examples of this person's "
        "writing. The style guide shapes how you write, not who you "
        "say you are."
    )
    return f"{identity}\n\n{style_guide}"


def _fold_memory(style_guide: str, facts: list[str]) -> str:
    if not facts:
        return style_guide
    known = "\n".join(f"- {f}" for f in facts)
    return f"{style_guide}\n\nKnown context about this conversation:\n{known}"


def _extra_body(provider_order: list[str]) -> dict[str, object] | None:
    """Build the OpenRouter `provider` routing object, or `None`.

    `only` (not `allow_fallbacks: False`) is what actually restricts
    requests to this list while still retrying within it - the two
    look similar but `allow_fallbacks: False` on its own only ever
    tries the *first* entry in `order` and fails outright on any
    error from it, silently ignoring the rest of the list. Confirmed
    live: a lone-provider pin 429'd with no retry even with a second
    provider listed in `order`, until `only` was added too.
    """
    if not provider_order:
        return None
    return {"provider": {"order": provider_order, "only": provider_order}}


def _build_context(
    settings: Settings,
    persona: Persona,
    facts: list[str],
    recent_turns: list[Turn],
    speaker_name: str,
) -> _VoiceContext:
    style_guide = _fold_identity(persona.style_guide, speaker_name)
    style_guide = _fold_memory(style_guide, facts)
    return _VoiceContext(
        settings.openrouter_api_key,
        settings.generation_model,
        _extra_body(settings.generation_provider_order),
        style_guide,
        json.loads(persona.exemplars_json),
        load_categories(json.loads(persona.safety_categories_json)),
        persona.safety_threshold,
        [(turn.speaker, turn.text) for turn in recent_turns],
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
        recent_turns=ctx.recent_turns,
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
    recent_turns: list[Turn],
    message: str,
    author: str,
    speaker_name: str,
) -> ReplyResult:
    """Generate a reply, regenerating if the safety scorer flags it.

    Suppresses (returns no text) if every attempt up to `MAX_ATTEMPTS`
    is flagged. `speaker_name` is what the persona calls itself in
    this reply - a persona speaking as "capsize" on Discord and "Joe"
    on joecurlee.com is the same voice under two different names, not
    two personas, so this is a per-call argument, not a `Persona`
    field. `recent_turns` is the short-term conversational context
    (distinct from `facts`, the durable memory) - the same turns are
    reused across every retry attempt within this one call; only
    safety-flagging changes attempt to attempt, not history.
    """
    ctx = _build_context(settings, persona, facts, recent_turns, speaker_name)
    return _run_attempts(ctx, message, author)


def should_interject(
    settings: Settings,
    message: str,
    author: str,
    recent_turns: list[Turn],
) -> bool:
    """Return whether the persona should reply to an ambient message.

    Never raises: a failed classification call defaults to not
    interjecting, the same "fail toward silence" posture the Discord
    gateway's own kill-switch already uses.
    """
    try:
        return _voice_should_interject(
            settings.openrouter_api_key,
            message,
            author,
            [(turn.speaker, turn.text) for turn in recent_turns],
            model=settings.generation_model,
            extra_body=_extra_body(settings.generation_provider_order),
        )
    except GenerationError:
        return False


def generate_post_candidates(
    settings: Settings,
    persona: Persona,
    context: str,
    count: int,
    speaker_name: str,
) -> list[str]:
    """Return up to `count` distinct candidate posts about `context`.

    An original post, not a reply - no conversation memory is folded
    in the way `generate_safe_reply` folds remembered facts, since a
    stand-alone post has no prior turn to be informed by. Candidates
    go to a human review queue, same as `capsize_voice.
    generate_candidates`'s own callers - no safety-score gate here;
    that gate is Joe approving each one, not an automated filter.
    """
    style_guide = _fold_identity(persona.style_guide, speaker_name)
    return generate_candidates(
        settings.openrouter_api_key,
        style_guide,
        json.loads(persona.exemplars_json),
        context,
        count,
        model=settings.generation_model,
        extra_body=_extra_body(settings.generation_provider_order),
    )


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
