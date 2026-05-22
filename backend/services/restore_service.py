import hashlib
import json
import logging
import shutil
import zipfile
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import select
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
from backend.schemas.backup import RestoreBackupResult, RestoreRecordRead
from backend.services import backup_integrity_service
from backend.services.project_service import project_dir, remove_project_dir

logger = logging.getLogger(__name__)

EXPECTED_APP_NAME = "工程图纸智能台账识别系统"
PROJECT_DATA_PATH = "database/project_data.json"
MANIFEST_PATH = "backup_manifest.json"
PATH_COLUMNS = {
    DrawingFile: ["storage_path", "converted_file_path"],
    DrawingSheet: ["thumbnail_path", "preview_path", "title_crop_path", "cad_preview_path"],
    RecognitionRun: ["output_path"],
    CadConversionRun: ["source_path", "target_path"],
    ExportRecord: ["file_path"],
}


def restore_project_backup_as_new_project(
    db: Session,
    backup_id: int,
    restore_mode: str = "new_project",
) -> RestoreBackupResult:
    if restore_mode != "new_project":
        raise restore_http_error(
            status.HTTP_400_BAD_REQUEST,
            "RESTORE_MODE_NOT_SUPPORTED",
            "当前版本仅支持恢复为新项目，不支持覆盖已有项目。",
        )

    backup = db.get(BackupRecord, backup_id)
    if backup is None:
        raise restore_http_error(
            status.HTTP_404_NOT_FOUND,
            "RESTORE_BACKUP_NOT_FOUND",
            "备份记录不存在。",
        )

    backup_path = settings.root_dir / backup.file_path
    if not backup_path.exists() or not backup_path.is_file():
        raise restore_http_error(
            status.HTTP_404_NOT_FOUND,
            "RESTORE_BACKUP_FILE_NOT_FOUND",
            "备份文件不存在，无法恢复。",
        )

    manifest: dict[str, Any] | None = None
    project_data: dict[str, Any] | None = None
    restore_record: RestoreRecord | None = None
    new_project_id: int | None = None

    try:
        manifest, project_data = read_and_validate_backup(backup_path)
        source_project = project_data.get("project") or manifest.get("project") or {}
        source_project_name = source_project.get("name") or backup.file_name
        old_project_id = int(source_project.get("id") or backup.project_id)

        restore_record = RestoreRecord(
            source_backup_id=backup.id,
            source_project_name=source_project_name,
            restore_mode="new_project",
            status="running",
            created_at=datetime.now(UTC),
        )
        db.add(restore_record)
        db.flush()

        new_project_name = unique_restored_project_name(db, source_project_name)
        new_project = Project(
            name=new_project_name,
            description=source_project.get("description"),
            status=source_project.get("status") or "active",
        )
        db.add(new_project)
        db.flush()
        new_project_id = new_project.id

        target_dir = project_dir(new_project_id)
        if target_dir.exists():
            raise RestoreFailure("RESTORE_PATH_INVALID", "恢复目标项目目录已存在。")
        extract_project_files(backup_path, target_dir)

        id_maps = restore_project_data(db, project_data, old_project_id, new_project_id)
        restored_counts = restored_counts_from_data(project_data)

        restore_record.new_project_id = new_project_id
        restore_record.status = "success"
        db.commit()
        db.refresh(restore_record)
        db.refresh(new_project)

        return RestoreBackupResult(
            restore_id=restore_record.id,
            backup_id=backup.id,
            source_project_name=source_project_name,
            new_project_id=new_project.id,
            new_project_name=new_project.name,
            status=restore_record.status,
            restored_counts=restored_counts,
            created_at=restore_record.created_at,
        )
    except HTTPException as exc:
        db.rollback()
        cleanup_failed_restore(new_project_id)
        write_failed_restore_record(db, backup, manifest, restore_mode, exc.detail)
        raise
    except RestoreFailure as exc:
        db.rollback()
        cleanup_failed_restore(new_project_id)
        write_failed_restore_record(
            db,
            backup,
            manifest,
            restore_mode,
            {"error_code": exc.error_code, "message": exc.message},
        )
        raise restore_http_error(status.HTTP_400_BAD_REQUEST, exc.error_code, exc.message) from exc
    except Exception as exc:
        db.rollback()
        cleanup_failed_restore(new_project_id)
        write_failed_restore_record(
            db,
            backup,
            manifest,
            restore_mode,
            {"error_code": "RESTORE_FAILED", "message": "项目恢复失败。"},
        )
        logger.exception("Failed to restore backup %s", backup_id)
        raise restore_http_error(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            "RESTORE_FAILED",
            "项目恢复失败。",
        ) from exc


