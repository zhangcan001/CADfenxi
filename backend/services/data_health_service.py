from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
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
from backend.models.field_value import FieldValue
from backend.models.project import Project
from backend.models.recognition_run import RecognitionRun
from backend.models.restore_record import RestoreRecord
from backend.schemas.data_health import (
    BackupRecordHealthResult,
    DataHealthItem,
    DataHealthSummary,
    DataSafetySummary,
    ExportRecordHealthResult,
    MaintenanceReportResult,
    OrphanFileItem,
    OrphanFileScanResult,
    ProjectHealthResult,
    SystemHealthResult,
)
from backend.services.project_service import project_dir
from recognizer.cad_engine.cad_json_writer import cad_parse_output_path

PROJECT_PATH_PREFIX = "app_data/projects/"
TEMP_CLEANUP_MAX_AGE_SECONDS = 0
LOW_CONFIDENCE_TRUST_LEVELS = {"C", "D"}
SYSTEM_GROUPS = ("storage", "project_files", "backup", "export", "restore", "temp")


@dataclass
class ReferencedPath:
    path: str
    record_type: str
    record_id: int
    project_id: int | None
    check_name: str
    missing_status: str
    missing_error_code: str
    missing_message: str
    suggestion: str


def run_system_health_check(db: Session) -> SystemHealthResult:
    generated_at = now()
    items: list[DataHealthItem] = []

    for name, directory, required in [
        ("app_data", settings.app_data_dir, True),
        ("database", settings.database_dir, True),
        ("projects", settings.projects_dir, True),
        ("backups", settings.backups_dir, True),
        ("logs", settings.logs_dir, True),
        ("temp", settings.temp_dir, True),
        ("exports", settings.app_data_dir / "exports", False),
    ]:
        items.append(check_directory(name, directory, required=required))
        if directory.exists():
            items.append(check_writable(name, directory))

    if settings.database_path.exists():
        items.append(ok_item("database", "database_file", f"数据库文件存在：{display_path(settings.database_path)}", path=relative_path(settings.database_path)))
    else:
        items.append(
            error_item(
                "database",
                "database_file",
                "数据库文件不存在。",
                "DATABASE_FILE_MISSING",
                path=relative_path(settings.database_path),
                suggestion="请先启动系统初始化数据库；如刚迁移数据，请确认 app_data/database/app.db 已复制。",
            )
        )

    backup_result = check_backup_records(db)
    export_result = check_export_records(db)
    items.extend(backup_result.items)
    items.extend(export_result.items)

    restore_items = check_restore_records(db)
    items.extend(restore_items)

    temp_count, temp_size = scan_temp_files()
    if temp_count > 0:
        items.append(
            info_item(
                "temp",
                "temp_cleanup_candidates",
                f"发现 {temp_count} 个临时文件，可使用安全清理释放 {format_bytes(temp_size)}。",
                "TEMP_CLEANUP_FILES_FOUND",
                suggestion="安全清理只会删除 app_data/temp 内的临时文件，不会删除项目文件或数据库记录。",
            )
        )
    else:
        items.append(ok_item("temp", "temp_cleanup_candidates", "未发现可清理的临时文件。"))

    project_count = count_rows(db, Project)
    backup_count = count_rows(db, BackupRecord)
    export_count = count_rows(db, ExportRecord)
    restore_count = count_rows(db, RestoreRecord)
    summary = build_summary(
        items,
        project_count=project_count,
        backup_count=backup_count,
        export_count=export_count,
        restore_count=restore_count,
        temp_file_count=temp_count,
        temp_size_bytes=temp_size,
    )
    return SystemHealthResult(
        status=overall_status(items),
        generated_at=generated_at,
        app_data_path=str(settings.app_data_dir),
        summary=summary,
        grouped_summary=build_grouped_summary(items),
        items=items,
    )


