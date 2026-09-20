# capsize-persona

A standalone voice-matched, memory-backed reply service. Callers create
**personas** (a voice - style guide + exemplars - and a content-safety
policy), then ask a persona to reply to a message in a given
conversation. The service generates the reply in that voice, gates it
against the persona's safety categories (regenerating if flagged), and
remembers durable facts learned along the way so later replies in the
same conversation are informed by them.

It's a consumer of [capsize-voice](https://github.com/capsize-games/capsize-voice)
(voice generation, safety scoring, fact extraction), not a
reimplementation of it, and has no opinion on who's calling it - Discord
bots, an AI agent framework, anything that wants "reply as this persona,
remembering what it's learned" over HTTP.

## Fleet boundary

The service uses `capsize-commons` for shared settings, database primitives,
health/readiness routes, and constant-time API-key comparison. Persona models,
generation and safety orchestration, memory policy, migrations, provider/model
policy, Docker startup, and secret injection remain local. See
[the fleet consolidation boundary](docs/FLEET_CONSOLIDATION.md) for the
dependency table and rollback decisions.

## Auth

Every request needs an `X-API-Key` header matching `PERSONA_API_KEY`.
This is service-to-service auth, not a login system - there is no
concept of a human user anywhere in this service.

## API

- `POST /api/personas` - create a persona (`name`, `style_guide`,
  `exemplars`, `safety_categories`, `safety_threshold`).
- `GET /api/personas`, `GET /api/personas/{id}`,
  `PATCH /api/personas/{id}`, `DELETE /api/personas/{id}` - CRUD.
- `POST /api/personas/{id}/reply` - `{conversation_key, message,
  author}` -> `{reply_text, status, safety_score, attempts}`.
  `status` is one of `sent`, `suppressed` (every attempt was flagged),
  or `failed` (the model couldn't be reached).
- `GET /api/personas/{id}/memory?conversation_key=...` - inspect facts
  stored for one conversation.
- `DELETE /api/personas/{id}/memory/{fact_id}` - remove a bad fact.

## Local development

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install "capsize-voice @ git+https://github.com/Capsize-Games/capsize-voice.git@main"
pip install -e ".[dev]"

cp .env.example .env   # fill in PERSONA_API_KEY and PERSONA_OPENROUTER_API_KEY
alembic upgrade head
python -m capsize_persona   # serves on :8879
```

## Tests

```bash
pytest
```

## Checks

```bash
ruff check capsize_persona tests migrations
mypy capsize_persona
```
