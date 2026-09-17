"""The FastAPI application."""

from fastapi import FastAPI

from capsize_persona.routers import generate, memory, personas, reply


def create_app() -> FastAPI:
    """Build and configure the FastAPI application.

    Every route resolves settings per-request via the `get_settings`
    dependency, so tests isolate configuration with
    `app.dependency_overrides[get_settings]` rather than a constructor
    argument here.
    """
    app = FastAPI(title="Capsize Persona")
    app.include_router(personas.router, prefix="/api")
    app.include_router(reply.router, prefix="/api")
    app.include_router(generate.router, prefix="/api")
    app.include_router(memory.router, prefix="/api")

    @app.get("/health")
    def health() -> dict[str, bool]:
        """Report liveness for container healthchecks."""
        return {"ok": True}

    return app


app = create_app()