def run_project_integrity_check(db: Session, project_id: int) -> ProjectHealthResult:
    generated_at = now()
    project = db.get(Project, project_id)
    if project is None:
        raise data_health_http_error(
            status.HTTP_404_NOT_FOUND,
            "PROJECT_NOT_FOUND",
            "项目不存在，无法执行数据健康检查。",
        )

    items: list[DataHealthItem] = []
    path = project_dir(project_id)
    if path.exists() and path.is_dir():
        items.append(ok_item("project", "project_directory", "项目目录存在。", path=relative_path(path), project_id=project_id))
    else:
        items.append(
            error_item(
                "project",
                "project_directory",
                "项目目录不存在。",
                "PROJECT_DIR_MISSING",
                path=relative_path(path),
                project_id=project_id,
                suggestion="请确认 app_data/projects 是否完整；如刚迁移数据，请复制整个 app_data 目录。",
            )
        )

    referenced = collect_project_referenced_paths(db, project_id)
    for ref in referenced:
        items.append(check_referenced_file(ref))

    items.extend(check_cad_json_files(db, project_id))
    items.extend(check_project_status_counts(db, project_id))
    orphan_files = scan_orphan_project_files(db, project_id)
    if orphan_files:
        items.append(
            warning_item(
                "project",
                "orphan_files",
                f"发现 {len(orphan_files)} 个数据库未引用的项目文件。",
                "ORPHAN_FILE_FOUND",
                project_id=project_id,
                suggestion="请人工确认这些文件是否为历史残留或手动保存文件。本版本不会自动删除项目文件。",
            )
        )
    else:
        items.append(ok_item("project", "orphan_files", "未发现数据库未引用的项目文件。", project_id=project_id))

    summary = build_summary(
        items,
        project_count=1,
        export_count=count_rows(db, ExportRecord, project_id=project_id),
        orphan_files=orphan_files,
    )
    return ProjectHealthResult(
        project_id=project_id,
        project_name=project.name,
        status=overall_status(items),
        generated_at=generated_at,
        project_path=str(path),
        summary=summary,
        grouped_summary=build_grouped_summary(items),
        items=items,
        orphan_files=orphan_files,
    )


def scan_orphan_project_files(db: Session, project_id: int) -> list[OrphanFileItem]:
    project = db.get(Project, project_id)
    if project is None:
        raise data_health_http_error(
            status.HTTP_404_NOT_FOUND,
            "PROJECT_NOT_FOUND",
            "项目不存在，无法扫描孤儿文件。",
        )

    base = project_dir(project_id)
    if not base.exists():
        return []

    referenced = referenced_path_keys_for_project(db, project_id)
    orphan_files: list[OrphanFileItem] = []
    for file_path in sorted(item for item in base.rglob("*") if item.is_file()):
        if should_ignore_orphan_candidate(file_path):
            continue
        if path_key(file_path) not in referenced:
            orphan_files.append(
                OrphanFileItem(
                    project_id=project_id,
                    path=display_path(file_path),
                    size_bytes=file_path.stat().st_size,
                )
            )
    return orphan_files


def check_backup_records(db: Session) -> BackupRecordHealthResult:
    items: list[DataHealthItem] = []
    records = db.scalars(select(BackupRecord).order_by(BackupRecord.id.asc())).all()
    if not records:
        items.append(ok_item("backup", "backup_records", "暂无项目备份记录。"))
    for record in records:
        ref = ReferencedPath(
            path=record.file_path,
            record_type="backup_records",
            record_id=record.id,
            project_id=record.project_id,
            check_name="backup_zip",
            missing_status="warning",
            missing_error_code="BACKUP_FILE_MISSING",
            missing_message=f"备份记录 #{record.id} 对应 zip 文件不存在。",
            suggestion="请确认备份文件是否被手动移动或删除；删除备份记录前请先确认项目数据安全。",
        )
        items.append(check_referenced_file(ref))
    return BackupRecordHealthResult(
        status=overall_status(items),
        generated_at=now(),
        summary=build_summary(items, backup_count=len(records)),
        grouped_summary=build_grouped_summary(items),
        items=items,
    )


def check_export_records(db: Session) -> ExportRecordHealthResult:
    items: list[DataHealthItem] = []
    records = db.scalars(select(ExportRecord).order_by(ExportRecord.id.asc())).all()
    if not records:
        items.append(ok_item("export", "export_records", "暂无 Excel 导出记录。"))
    for record in records:
        ref = ReferencedPath(
            path=record.file_path,
            record_type="export_records",
            record_id=record.id,
            project_id=record.project_id,
            check_name="export_excel",
            missing_status="warning",
            missing_error_code="EXPORT_FILE_MISSING",
            missing_message=f"导出记录 #{record.id} 对应 Excel 文件不存在。",
            suggestion="可重新执行 Excel 导出；该问题不会影响项目识别数据。",
        )
        items.append(check_referenced_file(ref))
    return ExportRecordHealthResult(
        status=overall_status(items),
        generated_at=now(),
        summary=build_summary(items, export_count=len(records)),
        grouped_summary=build_grouped_summary(items),
        items=items,
    )