def list_restores(db: Session) -> list[RestoreRecordRead]:
    records = db.scalars(select(RestoreRecord).order_by(RestoreRecord.created_at.desc())).all()
    return [
        RestoreRecordRead(
            restore_id=record.id,
            source_backup_id=record.source_backup_id,
            source_project_name=record.source_project_name,
            new_project_id=record.new_project_id,
            restore_mode=record.restore_mode,
            status=record.status,
            created_at=record.created_at,
            error_code=record.error_code,
            error_message=record.error_message,
        )
        for record in records
    ]


def read_and_validate_backup(backup_path: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    try:
        with zipfile.ZipFile(backup_path) as archive:
            names = set(archive.namelist())
            if MANIFEST_PATH not in names:
                raise RestoreFailure("BACKUP_MANIFEST_MISSING", "备份包缺少 backup_manifest.json。")
            if PROJECT_DATA_PATH not in names:
                raise RestoreFailure("BACKUP_DATA_MISSING", "备份包缺少 database/project_data.json。")

            manifest = json.loads(archive.read(MANIFEST_PATH).decode("utf-8"))
            project_data = json.loads(archive.read(PROJECT_DATA_PATH).decode("utf-8"))
            verify = backup_integrity_service.check_backup_package_integrity(backup_path)
            blocking_errors = [
                error
                for error in verify.errors
                if error.startswith("BACKUP_CHECKSUM_FAILED")
                or error.startswith("BACKUP_PROJECT_DATA_INVALID")
            ]
            if blocking_errors:
                first = blocking_errors[0]
                error_code, _, message = first.partition(": ")
                raise RestoreFailure(error_code, message or "备份包校验失败。")
            validate_manifest(manifest, names, archive)
            validate_project_data(project_data)
            return manifest, project_data
    except RestoreFailure:
        raise
    except zipfile.BadZipFile as exc:
        raise RestoreFailure("RESTORE_FAILED", "备份包不是有效 zip 文件。") from exc
    except json.JSONDecodeError as exc:
        raise RestoreFailure("RESTORE_FAILED", "备份包 JSON 数据无法解析。") from exc


def validate_manifest(manifest: dict[str, Any], names: set[str], archive: zipfile.ZipFile) -> None:
    if manifest.get("backup_type") != "project":
        raise RestoreFailure("BACKUP_VERSION_UNSUPPORTED", "备份类型不受支持。")
    if manifest.get("app_name") != EXPECTED_APP_NAME:
        raise RestoreFailure("BACKUP_VERSION_UNSUPPORTED", "备份包来源应用不受支持。")
    for item in manifest.get("files", []):
        relative_path = item.get("relative_path") or item.get("path")
        if not relative_path:
            continue
        if relative_path not in names:
            continue
        expected_sha = item.get("sha256")
        if expected_sha and zip_entry_sha256(archive, relative_path) != expected_sha:
            raise RestoreFailure("BACKUP_CHECKSUM_FAILED", f"备份文件校验失败：{relative_path}")


def validate_project_data(project_data: dict[str, Any]) -> None:
    required_keys = [
        "project",
        "import_batches",
        "drawing_files",
        "drawing_sheets",
        "recognition_runs",
        "recognition_candidates",
        "field_values",
        "field_evidence",
        "drawing_issues",
        "review_audit_logs",
        "cad_conversion_runs",
        "export_records",
    ]
    for key in required_keys:
        if key not in project_data:
            raise RestoreFailure("BACKUP_DATA_MISSING", f"备份数据缺少 {key}。")


def restore_project_data(
    db: Session,
    data: dict[str, Any],
    old_project_id: int,
    new_project_id: int,
) -> dict[str, dict[int, int]]:
    id_maps: dict[str, dict[int, int]] = {
        "project": {old_project_id: new_project_id},
        "batch": {},
        "file": {},
        "sheet": {},
        "run": {},
        "candidate": {},
        "field_value": {},
    }
    try:
        restore_rows(db, ImportBatch, data["import_batches"], id_maps, old_project_id, new_project_id)
        restore_rows(db, DrawingFile, data["drawing_files"], id_maps, old_project_id, new_project_id)
        restore_rows(db, DrawingSheet, data["drawing_sheets"], id_maps, old_project_id, new_project_id)
        restore_rows(db, RecognitionRun, data["recognition_runs"], id_maps, old_project_id, new_project_id)
        restore_rows(db, RecognitionCandidate, data["recognition_candidates"], id_maps, old_project_id, new_project_id)
        restore_rows(db, FieldValue, data["field_values"], id_maps, old_project_id, new_project_id)
        restore_rows(db, FieldEvidence, data["field_evidence"], id_maps, old_project_id, new_project_id)
        restore_rows(db, DrawingIssue, data["drawing_issues"], id_maps, old_project_id, new_project_id)
        restore_rows(db, ReviewAuditLog, data["review_audit_logs"], id_maps, old_project_id, new_project_id)
        restore_rows(db, CadConversionRun, data["cad_conversion_runs"], id_maps, old_project_id, new_project_id)
        restore_rows(db, ExportRecord, data["export_records"], id_maps, old_project_id, new_project_id)
        return id_maps
    except KeyError as exc:
        raise RestoreFailure("RESTORE_ID_MAPPING_FAILED", f"恢复 ID 映射失败：{exc}") from exc
    except Exception as exc:
        raise RestoreFailure("RESTORE_DATABASE_FAILED", "恢复数据库记录失败。") from exc


def restore_rows(
    db: Session,
    model: type[Any],
    rows: list[dict[str, Any]],
    id_maps: dict[str, dict[int, int]],
    old_project_id: int,
    new_project_id: int,
) -> None:
    for row in rows:
        old_id = row.get("id")
        payload = restored_payload(model, row, id_maps, old_project_id, new_project_id)
        instance = model(**payload)
        db.add(instance)
        db.flush()
        remember_id(model, id_maps, old_id, instance.id)


def restored_payload(
    model: type[Any],
    row: dict[str, Any],
    id_maps: dict[str, dict[int, int]],
    old_project_id: int,
    new_project_id: int,
) -> dict[str, Any]:
    payload: dict[str, Any] = {}
    for column in model.__table__.columns:
        name = column.name
        if name == "id" or name not in row:
            continue
        value = row[name]
        value = remap_column(model, name, value, id_maps, new_project_id)
        if name in PATH_COLUMNS.get(model, []):
            value = remap_project_path(value, old_project_id, new_project_id)
        payload[name] = coerce_column_value(column, value)
    return payload


def remap_column(
    model: type[Any],
    name: str,
    value: Any,
    id_maps: dict[str, dict[int, int]],
    new_project_id: int,
) -> Any:
    if value is None:
        return None
    if name == "project_id":
        return new_project_id
    if name == "batch_id":
        return id_maps["batch"][int(value)]
    if name == "file_id":
        return id_maps["file"][int(value)]
    if name == "source_file_id":
        return id_maps["file"][int(value)]
    if name == "sheet_id":
        return id_maps["sheet"][int(value)]
    if name == "run_id":
        return id_maps["run"].get(int(value))
    if name == "candidate_id":
        return id_maps["candidate"][int(value)]
    if name == "field_value_id":
        return id_maps["field_value"][int(value)]
    return value


def remember_id(
    model: type[Any],
    id_maps: dict[str, dict[int, int]],
    old_id: Any,
    new_id: int,
) -> None:
    if old_id is None:
        return
    key_by_model = {
        ImportBatch: "batch",
        DrawingFile: "file",
        DrawingSheet: "sheet",
        RecognitionRun: "run",
        RecognitionCandidate: "candidate",
        FieldValue: "field_value",
    }
    key = key_by_model.get(model)
    if key:
        id_maps[key][int(old_id)] = new_id


def remap_project_path(value: Any, old_project_id: int, new_project_id: int) -> Any:
    if not isinstance(value, str) or not value:
        return value
    return value.replace(
        f"app_data/projects/project_{old_project_id}/",
        f"app_data/projects/project_{new_project_id}/",
    ).replace(
        f"app_data\\projects\\project_{old_project_id}\\",
        f"app_data\\projects\\project_{new_project_id}\\",
    )


def coerce_column_value(column: Any, value: Any) -> Any:
    if value is None:
        return None
    try:
        python_type = column.type.python_type
    except NotImplementedError:
        return value
    if python_type is datetime and isinstance(value, str):
        return datetime.fromisoformat(value)
    if python_type is date and isinstance(value, str):
        return date.fromisoformat(value)
    return value


def extract_project_files(backup_path: Path, target_dir: Path) -> None:
    target_dir.mkdir(parents=True, exist_ok=False)
    with zipfile.ZipFile(backup_path) as archive:
        for name in archive.namelist():
            if not name.startswith("files/") or name.endswith("/"):
                continue
            relative = Path(name).relative_to("files")
            if ".." in relative.parts:
                raise RestoreFailure("RESTORE_PATH_INVALID", f"备份文件路径非法：{name}")
            output_path = target_dir / relative
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with archive.open(name) as source, output_path.open("wb") as target:
                shutil.copyfileobj(source, target)


def unique_restored_project_name(db: Session, source_name: str) -> str:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    base_name = f"{source_name}_恢复_{timestamp}"[:190]
    existing = set(db.scalars(select(Project.name).where(Project.name.like(f"{base_name}%"))).all())
    if base_name not in existing:
        return base_name
    for index in range(2, 1000):
        candidate = f"{base_name}_{index}"
        if candidate not in existing:
            return candidate
    return f"{base_name}_{datetime.now().strftime('%f')}"


def restored_counts_from_data(data: dict[str, Any]) -> dict[str, int]:
    return {
        "drawing_files": len(data.get("drawing_files", [])),
        "drawing_sheets": len(data.get("drawing_sheets", [])),
        "recognition_candidates": len(data.get("recognition_candidates", [])),
        "field_values": len(data.get("field_values", [])),
        "drawing_issues": len(data.get("drawing_issues", [])),
        "review_audit_logs": len(data.get("review_audit_logs", [])),
    }


def cleanup_failed_restore(new_project_id: int | None) -> None:
    if new_project_id is not None:
        remove_project_dir(new_project_id)


def write_failed_restore_record(
    db: Session,
    backup: BackupRecord,
    manifest: dict[str, Any] | None,
    restore_mode: str,
    detail: Any,
) -> None:
    if not isinstance(detail, dict):
        detail = {"error_code": "RESTORE_FAILED", "message": "项目恢复失败。"}
    source_project = (manifest or {}).get("project") or {}
    record = RestoreRecord(
        source_backup_id=backup.id,
        source_project_name=source_project.get("name"),
        restore_mode=restore_mode,
        status="failed",
        error_code=detail.get("error_code") or "RESTORE_FAILED",
        error_message=detail.get("message") or "项目恢复失败。",
        created_at=datetime.now(UTC),
    )
    db.add(record)
    db.commit()


def zip_entry_sha256(archive: zipfile.ZipFile, name: str) -> str:
    digest = hashlib.sha256()
    with archive.open(name) as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


class RestoreFailure(Exception):
    def __init__(self, error_code: str, message: str):
        super().__init__(message)
        self.error_code = error_code
        self.message = message


def restore_http_error(status_code: int, error_code: str, message: str) -> HTTPException:
    return HTTPException(status_code=status_code, detail={"error_code": error_code, "message": message})
