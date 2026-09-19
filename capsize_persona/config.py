"""Runtime settings, read once from the environment."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """All configuration this service reads from the environment."""

    model_config = SettingsConfigDict(
        env_prefix="PERSONA_", env_file=".env", extra="ignore"
    )

    database_url: str = "sqlite:///./capsize_persona.db"

    # Checked against the caller's X-API-Key header on every request.
    # Empty by default so the module can be imported with no environment
    # configured; every request is rejected until this is set.
    api_key: str = ""

    # No default: see capsize_voice.generate's module docstring for why a
    # generic tool shouldn't pick a vendor's model for every caller.
    openrouter_api_key: str = ""
    generation_model: str = ""

    # Comma-separated OpenRouter upstream-provider pin, empty = auto-route.
    generation_provider_order_raw: str = ""

    # How many recent turn *exchanges* (one incoming message + one
    # reply, each) to fold into every /reply call as short-term
    # conversational context, separate from durable MemoryFacts.
    # 6 is enough to answer "summarize the conversation so far"
    # without letting the prompt grow unboundedly on long threads.
    history_turns: int = 6

    @property
    def generation_provider_order(self) -> list[str]:
        """Return `generation_provider_order_raw` split into providers."""
        return [
            p.strip()
            for p in self.generation_provider_order_raw.split(",")
            if p.strip()
        ]


@lru_cache
def get_settings() -> Settings:
    """Build Settings from the environment, once per process."""
    return Settings()