def data_safety_summary(db: Session) -> DataSafetySummary:
    return DataSafetySummary(
        app_data_path=str(settings.app_data_dir),
        database_exists=settings.database_path.exists(),
        projects_dir_exists=settings.projects_dir.exists(),
        backups_dir_exists=settings.backups_dir.exists(),
        logs_dir_exists=settings.logs_dir.exists(),
        temp_dir_exists=settings.temp_dir.exists(),
        project_count=count_rows(db, Project),
        backup_count=count_rows(db, BackupRecord),
        export_count=count_rows(db, ExportRecord),
        restore_count=count_rows(db, RestoreRecord),
        app_data_writable=is_writable(settings.app_data_dir),
    )


def build_maintenance_report(db: Session) -> MaintenanceReportResult:
    system = run_system_health_check(db)
    lines = [
        "# 数据健康检查报告",
        "",
        f"- 生成时间：{system.generated_at.isoformat()}",
        f"- 系统版本：{settings.version}",
        f"- 总体状态：{system.status}",
        f"- app_data：{system.app_data_path}",
        "",
        "## 汇总",
        "",
        f"- OK：{system.summary.ok_count}",
        f"- Info：{system.summary.info_count}",
        f"- Warning：{system.summary.warning_count}",
        f"- Error：{system.summary.error_count}",
        f"- 缺失文件：{system.summary.missing_file_count}",
        f"- 临时文件：{system.summary.temp_file_count}，{format_bytes(system.summary.temp_size_bytes)}",
        "",
        "## 分组摘要",
        "",
    ]
    for group, counts in system.grouped_summary.items():
        lines.append(f"- {group}：error {counts.error}，warning {counts.warning}，info {counts.info}")
    lines.extend(
        [
            "",
            "## 检查项",
            "",
        ]
    )
    for item in system.items:
        line = f"- [{item.status}] {item.scope}/{item.check_name}：{item.message}"
        if item.path:
            line += f"（{item.path}）"
        if item.suggestion:
            line += f" 建议：{item.suggestion}"
        lines.append(line)
    return MaintenanceReportResult(
        status=system.status,
        generated_at=system.generated_at,
        report_markdown="\n".join(lines) + "\n",
        system_health=system,
    )


def cleanup_temp_files() -> dict[str, Any]:
    temp_dir = settings.temp_dir.resolve()
    temp_dir.mkdir(parents=True, exist_ok=True)
    deleted_file_count = 0
    deleted_dir_count = 0
    freed_bytes = 0
    errors: list[str] = []

    for path in sorted(temp_dir.rglob("*"), key=lambda item: len(item.parts), reverse=True):
        try:
            resolved = path.resolve()
            if not resolved.is_relative_to(temp_dir):
                errors.append(f"跳过非法路径：{path}")
                continue
            if path.is_file():
                if path.name == ".gitkeep":
                    continue
                age_seconds = datetime.now().timestamp() - path.stat().st_mtime
                if age_seconds < TEMP_CLEANUP_MAX_AGE_SECONDS:
                    continue
                freed_bytes += path.stat().st_size
                path.unlink()
                deleted_file_count += 1
            elif path.is_dir() and not any(path.iterdir()):
                path.rmdir()
                deleted_dir_count += 1
        except OSError as exc:
            errors.append(f"{path}: {exc}")

    return {
        "status": "warning" if errors else "ok",
        "deleted_file_count": deleted_file_count,
        "deleted_dir_count": deleted_dir_count,
        "freed_bytes": freed_bytes,
        "errors": errors,
    }


