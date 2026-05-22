import sqlite3
from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from backend.core.config import settings


class Base(DeclarativeBase):
    pass


engine = create_engine(
    f"sqlite:///{settings.database_path}",
    connect_args={"check_same_thread": False},
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_database() -> None:
    settings.ensure_storage()
    with sqlite3.connect(settings.database_path) as connection:
        connection.execute("PRAGMA journal_mode=WAL;")
    import backend.models.drawing_issue  # noqa: F401
    import backend.models.drawing_file  # noqa: F401
    import backend.models.drawing_sheet  # noqa: F401
    import backend.models.converter_setting  # noqa: F401
    import backend.models.cad_conversion_run  # noqa: F401
    import backend.models.export_record  # noqa: F401
    import backend.models.field_evidence  # noqa: F401
    import backend.models.field_value  # noqa: F401
    import backend.models.import_batch  # noqa: F401
    import backend.models.project  # noqa: F401
    import backend.models.recognition_candidate  # noqa: F401
    import backend.models.recognition_run  # noqa: F401
    import backend.models.review_audit_log  # noqa: F401

    Base.metadata.create_all(bind=engine)
    ensure_lightweight_migrations()


def ensure_lightweight_migrations() -> None:
    with sqlite3.connect(settings.database_path) as connection:
        file_columns = {
            row[1] for row in connection.execute("PRAGMA table_info(drawing_files);").fetchall()
        }
        if file_columns and "error_code" not in file_columns:
            connection.execute("ALTER TABLE drawing_files ADD COLUMN error_code VARCHAR(64);")
        if file_columns and "source_format" not in file_columns:
            connection.execute(
                "ALTER TABLE drawing_files "
                "ADD COLUMN source_format VARCHAR(20) NOT NULL DEFAULT 'pdf';"
            )
        if file_columns and "parse_status" not in file_columns:
            connection.execute("ALTER TABLE drawing_files ADD COLUMN parse_status VARCHAR(32);")
        if file_columns and "parse_error_code" not in file_columns:
            connection.execute(
                "ALTER TABLE drawing_files ADD COLUMN parse_error_code VARCHAR(64);"
            )
        if file_columns and "parse_error_message" not in file_columns:
            connection.execute("ALTER TABLE drawing_files ADD COLUMN parse_error_message TEXT;")
        if file_columns and "converted_format" not in file_columns:
            connection.execute("ALTER TABLE drawing_files ADD COLUMN converted_format VARCHAR(20);")
        if file_columns and "converted_file_path" not in file_columns:
            connection.execute("ALTER TABLE drawing_files ADD COLUMN converted_file_path TEXT;")
        if file_columns and "convert_status" not in file_columns:
            connection.execute("ALTER TABLE drawing_files ADD COLUMN convert_status VARCHAR(32);")
        if file_columns and "convert_error_code" not in file_columns:
            connection.execute("ALTER TABLE drawing_files ADD COLUMN convert_error_code VARCHAR(64);")
        if file_columns and "convert_error_message" not in file_columns:
            connection.execute("ALTER TABLE drawing_files ADD COLUMN convert_error_message TEXT;")

        sheet_columns = {
            row[1] for row in connection.execute("PRAGMA table_info(drawing_sheets);").fetchall()
        }
        if sheet_columns and "title_crop_bbox" not in sheet_columns:
            connection.execute("ALTER TABLE drawing_sheets ADD COLUMN title_crop_bbox TEXT;")
        if sheet_columns and "title_crop_status" not in sheet_columns:
            connection.execute(
                "ALTER TABLE drawing_sheets "
                "ADD COLUMN title_crop_status VARCHAR(32) NOT NULL DEFAULT 'pending';"
            )
        if sheet_columns and "title_crop_error_code" not in sheet_columns:
            connection.execute(
                "ALTER TABLE drawing_sheets ADD COLUMN title_crop_error_code VARCHAR(64);"
            )
        if sheet_columns and "title_crop_error_message" not in sheet_columns:
            connection.execute(
                "ALTER TABLE drawing_sheets ADD COLUMN title_crop_error_message TEXT;"
            )


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
