# Fleet consolidation boundary

## Repository identity and deployment

`capsize-persona` is the public Capsize-Games repository at
https://github.com/Capsize-Games/capsize-persona. The owner recorded in the
project metadata is Capsize-Games; the package is MIT-licensed and supports
Python 3.11 and newer.

The service is deployed as the repository's Docker image. The image exposes
port `8879`, runs `alembic upgrade head` before starting
`python -m capsize_persona`, and uses `GET /health` for its Docker
healthcheck. The local development and GitHub identity are the same canonical
repository; no private checkout, generated tree, model weights, credentials,
or live deployment copy is part of this migration.

## Boundary decisions

| Surface | Decision | Authority and compatibility contract |
| --- | --- | --- |
| Settings and environment loading | Adopt | `capsize-commons[config]` owns the base settings/cache. Persona keeps the `PERSONA_` prefix and service-specific fields. |
| SQLAlchemy engine, session factory, declarative base, and UTC datetime | Adopt | `capsize-commons[db]` supplies the common primitives. Persona keeps its models, Alembic revisions, SQLite file, and schema lifecycle local. |
| Health and readiness registration | Adopt | `capsize-commons[web]` installs the routes. Persona preserves `/health` as `200 {"ok": true}` and `/ready` as the unauthenticated `200 {"status":"ready"}` response. |
| API-key comparison | Adopt | `capsize-commons[web]` supplies the constant-time comparison. Persona keeps `PERSONA_API_KEY`, `X-API-Key`, and the `401` response contract. |
| Persona models, generation orchestration, memory policy, and room behavior | Retain-local | These are product behavior above the shared platform and the `capsize-memory`/`capsize-voice` domain libraries. No extraction is proposed. |
| Voice and memory libraries | Retain as domain dependencies | `capsize-voice` and `capsize-memory` remain separate consumer-facing libraries. Their package release and source provenance are not replaced by this service audit. |
| Alembic migrations and persistence schema | Retain-local | The persona schema and migration history are product-specific. Shared SQLAlchemy primitives do not own tables or migration ordering. |
| FastAPI routers, API schemas, auth dependency wiring, and provider/model policy | Retain-local | Public route shapes, service authentication, model selection, safety gates, and upstream policy remain persona behavior. |
| Docker startup, port, healthcheck, and secret injection | Retain-local | Deployment semantics and `PERSONA_*` environment variables are service-specific and remain in this repository. |
| Native/game standards from hq#33 | Not applicable | This is a Python HTTP service, not a native or game repository. |

## Dependency authority

Versions below are the resolved versions in `uv.lock` at audit time. Minimum
constraints remain in `pyproject.toml`; provider and persistence policy is not
reduced to a shared package merely because a library is used by more than one
service.

| Dependency | Resolved version | Proposed authority | Exception or reason to retain local |
| --- | --- | --- | --- |
| Python | `>=3.11` | Repository runtime contract | Required by the service and CI matrix. |
| `capsize-commons[config,db,web]` | `0.1.2` | `capsize-commons` | Adopted for shared settings, database primitives, web routes, and API-key comparison. |
| `capsize-memory` | `0.1.0` | `capsize-memory` | Domain persistence library; the service consumes it rather than extracting its models. The checkout remains a Git/local source until its release path is proven. |
| `capsize-voice` | `0.1.0` | `capsize-voice` | Voice generation and safety domain library; provider/model behavior remains above the platform boundary. The checkout remains a Git/local source until its release path is proven. |
| FastAPI | `0.141.1` | Repository service stack | HTTP framework and route behavior are service-owned. |
| Uvicorn | `0.53.0` | Repository service stack | Process startup and port binding are deployment-specific. |
| SQLAlchemy | `2.0.54` | `capsize-commons` conventions plus repository schema | Common engine/base conventions are shared; persona tables and migrations remain local. |
| Alembic | `1.20.0` | Repository migration contract | Migration history is persona-specific. |
| Pydantic / pydantic-settings | `2.13.5` / `2.15.0` | Repository service stack | API schemas and `PERSONA_` settings are persona-specific. |
| pytest / Ruff / mypy | `9.1.1` / `0.16.8` / `2.3.1` | Repository development contract | Test, lint, and type-check tooling is run locally and in the existing CI matrix. |

## Extraction and compatibility evidence

This audit proposes no new extraction. The already-landed shared adoption has
focused consumers and compatibility tests:

| Consumer | Shared API shape | Evidence | Rollback/provenance |
| --- | --- | --- | --- |
| `capsize_persona/config.py` | `CapsizeSettings` plus cached `get_settings(Settings)` | Settings overrides and service tests exercise the existing dependency shape. | Revert the shared-health adoption commits to restore the prior local implementation; the shared package remains version-pinned. |
| `capsize_persona/db/{base,engine}.py` | `Base`, `UtcDateTime`, `make_engine`, and `make_session_factory` re-exports | The full persona suite exercises model/session behavior, including SQLite fixtures and migrations. | Revert the adoption commits; keep persona migrations and data untouched. |
| `capsize_persona/app.py` | `install_health_routes(app, health_body={"ok": True})` | `tests/test_health.py` asserts both response bodies and status codes. | Revert the health adoption commit; no route normalization is authorized. |
| `capsize_persona/auth.py` | `check_api_key` with the existing `X-API-Key` / `401` contract | Authenticated route tests cover the service API-key behavior. | Revert the shared helper adoption; retain the public auth shape. |

No consumer, API shape, compatibility test, or rollback plan exists for
extracting persona domain models, generation logic, migrations, credentials,
or deployment behavior, so those surfaces remain local.

## Protected state

This audit adds only the manifest, task runner, tests, and documentation. It
does not delete, archive, retire, or overwrite repositories, directories,
branches, issue history, generated output, secrets, private data, model
weights, or deployment copies. The release and dependency-provenance questions
for the `capsize-memory` and `capsize-voice` sources remain explicit follow-up
gates rather than being asserted as complete here.