def collect_project_referenced_paths(db: Session, project_id: int) -> list[ReferencedPath]:
    refs: list[ReferencedPath] = []
    for row in db.scalars(select(DrawingFile).where(DrawingFile.project_id == project_id).order_by(DrawingFile.id.asc())).all():
        refs.append(
            ReferencedPath(
                path=row.storage_path,
                record_type="drawing_files",
                record_id=row.id,
                project_id=project_id,
                check_name="drawing_file_storage",
                missing_status="error",
                missing_error_code="DRAWING_FILE_MISSING",
                missing_message=f"图纸文件 #{row.id} 原始文件不存在：{row.original_name}",
                suggestion="请确认 app_data/projects 是否完整；如只复制了数据库，需要补回 projects 目录。",
            )
        )
        if row.converted_file_path:
            converted_missing_status = "error" if row.convert_status == "success" else "warning"
            refs.append(
                ReferencedPath(
                    path=row.converted_file_path,
                    record_type="drawing_files",
                    record_id=row.id,
                    project_id=project_id,
                    check_name="dwg_converted_dxf",
                    missing_status=converted_missing_status,
                    missing_error_code="CONVERTED_DXF_MISSING",
                    missing_message=f"图纸文件 #{row.id} 的 DWG 转换后 DXF 文件不存在。",
                    suggestion="可重新执行 DWG 转 DXF；该问题不会删除原始 DWG。",
                )
            )

    for sheet in db.scalars(select(DrawingSheet).where(DrawingSheet.project_id == project_id).order_by(DrawingSheet.id.asc())).all():
        for attr, check_name, error_code, message in [
            ("preview_path", "sheet_preview", "SHEET_PREVIEW_MISSING", "图纸页预览图不存在。"),
            ("thumbnail_path", "sheet_thumbnail", "SHEET_THUMBNAIL_MISSING", "图纸页缩略图不存在。"),
            ("title_crop_path", "title_crop", "TITLE_CROP_MISSING", "标题栏裁剪图不存在。"),
            ("cad_preview_path", "cad_preview", "CAD_PREVIEW_MISSING", "CAD 预览图不存在。"),
        ]:
            value = getattr(sheet, attr)
            if not value:
                continue
            refs.append(
                ReferencedPath(
                    path=value,
                    record_type="drawing_sheets",
                    record_id=sheet.id,
                    project_id=project_id,
                    check_name=check_name,
                    missing_status="warning",
                    missing_error_code=error_code,
                    missing_message=f"图纸页 #{sheet.id} {message}",
                    suggestion="该文件可通过重新生成预览、标题栏裁剪或 CAD 预览补回，不影响数据库记录。",
                )
            )

    for run in db.scalars(select(RecognitionRun).where(RecognitionRun.project_id == project_id).order_by(RecognitionRun.id.asc())).all():
        if run.output_path:
            refs.append(
                ReferencedPath(
                    path=run.output_path,
                    record_type="recognition_runs",
                    record_id=run.id,
                    project_id=project_id,
                    check_name="recognition_output",
                    missing_status="warning",
                    missing_error_code="RECOGNITION_OUTPUT_MISSING",
                    missing_message=f"识别运行记录 #{run.id} 输出文件不存在。",
                    suggestion="可重新执行对应识别步骤；该问题不会影响已保存的台账字段。",
                )
            )

    for run in db.scalars(select(CadConversionRun).where(CadConversionRun.project_id == project_id).order_by(CadConversionRun.id.asc())).all():
        source_missing_status = "error" if run.status == "success" else "warning"
        refs.append(
            ReferencedPath(
                path=run.source_path,
                record_type="cad_conversion_runs",
                record_id=run.id,
                project_id=project_id,
                check_name="cad_conversion_source",
                missing_status=source_missing_status,
                missing_error_code="CONVERSION_SOURCE_MISSING",
                missing_message=f"CAD 转换记录 #{run.id} 源文件不存在。",
                suggestion="请确认原图纸文件是否仍在项目目录中。",
            )
        )
        if run.target_path:
            target_missing_status = "error" if run.status == "success" else "warning"
            refs.append(
                ReferencedPath(
                    path=run.target_path,
                    record_type="cad_conversion_runs",
                    record_id=run.id,
                    project_id=project_id,
                    check_name="cad_conversion_target",
                    missing_status=target_missing_status,
                    missing_error_code="CONVERTED_DXF_MISSING" if run.status == "success" else "CONVERSION_TARGET_MISSING",
                    missing_message=f"CAD 转换记录 #{run.id} 目标 DXF 不存在。",
                    suggestion="可重新执行 DWG 转 DXF。",
                )
            )

    for record in db.scalars(select(ExportRecord).where(ExportRecord.project_id == project_id).order_by(ExportRecord.id.asc())).all():
        refs.append(
            ReferencedPath(
                path=record.file_path,
                record_type="export_records",
                record_id=record.id,
                project_id=project_id,
                check_name="export_excel",
                missing_status="warning",
                missing_error_code="EXPORT_FILE_MISSING",
                missing_message=f"导出记录 #{record.id} 对应 Excel 文件不存在。",
                suggestion="可重新导出 Excel。",
            )
        )
    return refs


