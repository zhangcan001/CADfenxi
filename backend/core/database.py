import logging
import sqlite3
from collections.abc import Generator
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from backend.core.config import settings


class Base(DeclarativeBase):
    pass


engine = create_engine(
    f"sqlite:///{settings.database_path}",
    connect_args={"check_same_thread": False},
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

logger = logging.getLogger(__name__)


def init_database() -> None:
    settings.ensure_storage()
    with sqlite3.connect(settings.database_path) as connection:
        connection.execute("PRAGMA journal_mode=WAL;")
    import backend.models.cad_conversion_run
    import backend.models.backup_record
    import backend.models.converter_setting
    import backend.models.drawing_file
    import backend.models.drawing_issue
    import backend.models.drawing_sheet
    import backend.models.export_record
    import backend.models.field_evidence
    import backend.models.field_value
    import backend.models.import_batch
    import backend.models.project
    import backend.models.recognition_candidate
    import backend.models.recognition_run
    import backend.models.review_audit_log
    import backend.models.restore_record

    Base.metadata.create_all(bind=engine)
    apply_alembic_migrations()


def apply_alembic_migrations() -> None:
    config = alembic_config()
    if config is None:
        return
    inspector = inspect(engine)
    try:
        if "alembic_version" in inspector.get_table_names():
            command.upgrade(config, "head")
        else:
            command.stamp(config, "head")
    except Exception:
        logger.exception("Alembic migration failed; database left in current state")


def alembic_config() -> Config | None:
    ini_path = settings.root_dir / "alembic.ini"
    if not ini_path.exists():
        return None
    config = Config(str(ini_path))
    config.set_main_option("sqlalchemy.url", f"sqlite:///{settings.database_path}")
    config.set_main_option("script_location", str(settings.root_dir / "backend" / "migrations"))
    return config


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def check_database() -> bool:
    try:
        init_database()
        with sqlite3.connect(settings.database_path) as connection:
            connection.execute("SELECT 1;").fetchone()
        return True
    except sqlite3.Error:
        return False
    except OSError:
        return False
