"""Alembic environment.

The URL comes from the service's own settings rather than alembic.ini, so
there is one place the deployed database is configured.
"""

from alembic import context
from sqlalchemy import engine_from_config, pool

from capsize_persona import models
from capsize_persona.config import get_settings
from capsize_persona.db.base import Base, UtcDateTime

config = context.config

# Importing the models module is what registers every table on the
# metadata; naming its export here states that dependency outright.
_REGISTERED_TABLES = tuple(models.__all__)

target_metadata = Base.metadata


def _render_item(type_: str, obj: object, autogen_context: object) -> object:
    """Render `UtcDateTime` as the plain DDL it actually produces.

    It's a type decorator: everything it does happens in Python, on the
    way to and from the driver. The column it creates is an ordinary
    timestamp-with-timezone, so that's what a migration should say -
    and it keeps a revision file from needing to import application
    code just to run.
    """
    if type_ == "type" and isinstance(obj, UtcDateTime):
        return "sa.DateTime(timezone=True)"
    return False


def run_migrations_offline() -> None:
    """Emit SQL to stdout instead of running it."""
    context.configure(
        url=get_settings().database_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        render_item=_render_item,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Apply migrations against the configured database."""
    section = config.get_section(config.config_ini_section) or {}
    section["sqlalchemy.url"] = get_settings().database_url
    connectable = engine_from_config(
        section, prefix="sqlalchemy.", poolclass=pool.NullPool
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            render_item=_render_item,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