def check_cad_json_files(db: Session, project_id: int) -> list[DataHealthItem]:
    items: list[DataHealthItem] = []
    sheets = db.scalars(select(DrawingSheet).where(DrawingSheet.project_id == project_id).order_by(DrawingSheet.id.asc())).all()
    for sheet in sheets:
        if sheet.file is not None:
            source_format = sheet.file.source_format
        else:
            drawing_file = db.get(DrawingFile, sheet.file_id)
            source_format = drawing_file.source_format if drawing_file else ""
        if source_format not in {"dxf", "dwg"} and not sheet.status.startswith("cad"):
            continue
        if sheet.status not in {"cad_parsed", "recognized", "need_review", "confirmed"}:
            continue
        path = cad_parse_output_path(settings.root_dir, sheet.project_id, sheet.id)
        ref = ReferencedPath(
            path=relative_path(path),
            record_type="drawing_sheets",
            record_id=sheet.id,
            project_id=project_id,
            check_name="cad_json",
            missing_status="warning",
            missing_error_code="CAD_JSON_MISSING",
            missing_message=f"图纸页 #{sheet.id} CAD JSON 解析结果不存在。",
            suggestion="可重新执行 DXF 解析；该问题不会删除已有候选值或推荐字段。",
        )
        items.append(check_referenced_file(ref))
    return items


def check_project_status_counts(db: Session, project_id: int) -> list[DataHealthItem]:
    items: list[DataHealthItem] = []
    open_error_count = int(
        db.scalar(
            select(func.count())
            .select_from(DrawingIssue)
            .where(
                DrawingIssue.project_id == project_id,
                DrawingIssue.status == "open",
                DrawingIssue.severity == "error",
            )
        )
        or 0
    )
    open_warning_count = int(
        db.scalar(
            select(func.count())
            .select_from(DrawingIssue)
            .where(
                DrawingIssue.project_id == project_id,
                DrawingIssue.status == "open",
                DrawingIssue.severity == "warning",
            )
        )
        or 0
    )
    failed_sheet_count = int(
        db.scalar(
            select(func.count())
            .select_from(DrawingSheet)
            .where(DrawingSheet.project_id == project_id, DrawingSheet.status == "failed")
        )
        or 0
    )
    low_confidence_count = int(
        db.scalar(
            select(func.count())
            .select_from(DrawingSheet)
            .where(
                DrawingSheet.project_id == project_id,
                DrawingSheet.trust_level.in_(LOW_CONFIDENCE_TRUST_LEVELS),
            )
        )
        or 0
    )
    unreviewed_sheet_count = int(
        db.scalar(
            select(func.count())
            .select_from(DrawingSheet)
            .where(
                DrawingSheet.project_id == project_id,
                DrawingSheet.review_status != "confirmed",
            )
        )
        or 0
    )
    unreviewed_field_count = int(
        db.scalar(
            select(func.count())
            .select_from(FieldValue)
            .where(FieldValue.project_id == project_id, FieldValue.is_reviewed.is_(False))
        )
        or 0
    )
    if open_error_count:
        items.append(
            warning_item(
                "project",
                "open_errors",
                f"当前项目存在 {open_error_count} 个未关闭 error 问题。",
                "OPEN_ERROR_EXISTS",
                project_id=project_id,
                suggestion="建议在校核工作台处理后再交付或归档。",
            )
        )
    else:
        items.append(ok_item("project", "open_errors", "当前项目没有未关闭 error 问题。", project_id=project_id))
    if open_warning_count:
        items.append(
            info_item(
                "project",
                "open_warnings",
                f"当前项目存在 {open_warning_count} 个未关闭 warning 问题。",
                "OPEN_WARNING_EXISTS",
                project_id=project_id,
                suggestion="建议交付前复核 warning；该项通常不表示文件缺失。",
            )
        )
    else:
        items.append(ok_item("project", "open_warnings", "当前项目没有未关闭 warning 问题。", project_id=project_id))
    if failed_sheet_count:
        items.append(
            warning_item(
                "project",
                "failed_sheets",
                f"当前项目存在 {failed_sheet_count} 张失败状态图纸。",
                "FAILED_SHEET_EXISTS",
                project_id=project_id,
                suggestion="建议查看失败图纸的 error_code 和 message 后重试对应步骤。",
            )
        )
    else:
        items.append(ok_item("project", "failed_sheets", "当前项目没有失败状态图纸。", project_id=project_id))
    if low_confidence_count:
        items.append(
            info_item(
                "project",
                "low_confidence",
                f"当前项目存在 {low_confidence_count} 张低可信图纸。",
                "LOW_CONFIDENCE_EXISTS",
                project_id=project_id,
                suggestion="建议在校核工作台抽查 C/D 级图纸。",
            )
        )
    else:
        items.append(ok_item("project", "low_confidence", "当前项目没有 C/D 级低可信图纸。", project_id=project_id))
    if unreviewed_sheet_count or unreviewed_field_count:
        items.append(
            info_item(
                "project",
                "unreviewed_sheets",
                f"当前项目存在 {unreviewed_sheet_count} 张未确认图纸、{unreviewed_field_count} 个未人工确认字段。",
                "UNREVIEWED_SHEETS_EXISTS",
                project_id=project_id,
                suggestion="这是校核进度提示，不表示文件损坏；交付前建议完成确认。",
            )
        )
    else:
        items.append(ok_item("project", "unreviewed_sheets", "当前项目图纸和字段均已确认。", project_id=project_id))
    return items


