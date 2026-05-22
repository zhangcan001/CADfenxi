import hashlib
import json
import zipfile
from pathlib import Path
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import func, select
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
from backend.models.review_audit_log import ReviewAuditLog
from backend.schemas.backup import BackupVerifyResult, ProjectIntegrityResult, ProjectPathCheck

MANIFEST_PATH = "backup_manifest.json"
PROJECT_DATA_PATH = "database/project_data.json"

PROJECT_MODELS = {
    "import_batches": ImportBatch,
    "drawing_files": DrawingFile,
    "drawing_sheets": DrawingSheet,
    "recognition_runs": RecognitionRun,
    "recognition_candidates": RecognitionCandidate,
    "field_values": FieldValue,
    "drawing_issues": DrawingIssue,
    "review_audit_logs": ReviewAuditLog,
    "cad_conversion_runs": CadConversionRun,
    "export_records": ExportRecord,
}

PATH_COLUMNS = {
    DrawingFile: ["storage_path", "converted_file_path"],
    DrawingSheet: ["thumbnail_path", "preview_path", "title_crop_path", "cad_preview_path"],
    RecognitionRun: ["output_path"],
    CadConversionRun: ["source_path", "target_path"],
    ExportRecord: ["file_path"],
}


def verify_backup_record(db: Session, backup_id: int) -> BackupVerifyResult:
    record = db.get(BackupRecord, backup_id)
    if record is None:
        raise integrity_http_error("BACKUP_FILE_NOT_FOUND", "备份记录不存在。", status.HTTP_404_NOT_FOUND)
    path = settings.root_dir / record.file_path
    if not path.exists():
        return BackupVerifyResult(
            backup_id=backup_id,
            valid=False,
            warnings=[],
            errors=["BACKUP_FILE_NOT_FOUND: 备份文件不存在。"],
            counts={"manifest_files": 0, "missing_files": 0, "checksum_failed": 0},
            summary=verify_summary(False, False, {"manifest_files": 0, "missing_files": 0, "checksum_failed": 0}),
        )
    return check_backup_package_integrity(path, backup_id=backup_id)


def check_backup_package_integrity(zip_path: Path, backup_id: int | None = None) -> BackupVerifyResult:
    warnings: list[str] = []
    errors: list[str] = []
    counts = {
        "manifest_files": 0,
        "missing_files": 0,
        "checksum_failed": 0,
        "manifest_count_mismatches": 0,
    }
    has_manifest = False
    has_project_data = False
    try:
        with zipfile.ZipFile(zip_path) as archive:
            names = set(archive.namelist())
            has_manifest = MANIFEST_PATH in names
            has_project_data = PROJECT_DATA_PATH in names
            if MANIFEST_PATH not in names:
                errors.append("BACKUP_MANIFEST_MISSING: 备份包缺少 backup_manifest.json。")
            if PROJECT_DATA_PATH not in names:
                errors.append("BACKUP_DATA_MISSING: 备份包缺少 database/project_data.json。")
            if errors:
                return BackupVerifyResult(
                    backup_id=backup_id,
                    valid=False,
                    warnings=warnings,
                    errors=errors,
                    counts=counts,
                    summary=verify_summary(has_manifest, has_project_data, counts),
                )

            manifest = json.loads(archive.read(MANIFEST_PATH).decode("utf-8"))
            project_data = json.loads(archive.read(PROJECT_DATA_PATH).decode("utf-8"))
            if not isinstance(project_data, dict) or not isinstance(manifest, dict):
                errors.append("BACKUP_PROJECT_DATA_INVALID: 备份数据文件格式不正确，无法恢复。")
                return BackupVerifyResult(
                    backup_id=backup_id,
                    valid=False,
                    warnings=warnings,
                    errors=errors,
                    counts=counts,
                    summary=verify_summary(has_manifest, has_project_data, counts),
                )

            counts.update(compare_manifest_counts(manifest, project_data, warnings))
            file_items = manifest.get("files", [])
            counts["manifest_files"] = len(file_items) if isinstance(file_items, list) else 0
            if not isinstance(file_items, list):
                errors.append("BACKUP_PROJECT_DATA_INVALID: manifest files 字段格式不正确。")
                file_items = []

            for item in file_items:
                if not isinstance(item, dict):
                    warnings.append("BACKUP_PROJECT_DATA_INVALID: manifest files 存在无效条目。")
                    continue
                relative_path = item.get("relative_path") or item.get("path")
                if not relative_path:
                    warnings.append("BACKUP_PROJECT_DATA_INVALID: manifest files 存在空路径。")
                    continue
                if relative_path not in names:
                    counts["missing_files"] += 1
                    warnings.append(f"BACKUP_FILE_MISSING_IN_ZIP: {relative_path}")
                    continue
                expected_size = item.get("size")
                if expected_size is not None and archive.getinfo(relative_path).file_size != int(expected_size):
                    warnings.append(f"BACKUP_FILE_MISSING_IN_ZIP: 文件大小不一致 {relative_path}")
                expected_sha = item.get("sha256")
                if expected_sha and zip_entry_sha256(archive, relative_path) != expected_sha:
                    counts["checksum_failed"] += 1
                    errors.append(f"BACKUP_CHECKSUM_FAILED: {relative_path}")
    except zipfile.BadZipFile:
        errors.append("BACKUP_VERIFY_FAILED: 备份包不是有效 zip 文件。")
    except (json.JSONDecodeError, UnicodeDecodeError):
        errors.append("BACKUP_PROJECT_DATA_INVALID: 备份 JSON 数据无法解析。")
    except OSError as exc:
        errors.append(f"BACKUP_VERIFY_FAILED: {exc}")

    return BackupVerifyResult(
        backup_id=backup_id,
        valid=not errors,
        warnings=warnings,
        errors=errors,
        counts=counts,
        summary=verify_summary(has_manifest, has_project_data, counts),
    )


