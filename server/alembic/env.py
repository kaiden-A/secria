import ssl
import sys
from logging.config import fileConfig
from pathlib import Path

from sqlalchemy import create_engine, pool

from alembic import context

# Make `app` importable when alembic runs from the server/ directory.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import models  # noqa: E402,F401  (register every model on Base.metadata)
from app.config import get_settings  # noqa: E402
from app.database import Base  # noqa: E402

config = context.config

# The URL comes from app settings (root .env); "%" must be escaped for
# configparser.
settings = get_settings()
config.set_main_option("sqlalchemy.url", settings.alembic_database_url.replace("%", "%%"))

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    pg8000 needs an explicit ssl_context; the URL has sslmode stripped because
    it is a libpq-only query parameter.
    """
    connect_args: dict[str, object] = {"timeout": 10}
    if settings.alembic_ssl_required:
        connect_args["ssl_context"] = ssl.create_default_context()

    connectable = create_engine(
        settings.alembic_database_url,
        poolclass=pool.NullPool,
        connect_args=connect_args,
    )

    with connectable.connect() as connection:
        # Autogenerate reports schema-qualified FKs and enum schemas as churn on
        # this database; that is a known Postgres reflection quirk. Review
        # migrations by hand and ignore those specific lines.
        context.configure(connection=connection, target_metadata=target_metadata)

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
