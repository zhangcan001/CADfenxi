import hashlib
import json
import logging
import re
import zipfile
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

from backend.core.config import settings
from backend.models.backup_record import BackupRecord
from backend.models.cad_conversion_run import CadConversionRun
from backend.models.drawing_file import DrawingFile
from backend.models.drawing_issue import DrawingIssue
from backend.models.drawing_sheet import DrawingSheet
from backend.models.export_record import ExportRecord
from backend.models.field_evidence import FieldEvidence
from backend.models.field_value import FieldValue
from backend.models.import_batch import ImportBatch
from backend.models.project import Project
from backend.models.recognition_candidate import RecognitionCandidate
from backend.models.recognition_run import RecognitionRun
from backend.models.restore_record import RestoreRecord
from backend.models.review_audit_log import ReviewAuditLog
from backend.schemas.backup import BackupRecordRead, ProjectBackupResult
from backend.services.project_service import project_dir

logger = logging.getLogger(__name__)

SAFE_NAME_PATTERN = re.compile(r"[^A-Za-z0-9\u4e00-\u9fff._-]+")
BACKUP_APP_VERSION = settings.version


def create_project_backup(db: Session, project_id: int) -> ProjectBackupResult:
    project = db.get(Project, project_id)
    if project is None:
        raise backup_http_error(
            status.HTTP_404_NOT_FOUND,
            "BACKUP_PROJECT_NOT_FOUND",
            "项目不存在，无法创建备份。",
        )

    settings.ensure_storage()
    created_at = datetime.now(UTC)
    safe_project_name = safe_backup_name(project.name)
    file_name = f"project_backup_{project_id}_{safe_project_name}_{created_at:%Y%m%d_%H%M%S}.zip"
    backup_path = settings.backups_dir / file_name
    record = BackupRecord(
        project_id=project_id,
        backup_type="project",
        file_name=file_name,
        file_path=relative_to_root(backup_path),
        file_size=0,
        status="running",
        created_at=created_at,
    )
    db.add(record)
    db.flush()

    try:
        files = list_project_files(project_id)
        project_data = build_project_data(db, project_id)
        manifest = build_manifest(db, project, created_at, files)

        with zipfile.ZipFile(backup_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            archive.writestr("backup_manifest.json", dump_json(manifest))
            archive.writestr("database/project_data.json", dump_json(project_data))
            write_project_files(archive, project_id)

        record.file_size = backup_path.stat().st_size
        record.status = "success"
        db.commit()
        db.refresh(record)
        return backup_result(record)
    except Exception as exc:
        backup_path.unlink(missing_ok=True)
        record.status = "failed"
        record.error_code = "BACKUP_CREATE_FAILED"
        record.error_message = str(exc)
        db.commit()
        logger.exception("Failed to create project backup for project %s", project_id)
        raise backup_http_error(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            "BACKUP_CREATE_FAILED",
            "项目备份创建失败。",
        ) from exc


def list_backups(db: Session) -> list[BackupRecordRead]:
    records = db.scalars(select(BackupRecord).order_by(BackupRecord.created_at.desc())).all()
    return [backup_record_read(record) for record in records]


def list_project_backups(db: Session, project_id: int) -> list[BackupRecordRead]:
    records = db.scalars(
        select(BackupRecord)
        .where(BackupRecord.project_id == project_id)
        .order_by(BackupRecord.created_at.desc())
    ).all()
    return [backup_record_read(record) for record in records]


def delete_backup(db: Session, backup_id: int) -> None:
    record = db.get(BackupRecord, backup_id)
    if record is None:
        raise backup_http_error(
            status.HTTP_404_NOT_FOUND,
            "BACKUP_FILE_NOT_FOUND",
            "备份文件不存在。",
        )
    try:
        path = settings.root_dir / record.file_path
        path.unlink(missing_ok=True)
        db.query(RestoreRecord).filter(RestoreRecord.source_backup_id == backup_id).update(
            {RestoreRecord.source_backup_id: None},
            synchronize_session=False,
        )
        db.delete(record)
        db.commit()
    except Exception as exc:
        db.rollback()
        logger.exception("Failed to delete backup %s", backup_id)
        raise backup_http_error(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            "BACKUP_DELETE_FAILED",
            "备份删除失败。",
        ) from exc


def backup_file_path(db: Session, backup_id: int) -> tuple[Path, str]:
    record = db.get(BackupRecord, backup_id)
    if record is None or record.status != "success":
        raise backup_http_error(
            status.HTTP_404_NOT_FOUND,
            "BACKUP_FILE_NOT_FOUND",
            "备份文件不存在。",
        )
    path = settings.root_dir / record.file_path
    if not path.exists() or not path.is_file():
        raise backup_http_error(
            status.HTTP_404_NOT_FOUND,
            "BACKUP_FILE_NOT_FOUND",
            "备份文件不存在。",
        )
    return path, record.file_name


def build_manifest(
    db: Session,
    project: Project,
    created_at: datetime,
    files: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "backup_type": "project",
        "app_name": settings.app_name,
        "app_version": BACKUP_APP_VERSION,
        "created_at": serialize_value(created_at),
        "project": row_to_dict(project),
        "counts": {
            "import_batches": count_project_rows(db, ImportBatch, project.id),
            "drawing_files": count_project_rows(db, DrawingFile, project.id),
            "drawing_sheets": count_project_rows(db, DrawingSheet, project.id),
            "recognition_runs": count_project_rows(db, RecognitionRun, project.id),
            "recognition_candidates": count_project_rows(db, RecognitionCandidate, project.id),
            "field_values": count_project_rows(db, FieldValue, project.id),
            "field_evidence": count_field_evidence(db, project.id),
            "drawing_issues": count_project_rows(db, DrawingIssue, project.id),
            "review_audit_logs": count_project_rows(db, ReviewAuditLog, project.id),
            "cad_conversion_runs": count_project_rows(db, CadConversionRun, project.id),
            "export_records": count_project_rows(db, ExportRecord, project.id),
        },
        "files": files,
    }


def build_project_data(db: Session, project_id: int) -> dict[str, Any]:
    project = db.get(Project, project_id)
    return {
        "project": row_to_dict(project) if project else None,
        "import_batches": export_project_rows(db, ImportBatch, project_id),
        "drawing_files": export_project_rows(db, DrawingFile, project_id),
        "drawing_sheets": export_project_rows(db, DrawingSheet, project_id),
        "recognition_runs": export_project_rows(db, RecognitionRun, project_id),
        "recognition_candidates": export_project_rows(db, RecognitionCandidate, project_id),
        "field_values": export_project_rows(db, FieldValue, project_id),
        "field_evidence": export_field_evidence(db, project_id),
        "drawing_issues": export_project_rows(db, DrawingIssue, project_id),
        "review_audit_logs": export_project_rows(db, ReviewAuditLog, project_id),
        "cad_conversion_runs": export_project_rows(db, CadConversionRun, project_id),
        "export_records": export_project_rows(db, ExportRecord, project_id),
    }


def export_project_rows(db: Session, model: type[Any], project_id: int) -> list[dict[str, Any]]:
    rows = db.scalars(select(model).where(model.project_id == project_id).order_by(model.id)).all()
    return [row_to_dict(row) for row in rows]


def export_field_evidence(db: Session, project_id: int) -> list[dict[str, Any]]:
    rows = db.scalars(
        select(FieldEvidence)
        .join(FieldValue, FieldEvidence.field_value_id == FieldValue.id)
        .where(FieldValue.project_id == project_id)
        .order_by(FieldEvidence.id)
    ).all()
    return [row_to_dict(row) for row in rows]


def count_project_rows(db: Session, model: type[Any], project_id: int) -> int:
    statement: Select[tuple[int]] = select(func.count()).select_from(model).where(model.project_id == project_id)
    return int(db.scalar(statement) or 0)


def count_field_evidence(db: Session, project_id: int) -> int:
    statement = (
        select(func.count())
        .select_from(FieldEvidence)
        .join(FieldValue, FieldEvidence.field_value_id == FieldValue.id)
        .where(FieldValue.project_id == project_id)
    )
    return int(db.scalar(statement) or 0)


def list_project_files(project_id: int) -> list[dict[str, Any]]:
    base = project_dir(project_id)
    if not base.exists():
        return []
    files: list[dict[str, Any]] = []
    for path in sorted(item for item in base.rglob("*") if item.is_file()):
        relative_path = path.relative_to(base).as_posix()
        files.append(
            {
                "relative_path": f"files/{relative_path}",
                "size": path.stat().st_size,
                "sha256": file_sha256(path),
            }
        )
    return files


def write_project_files(archive: zipfile.ZipFile, project_id: int) -> None:
    base = project_dir(project_id)
    if not base.exists():
        return
    for path in sorted(item for item in base.rglob("*") if item.is_file()):
        archive.write(path, f"files/{path.relative_to(base).as_posix()}")


def row_to_dict(row: Any) -> dict[str, Any]:
    return {
        column.name: serialize_value(getattr(row, column.name))
        for column in row.__table__.columns
    }


def serialize_value(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, date):
        return value.isoformat()
    return value


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def safe_backup_name(name: str) -> str:
    safe_name = SAFE_NAME_PATTERN.sub("_", name).strip("._-")
    return (safe_name or "project")[:80]


def relative_to_root(path: Path) -> str:
    try:
        return path.relative_to(settings.root_dir).as_posix()
    except ValueError:
        return path.as_posix()


def dump_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2)


def backup_result(record: BackupRecord) -> ProjectBackupResult:
    return ProjectBackupResult(
        backup_id=record.id,
        project_id=record.project_id,
        file_name=record.file_name,
        file_path=record.file_path,
        file_size=record.file_size,
        created_at=record.created_at,
        download_url=f"/api/backups/{record.id}/download",
    )


def backup_record_read(record: BackupRecord) -> BackupRecordRead:
    return BackupRecordRead(
        backup_id=record.id,
        project_id=record.project_id,
        backup_type=record.backup_type,
        file_name=record.file_name,
        file_path=record.file_path,
        file_size=record.file_size,
        status=record.status,
        created_at=record.created_at,
        error_code=record.error_code,
        error_message=record.error_message,
        download_url=f"/api/backups/{record.id}/download",
    )


def backup_http_error(status_code: int, error_code: str, message: str) -> HTTPException:
    return HTTPException(status_code=status_code, detail={"error_code": error_code, "message": message})