def check_restore_records(db: Session) -> list[DataHealthItem]:
    items: list[DataHealthItem] = []
    records = db.scalars(select(RestoreRecord).order_by(RestoreRecord.id.asc())).all()
    if not records:
        return [ok_item("restore", "restore_records", "暂无恢复记录。")]
    for record in records:
        if record.status == "success" and record.new_project_id is not None and db.get(Project, record.new_project_id) is None:
            items.append(
                warning_item(
                    "restore",
                    "restore_target_project",
                    f"恢复记录 #{record.id} 指向的新项目不存在。",
                    "RESTORE_TARGET_MISSING",
                    record_type="restore_records",
                    record_id=record.id,
                    suggestion="如果该项目已被删除，请保留记录用于追溯；如为异常，请查看恢复日志。",
                )
            )
        elif record.status == "failed":
            items.append(
                warning_item(
                    "restore",
                    "restore_failed_record",
                    f"恢复记录 #{record.id} 为失败状态：{record.error_code or 'RESTORE_FAILED'}。",
                    "RESTORE_FAILED_RECORD",
                    record_type="restore_records",
                    record_id=record.id,
                    suggestion="失败记录不会影响已有项目，可根据错误码重新执行恢复。",
                )
            )
        else:
            items.append(
                ok_item(
                    "restore",
                    "restore_record",
                    f"恢复记录 #{record.id} 状态正常。",
                    record_type="restore_records",
                    record_id=record.id,
                )
            )
    return items


def check_referenced_file(ref: ReferencedPath) -> DataHealthItem:
    path = absolute_path(ref.path)
    if path.exists() and path.is_file():
        return ok_item(
            ref.record_type,
            ref.check_name,
            "文件存在。",
            path=normalize_relative_path(ref.path),
            record_type=ref.record_type,
            record_id=ref.record_id,
            project_id=ref.project_id,
            checked_file=True,
        )
    factory = item_factory_for_status(ref.missing_status)
    return factory(
        ref.record_type,
        ref.check_name,
        ref.missing_message,
        ref.missing_error_code,
        path=normalize_relative_path(ref.path),
        record_type=ref.record_type,
        record_id=ref.record_id,
        project_id=ref.project_id,
        suggestion=ref.suggestion,
        missing_file=True,
        checked_file=True,
    )


def check_directory(name: str, directory: Path, *, required: bool) -> DataHealthItem:
    if directory.exists() and directory.is_dir():
        return ok_item("app_data", f"{name}_directory", f"{name} 目录存在。", path=relative_path(directory))
    if not required:
        return ok_item(
            "app_data",
            f"{name}_directory",
            f"{name} 目录未创建；当前导出文件默认保存在项目目录中。",
            path=relative_path(directory),
        )
    if required:
        return error_item(
            "app_data",
            f"{name}_directory",
            f"{name} 目录不存在。",
            "APP_DATA_DIRECTORY_MISSING",
            path=relative_path(directory),
            suggestion="请确认 portable 包根目录下 app_data 结构完整，或重新运行 start.bat 初始化目录。",
        )
    raise AssertionError("unreachable")


def check_writable(name: str, directory: Path) -> DataHealthItem:
    if is_writable(directory):
        return ok_item("app_data", f"{name}_writable", f"{name} 目录可写。", path=relative_path(directory))
    return error_item(
        "app_data",
        f"{name}_writable",
        f"{name} 目录不可写。",
        "APP_DATA_NOT_WRITABLE",
        path=relative_path(directory),
        suggestion="请检查当前用户权限、杀毒软件拦截或目录是否位于只读位置。",
    )


