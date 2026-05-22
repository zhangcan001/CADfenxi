from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool

from alembic import context

from backend.core.config import settings as app_settings
from backend.core.database import Base
import backend.models.cad_conversion_run  # noqa: F401
import backend.models.converter_setting  # noqa: F401
import backend.models.drawing_file  # noqa: F401
import backend.models.drawing_issue  # noqa: F401
import backend.models.drawing_sheet  # noqa: F401
import backend.models.export_record  # noqa: F401
import backend.models.field_evidence  # noqa: F401
import backend.models.field_value  # noqa: F401
import backend.models.import_batch  # noqa: F401
import backend.models.project  # noqa: F401
import backend.models.recognition_candidate  # noqa: F401
import backend.models.recognition_run  # noqa: F401
import backend.models.review_audit_log  # noqa: F401


config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

config.set_main_option(
    "sqlalchemy.url", f"sqlite:///{app_settings.database_path}"
)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        render_as_batch=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            render_as_batch=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
