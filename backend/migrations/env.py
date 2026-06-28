"""
migrations/env.py — Alembic migration environment for Flask-Migrate.

This file is called by Alembic when running ``flask db migrate`` or
``flask db upgrade``.  It wires up the SQLAlchemy metadata from the Pepto
models so that autogenerate can diff the current schema.
"""

from __future__ import annotations

import logging
from logging.config import fileConfig

from alembic import context
from flask import current_app
from sqlalchemy import engine_from_config, pool

# ── Alembic Config object ─────────────────────────────────────────────────────
# This provides access to the .ini file values.
config = context.config

# ── Logging ───────────────────────────────────────────────────────────────────
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

logger = logging.getLogger("alembic.env")


def get_engine():
    """Return the SQLAlchemy engine bound to the current Flask app.

    Flask-Migrate stores the engine under different keys depending on the
    Flask-SQLAlchemy version.
    """
    try:
        # Flask-SQLAlchemy >= 3 and Flask-Migrate >= 4
        return current_app.extensions["migrate"].db.get_engine()
    except (TypeError, AttributeError, KeyError):
        # Fallback for older versions
        return current_app.extensions["migrate"].db.engine


def get_engine_url() -> str:
    """Return the DB URL string with ``%`` characters escaped for configparser."""
    try:
        return get_engine().url.render_as_string(hide_password=False).replace(
            "%", "%%"
        )
    except AttributeError:
        return str(get_engine().url).replace("%", "%%")


# Tell Alembic about the database URL so it can connect.
config.set_main_option("sqlalchemy.url", get_engine_url())

# ── Target metadata ───────────────────────────────────────────────────────────
# Import all models so their Table definitions are registered on the metadata.
# Flask-Migrate populates ``target_metadata`` via the Migrate extension.

target_db = current_app.extensions["migrate"].db


def get_metadata():
    """Return the SQLAlchemy MetaData object that Alembic should diff against."""
    if hasattr(target_db, "metadatas"):
        # Flask-SQLAlchemy >= 3 with multiple binds
        return target_db.metadatas[None]
    return target_db.metadata


# ── Offline mode ──────────────────────────────────────────────────────────────


def run_migrations_offline() -> None:
    """Run migrations without an active DB connection.

    This emits SQL to stdout / a file rather than executing it.
    Useful for generating migration scripts to review before applying.
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=get_metadata(),
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()


# ── Online mode ───────────────────────────────────────────────────────────────


def run_migrations_online() -> None:
    """Run migrations against a live database connection."""

    def process_revision_directives(context, revision, directives):
        """Prevent empty migration files from being generated."""
        if getattr(config.cmd_opts, "autogenerate", False):
            script = directives[0]
            if script.upgrade_ops.is_empty():
                directives[:] = []
                logger.info("No schema changes detected; empty migration skipped.")

    conf_args = current_app.extensions["migrate"].configure_args
    if conf_args.get("process_revision_directives") is None:
        conf_args["process_revision_directives"] = process_revision_directives

    connectable = get_engine()

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=get_metadata(),
            compare_type=True,
            compare_server_default=True,
            **conf_args,
        )

        with context.begin_transaction():
            context.run_migrations()


# ── Entry point ───────────────────────────────────────────────────────────────

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