def is_writable(directory: Path) -> bool:
    try:
        directory.mkdir(parents=True, exist_ok=True)
        test_file = directory / ".data_health_write_check"
        test_file.write_text("ok", encoding="utf-8")
        test_file.unlink(missing_ok=True)
        return True
    except OSError:
        return False


def scan_temp_files() -> tuple[int, int]:
    if not settings.temp_dir.exists():
        return 0, 0
    count = 0
    size = 0
    for path in settings.temp_dir.rglob("*"):
        if path.name == ".gitkeep":
            continue
        if path.is_file():
            count += 1
            try:
                size += path.stat().st_size
            except OSError:
                pass
    return count, size


def build_summary(
    items: list[DataHealthItem],
    *,
    project_count: int = 0,
    backup_count: int = 0,
    export_count: int = 0,
    restore_count: int = 0,
    temp_file_count: int = 0,
    temp_size_bytes: int = 0,
    orphan_files: list[OrphanFileItem] | None = None,
) -> DataHealthSummary:
    checked_file_count = sum(1 for item in items if item.is_checked_file)
    missing_file_count = sum(1 for item in items if item.is_missing_file)
    orphan_files = orphan_files or []
    return DataHealthSummary(
        ok_count=sum(1 for item in items if item.status == "ok"),
        info_count=sum(1 for item in items if item.status == "info"),
        warning_count=sum(1 for item in items if item.status == "warning"),
        error_count=sum(1 for item in items if item.status == "error"),
        checked_file_count=checked_file_count,
        missing_file_count=missing_file_count,
        orphan_file_count=len(orphan_files),
        orphan_file_size_bytes=sum(item.size_bytes for item in orphan_files),
        temp_file_count=temp_file_count,
        temp_size_bytes=temp_size_bytes,
        project_count=project_count,
        backup_count=backup_count,
        export_count=export_count,
        restore_count=restore_count,
    )


def build_grouped_summary(items: list[DataHealthItem]) -> dict[str, dict[str, int]]:
    groups: dict[str, dict[str, int]] = {
        group: {"error": 0, "warning": 0, "info": 0}
        for group in SYSTEM_GROUPS
    }
    for item in items:
        if item.status not in {"error", "warning", "info"}:
            continue
        group = group_for_item(item)
        groups.setdefault(group, {"error": 0, "warning": 0, "info": 0})
        groups[group][item.status] += 1
    return groups


def group_for_item(item: DataHealthItem) -> str:
    if item.scope in {"backup", "backup_records"} or item.record_type == "backup_records":
        return "backup"
    if item.scope in {"export", "export_records"} or item.record_type == "export_records":
        return "export"
    if item.scope == "restore" or item.record_type == "restore_records":
        return "restore"
    if item.scope == "temp":
        return "temp"
    if item.scope in {"app_data", "database"}:
        return "storage"
    if item.scope in {"project", "drawing_files", "drawing_sheets", "recognition_runs", "cad_conversion_runs"}:
        return "project_files"
    return item.scope or "storage"


def overall_status(items: list[DataHealthItem]) -> str:
    if any(item.status == "error" for item in items):
        return "error"
    if any(item.status == "warning" for item in items):
        return "warning"
    if any(item.status == "info" for item in items):
        return "info"
    return "ok"


def ok_item(
    scope: str,
    check_name: str,
    message: str,
    *,
    path: str | None = None,
    record_type: str | None = None,
    record_id: int | None = None,
    project_id: int | None = None,
    checked_file: bool = False,
) -> DataHealthItem:
    item = DataHealthItem(
        scope=scope,
        check_name=check_name,
        status="ok",
        message=message,
        path=path,
        record_type=record_type,
        record_id=record_id,
        project_id=project_id,
        is_checked_file=checked_file,
    )
    return item


def warning_item(
    scope: str,
    check_name: str,
    message: str,
    error_code: str,
    *,
    path: str | None = None,
    record_type: str | None = None,
    record_id: int | None = None,
    project_id: int | None = None,
    suggestion: str | None = None,
    missing_file: bool = False,
    checked_file: bool = False,
) -> DataHealthItem:
    item = DataHealthItem(
        scope=scope,
        check_name=check_name,
        status="warning",
        error_code=error_code,
        message=message,
        path=path,
        record_type=record_type,
        record_id=record_id,
        project_id=project_id,
        suggestion=suggestion,
        is_checked_file=checked_file,
        is_missing_file=missing_file,
    )
    return item


