from logging.config import fileConfig
import os
from alembic import context
from sqlalchemy import engine_from_config, pool

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = None


def get_url() -> str:
    url = os.getenv("DATABASE_URL")
    if url:
        return url

    from app.core.config import settings
    return settings.database_url


def maybe_load_metadata() -> None:
    """
    Импортируем Base.metadata ТОЛЬКО если запущено:
      alembic -x use_model_metadata=1 revision --autogenerate -m "..."
    Для обычного 'upgrade' метаданные не нужны.
    """
    global target_metadata
    x_args = context.get_x_argument(as_dictionary=True)
    if x_args.get("use_model_metadata") in {"1", "true", "yes"}:
        from app.db.models.base import Base
        target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = get_url()
    maybe_load_metadata()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    url = get_url()
    connectable = engine_from_config(
        {"sqlalchemy.url": url}, prefix="sqlalchemy.", poolclass=pool.NullPool
    )
    with connectable.connect() as connection:
        maybe_load_metadata()
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