def verify_summary(has_manifest: bool, has_project_data: bool, counts: dict[str, int]) -> dict[str, bool | int]:
    return {
        "has_manifest": has_manifest,
        "has_project_data": has_project_data,
        "file_count": counts.get("manifest_files", 0),
        "missing_file_count": counts.get("missing_files", 0),
        "checksum_failed_count": counts.get("checksum_failed", 0),
    }


def compare_project_restore_counts(
    db: Session,
    original_project_id: int,
    restored_project_id: int,
) -> dict[str, tuple[int, int]]:
    result: dict[str, tuple[int, int]] = {}
    for key, model in PROJECT_MODELS.items():
        result[key] = (
            count_project_rows(db, model, original_project_id),
            count_project_rows(db, model, restored_project_id),
        )
    result["field_evidence"] = (
        count_field_evidence(db, original_project_id),
        count_field_evidence(db, restored_project_id),
    )
    return result


def check_project_integrity(db: Session, project_id: int) -> ProjectIntegrityResult:
    project = db.get(Project, project_id)
    if project is None:
        raise integrity_http_error("PROJECT_INTEGRITY_CHECK_FAILED", "项目不存在，无法检查。", status.HTTP_404_NOT_FOUND)
    path_result = check_restored_project_paths(db, project_id)
    counts = {
        key: count_project_rows(db, model, project_id)
        for key, model in PROJECT_MODELS.items()
    }
    counts["field_evidence"] = count_field_evidence(db, project_id)
    errors = list(path_result["errors"])
    warnings = list(path_result["warnings"])
    return ProjectIntegrityResult(
        project_id=project_id,
        valid=not errors,
        warnings=warnings,
        errors=errors,
        path_check=ProjectPathCheck(
            invalid_paths=path_result["invalid_paths"],
            missing_files=path_result["missing_files"],
        ),
        counts=counts,
    )


def check_restored_project_paths(db: Session, project_id: int) -> dict[str, Any]:
    expected_marker = f"app_data/projects/project_{project_id}/"
    invalid_paths = 0
    missing_files = 0
    warnings: list[str] = []
    errors: list[str] = []
    for model, columns in PATH_COLUMNS.items():
        rows = db.scalars(select(model).where(model.project_id == project_id)).all()
        for row in rows:
            for column in columns:
                value = getattr(row, column, None)
                if not value:
                    continue
                normalized = str(value).replace("\\", "/")
                if normalized.startswith("app_data/projects/") and expected_marker not in normalized:
                    invalid_paths += 1
                    errors.append(f"RESTORE_PATH_CHECK_FAILED: {model.__tablename__}.{column} 指向其他项目：{value}")
                if normalized.startswith("app_data/projects/") and not (settings.root_dir / value).exists():
                    missing_files += 1
                    warnings.append(f"RESTORE_PATH_CHECK_FAILED: 文件不存在：{value}")
    return {
        "invalid_paths": invalid_paths,
        "missing_files": missing_files,
        "warnings": warnings,
        "errors": errors,
    }


def compare_manifest_counts(
    manifest: dict[str, Any],
    project_data: dict[str, Any],
    warnings: list[str],
) -> dict[str, int]:
    mismatches = 0
    manifest_counts = manifest.get("counts", {})
    if not isinstance(manifest_counts, dict):
        warnings.append("BACKUP_PROJECT_DATA_INVALID: manifest counts 字段格式不正确。")
        return {"manifest_count_mismatches": 1}
    for key in [
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
    ]:
        expected = manifest_counts.get(key)
        actual_data = project_data.get(key)
        actual = len(actual_data) if isinstance(actual_data, list) else 0
        if expected != actual:
            mismatches += 1
            warnings.append(f"RESTORE_COUNT_MISMATCH: {key} manifest={expected} project_data={actual}")
    return {"manifest_count_mismatches": mismatches}


def count_project_rows(db: Session, model: type[Any], project_id: int) -> int:
    return int(db.scalar(select(func.count()).select_from(model).where(model.project_id == project_id)) or 0)


def count_field_evidence(db: Session, project_id: int) -> int:
    statement = (
        select(func.count())
        .select_from(FieldEvidence)
        .join(FieldValue, FieldEvidence.field_value_id == FieldValue.id)
        .where(FieldValue.project_id == project_id)
    )
    return int(db.scalar(statement) or 0)


def zip_entry_sha256(archive: zipfile.ZipFile, name: str) -> str:
    digest = hashlib.sha256()
    with archive.open(name) as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def integrity_http_error(error_code: str, message: str, status_code: int) -> HTTPException:
    return HTTPException(status_code=status_code, detail={"error_code": error_code, "message": message})