def info_item(
    scope: str,
    check_name: str,
    message: str,
    error_code: str,
    *,
    path: str | None = None,
    record_type: str | None = None,
    record_id: int | None = None,
    project_id: int | None = None,
    suggestion: str | None = None,
    missing_file: bool = False,
    checked_file: bool = False,
) -> DataHealthItem:
    item = DataHealthItem(
        scope=scope,
        check_name=check_name,
        status="info",
        error_code=error_code,
        message=message,
        path=path,
        record_type=record_type,
        record_id=record_id,
        project_id=project_id,
        suggestion=suggestion,
        is_checked_file=checked_file,
        is_missing_file=missing_file,
    )
    return item


def error_item(
    scope: str,
    check_name: str,
    message: str,
    error_code: str,
    *,
    path: str | None = None,
    record_type: str | None = None,
    record_id: int | None = None,
    project_id: int | None = None,
    suggestion: str | None = None,
    missing_file: bool = False,
    checked_file: bool = False,
) -> DataHealthItem:
    item = DataHealthItem(
        scope=scope,
        check_name=check_name,
        status="error",
        error_code=error_code,
        message=message,
        path=path,
        record_type=record_type,
        record_id=record_id,
        project_id=project_id,
        suggestion=suggestion,
        is_checked_file=checked_file,
        is_missing_file=missing_file,
    )
    return item


def item_factory_for_status(status_value: str):
    if status_value == "error":
        return error_item
    if status_value == "info":
        return info_item
    return warning_item


def absolute_path(value: str) -> Path:
    normalized = normalize_relative_path(value)
    path = Path(normalized)
    if path.is_absolute():
        return path
    return settings.root_dir / normalized


def relative_path(path: Path) -> str:
    try:
        return path.resolve().relative_to(settings.root_dir.resolve()).as_posix()
    except ValueError:
        return path.as_posix()
    except OSError:
        pass
    try:
        return path.relative_to(settings.root_dir).as_posix()
    except ValueError:
        return path.as_posix()


def normalize_relative_path(value: str) -> str:
    return str(value).replace("\\", "/")


def display_path(path: Path) -> str:
    return normalize_relative_path(relative_path(path))


def path_key(value: str | Path) -> str:
    path = absolute_path(str(value)) if not isinstance(value, Path) else value
    try:
        normalized = path.resolve(strict=False)
    except OSError:
        normalized = path.absolute()
    text = normalized.as_posix()
    if is_windows_like_path(text):
        return text.casefold()
    return text


def is_windows_like_path(value: str) -> bool:
    return value[:2].endswith(":") or "\\" in value or settings.root_dir.drive != ""


def referenced_path_keys_for_project(db: Session, project_id: int) -> set[str]:
    keys = {
        path_key(ref.path)
        for ref in collect_project_referenced_paths(db, project_id)
        if ref.path
    }
    keys.update(
        path_key(cad_parse_output_path(settings.root_dir, sheet.project_id, sheet.id))
        for sheet in db.scalars(select(DrawingSheet).where(DrawingSheet.project_id == project_id)).all()
    )
    return keys


def should_ignore_orphan_candidate(path: Path) -> bool:
    if path.name in {".gitkeep", "README.md"}:
        return True
    if path.suffix.lower() in {".lock", ".lck"}:
        return True
    try:
        resolved = path.resolve(strict=False)
        logs_dir = settings.logs_dir.resolve(strict=False)
        temp_dir = settings.temp_dir.resolve(strict=False)
        backups_dir = settings.backups_dir.resolve(strict=False)
    except OSError:
        return False
    return any(
        safe_is_relative_to(resolved, directory)
        for directory in (logs_dir, temp_dir, backups_dir)
    )


def safe_is_relative_to(path: Path, parent: Path) -> bool:
    try:
        return path.is_relative_to(parent)
    except ValueError:
        return False


def count_rows(db: Session, model: type[Any], *, project_id: int | None = None) -> int:
    statement = select(func.count()).select_from(model)
    if project_id is not None and hasattr(model, "project_id"):
        statement = statement.where(model.project_id == project_id)
    return int(db.scalar(statement) or 0)


def format_bytes(value: int) -> str:
    if value < 1024:
        return f"{value} B"
    if value < 1024 * 1024:
        return f"{value / 1024:.1f} KB"
    return f"{value / 1024 / 1024:.1f} MB"


def now() -> datetime:
    return datetime.now(UTC)


def data_health_http_error(status_code: int, error_code: str, message: str) -> HTTPException:
    return HTTPException(status_code=status_code, detail={"error_code": error_code, "message": message})
