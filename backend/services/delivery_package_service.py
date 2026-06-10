from __future__ import annotations

import json
import shutil
import zipfile
from collections import Counter
from datetime import datetime
from pathlib import Path

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.core.config import settings
from backend.models.drawing_file import DrawingFile
from backend.models.drawing_issue import DrawingIssue
from backend.models.drawing_sheet import DrawingSheet
from backend.models.export_record import ExportRecord
from backend.models.project import Project
from backend.schemas.delivery_package import DeliveryPackageRequest, DeliveryPackageResult
from backend.services import export_service
from backend.services import excel_export_service, export_check_service

DELIVERY_PACKAGE_PREFIX = "delivery"
DELIVERY_PACKAGE_MAX_ORIGINAL_BYTES = 500 * 1024 * 1024


def create_project_delivery_package(
    db: Session,
    project_id: int,
    payload: DeliveryPackageRequest,
) -> DeliveryPackageResult:
    project = db.get(Project, project_id)
    if project is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error_code": "PROJECT_NOT_FOUND", "message": "项目不存在。"},
        )
    sheet_count = db.scalar(
        select(func.count()).select_from(DrawingSheet).where(DrawingSheet.project_id == project_id)
    ) or 0
    if sheet_count == 0:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "error_code": "DELIVERY_PACKAGE_EMPTY_PROJECT",
                "message": "当前项目还没有图纸，无法生成项目交付包。请先导入图纸并生成台账。",
            },
        )

    package_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    package_id = f"{DELIVERY_PACKAGE_PREFIX}_{package_timestamp}"
    package_dir = settings.projects_dir / f"project_{project_id}" / "delivery_packages"
    package_dir.mkdir(parents=True, exist_ok=True)
    file_name = unique_delivery_name(package_dir, project_id, project.name, package_timestamp)
    zip_path = package_dir / file_name
    work_dir = package_dir / f".{package_id}"
    if work_dir.exists():
        shutil.rmtree(work_dir)
    work_dir.mkdir(parents=True, exist_ok=True)

    try:
        latest_excel, excel_included, excel_generated_for_package = ensure_latest_excel(
            db, project, project_id, payload.include_latest_excel, work_dir / "图纸台账.xlsx"
        )
        sheets = list_project_sheets(db, project_id)
        files = list_project_files(db, project_id)
        issues = list_project_issues(db, project_id)
        source_assets = collect_asset_sources(sheets, files, payload, excel_included)
        included = source_assets.included
        warnings = build_delivery_warnings(payload, files, included, excel_generated_for_package)

        write_delivery_readme(work_dir / "交付说明.txt", project, included, warnings)
        write_json(
            work_dir / "project_summary.json",
            project_summary(project, sheets, files, issues, included, warnings),
        )
        write_json(work_dir / "issue_summary.json", issue_summary(issues))

        copy_named_sources(source_assets.cad_previews, work_dir / "cad_previews")
        copy_named_sources(source_assets.pdf_previews, work_dir / "pdf_previews")
        copy_named_sources(source_assets.original_files, work_dir / "original_files")

        write_zip(work_dir, zip_path)
    finally:
        shutil.rmtree(work_dir, ignore_errors=True)

    return DeliveryPackageResult(
        package_id=package_id,
        file_name=file_name,
        file_size=zip_path.stat().st_size,
        download_url=f"/api/projects/{project_id}/delivery-package/download?package_id={package_id}",
        included=included,
        warnings=warnings,
    )


def delivery_package_file_path(db: Session, project_id: int, package_id: str) -> tuple[Path, str]:
    if db.get(Project, project_id) is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error_code": "PROJECT_NOT_FOUND", "message": "项目不存在，无法下载交付包。"},
        )
    if not package_id.startswith(f"{DELIVERY_PACKAGE_PREFIX}_"):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error_code": "DELIVERY_PACKAGE_NOT_FOUND", "message": "交付包不存在。"},
        )
    package_dir = settings.projects_dir / f"project_{project_id}" / "delivery_packages"
    matches = sorted(
        (path for path in package_dir.glob(f"*{package_id}*.zip") if path.is_file()),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    if not matches:
        timestamp = package_id.removeprefix(f"{DELIVERY_PACKAGE_PREFIX}_")
        matches = sorted(
            (path for path in package_dir.glob(f"project_delivery_{project_id}_*_{timestamp}*.zip") if path.is_file()),
            key=lambda path: path.stat().st_mtime,
            reverse=True,
        )
    if not matches:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error_code": "DELIVERY_PACKAGE_NOT_FOUND", "message": "交付包不存在。"},
        )
    path = matches[0]
    return path, path.name


def ensure_latest_excel(
    db: Session,
    project: Project,
    project_id: int,
    include_latest_excel: bool,
    delivery_excel_path: Path,
) -> tuple[ExportRecord | None, bool, bool]:
    if not include_latest_excel:
        return None, False, False
    record = latest_existing_excel(db, project_id)
    if record is not None:
        copy_if_exists(settings.root_dir / record.file_path, delivery_excel_path)
        return record, delivery_excel_path.is_file(), False

    check_result = export_check_service.check_project_export(db, project_id)
    if not check_result.can_export:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "error_code": "DELIVERY_PACKAGE_EXCEL_NOT_READY",
                "message": "当前项目暂不能生成 Excel 台账，请先导出 Excel 后再生成交付包。",
                "precheck": check_result.model_dump(),
            },
        )

    try:
        delivery_excel_path.parent.mkdir(parents=True, exist_ok=True)
        excel_export_service.build_excel(db, project, delivery_excel_path, check_result)
    except Exception as exc:
        delivery_excel_path.unlink(missing_ok=True)
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "error_code": "DELIVERY_PACKAGE_EXCEL_GENERATE_FAILED",
                "message": f"交付包需要 Excel 台账，但自动生成失败：{exc}",
            },
        ) from exc

    return None, delivery_excel_path.is_file(), True


def latest_existing_excel(db: Session, project_id: int) -> ExportRecord | None:
    records = db.scalars(
        select(ExportRecord)
        .where(ExportRecord.project_id == project_id, ExportRecord.export_type == export_service.EXPORT_TYPE)
        .order_by(ExportRecord.created_at.desc(), ExportRecord.id.desc())
    ).all()
    for record in records:
        if (settings.root_dir / record.file_path).is_file():
            return record
    return None


def list_project_sheets(db: Session, project_id: int) -> list[DrawingSheet]:
    return db.scalars(
        select(DrawingSheet).where(DrawingSheet.project_id == project_id).order_by(DrawingSheet.id.asc())
    ).all()


def list_project_files(db: Session, project_id: int) -> list[DrawingFile]:
    return db.scalars(
        select(DrawingFile).where(DrawingFile.project_id == project_id).order_by(DrawingFile.id.asc())
    ).all()


def list_project_issues(db: Session, project_id: int) -> list[DrawingIssue]:
    return db.scalars(
        select(DrawingIssue).where(DrawingIssue.project_id == project_id).order_by(DrawingIssue.id.asc())
    ).all()


def issue_summary(issues: list[DrawingIssue]) -> dict:
    by_status = Counter(issue.status for issue in issues)
    by_severity = Counter(issue.severity for issue in issues)
    by_code = Counter(issue.issue_code for issue in issues)
    return {
        "total": len(issues),
        "by_status": dict(by_status),
        "by_severity": dict(by_severity),
        "by_code": dict(by_code),
        "items": [
            {
                "id": issue.id,
                "sheet_id": issue.sheet_id,
                "issue_code": issue.issue_code,
                "severity": issue.severity,
                "status": issue.status,
                "message": issue.message,
                "suggestion": issue.suggestion,
                "created_at": issue.created_at.isoformat() if issue.created_at else None,
            }
            for issue in issues
        ],
    }


class DeliveryPackageAssetSources:
    def __init__(
        self,
        excel: bool,
        cad_previews: list[tuple[Path, str]],
        pdf_previews: list[tuple[Path, str]],
        original_files: list[tuple[Path, str]],
    ) -> None:
        self.excel = excel
        self.cad_previews = cad_previews
        self.pdf_previews = pdf_previews
        self.original_files = original_files

    @property
    def included(self) -> dict[str, bool]:
        return {
            "excel": self.excel,
            "cad_previews": bool(self.cad_previews),
            "pdf_previews": bool(self.pdf_previews),
            "original_files": bool(self.original_files),
        }


def collect_asset_sources(
    sheets: list[DrawingSheet],
    files: list[DrawingFile],
    payload: DeliveryPackageRequest,
    excel_included: bool,
) -> DeliveryPackageAssetSources:
    return DeliveryPackageAssetSources(
        excel=excel_included,
        cad_previews=sheet_asset_sources(sheets, "cad_preview_path") if payload.include_cad_previews else [],
        pdf_previews=(
            sheet_asset_sources(sheets, "thumbnail_path") + sheet_asset_sources(sheets, "preview_path")
            if payload.include_pdf_previews
            else []
        ),
        original_files=original_file_sources(files) if payload.include_original_files else [],
    )


def build_delivery_warnings(
    payload: DeliveryPackageRequest,
    files: list[DrawingFile],
    included: dict[str, bool],
    excel_generated_for_package: bool,
) -> list[str]:
    warnings = []
    if payload.include_latest_excel and excel_generated_for_package:
        warnings.append("未找到可用 Excel 台账，已为本次交付包自动生成临时台账文件，未写入导出历史。")
    if payload.include_cad_previews and not included["cad_previews"]:
        warnings.append("未找到可用 CAD 预览图，交付包未包含 cad_previews 目录。")
    if payload.include_pdf_previews and not included["pdf_previews"]:
        warnings.append("未找到可用 PDF 预览图，交付包未包含 pdf_previews 目录。")
    if payload.include_original_files:
        total_size = sum(file.file_size or 0 for file in files)
        warnings.append(f"已选择包含原始图纸文件，交付包可能较大；当前原始文件合计约 {total_size} 字节。")
        if total_size > DELIVERY_PACKAGE_MAX_ORIGINAL_BYTES:
            warnings.append("原始图纸合计超过 500MB，建议仅在确需移交源文件时包含。")
    else:
        warnings.append("默认未包含原始图纸文件，可避免交付包过大。")
    warnings.append("交付包用于成果查看和归档，不用于恢复系统数据；系统恢复请使用项目备份包。")
    return warnings


def project_summary(
    project: Project,
    sheets: list[DrawingSheet],
    files: list[DrawingFile],
    issues: list[DrawingIssue],
    included: dict[str, bool],
    warnings: list[str],
) -> dict:
    formats = Counter(file.source_format for file in files)
    review_statuses = Counter(sheet.review_status for sheet in sheets)
    return {
        "project_id": project.id,
        "project_name": project.name,
        "exported_at": datetime.now().isoformat(timespec="seconds"),
        "drawing_file_count": len(files),
        "drawing_sheet_count": len(sheets),
        "file_type_counts": dict(formats),
        "confirmed_sheet_count": review_statuses.get("confirmed", 0),
        "unreviewed_sheet_count": len(sheets) - review_statuses.get("confirmed", 0),
        "open_issue_count": sum(1 for issue in issues if issue.status == "open"),
        "open_error_count": sum(1 for issue in issues if issue.status == "open" and issue.severity == "error"),
        "open_warning_count": sum(1 for issue in issues if issue.status == "open" and issue.severity == "warning"),
        "included": included,
        "warnings": warnings,
        "note": "交付包用于成果查看和归档，不用于系统恢复。",
    }


def write_delivery_readme(path: Path, project: Project, included: dict[str, bool], warnings: list[str]) -> None:
    lines = [
        "工程图纸智能台账识别系统 项目交付包",
        "",
        f"项目名称：{project.name}",
        f"导出时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "包含内容：",
        "- 图纸台账 Excel" if included["excel"] else "- 图纸台账 Excel：未包含",
        "- 项目摘要",
        "- 问题清单摘要",
    ]
    if included["cad_previews"]:
        lines.append("- CAD 预览图")
    if included["pdf_previews"]:
        lines.append("- PDF 预览图")
    if included["original_files"]:
        lines.append("- 原始图纸文件")
    lines.extend(
        [
            "",
            "说明：",
            "1. 本交付包用于成果查看和归档。",
            "2. 如需恢复系统数据，请使用项目备份包。",
            "3. CAD 预览仅用于辅助查看。",
            "4. 最终成果应以人工复核后的图纸台账为准。",
            "5. 原始图纸默认不包含；包含原始图纸时交付包可能明显变大。",
            "6. 本交付包不包含完整数据库恢复信息，不可替代项目备份包。",
            "",
            "提示：",
            *[f"- {warning}" for warning in warnings],
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def sheet_asset_sources(sheets: list[DrawingSheet], attr_name: str) -> list[tuple[Path, str]]:
    sources: list[tuple[Path, str]] = []
    for sheet in sheets:
        relative = getattr(sheet, attr_name, None)
        if not relative:
            continue
        source = settings.root_dir / relative
        if not source.is_file():
            continue
        sources.append((source, f"sheet_{sheet.id}_{source.name}"))
    return sources


def original_file_sources(files: list[DrawingFile]) -> list[tuple[Path, str]]:
    sources: list[tuple[Path, str]] = []
    for drawing_file in files:
        source = settings.root_dir / drawing_file.storage_path
        if not source.is_file():
            continue
        original_path = Path(drawing_file.original_name)
        safe_stem = export_service.safe_filename(original_path.stem) or f"file_{drawing_file.id}"
        sources.append((source, f"file_{drawing_file.id}_{safe_stem}{original_path.suffix}"))
    return sources


def copy_named_sources(sources: list[tuple[Path, str]], target_dir: Path) -> int:
    copied = 0
    for source, file_name in sources:
        copy_if_exists(source, target_dir / file_name)
        copied += 1
    return copied


def copy_if_exists(source: Path, target: Path) -> None:
    if not source.is_file():
        return
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)


def write_zip(source_dir: Path, zip_path: Path) -> None:
    if zip_path.exists():
        zip_path.unlink()
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(source_dir.rglob("*")):
            if path.is_file():
                archive.write(path, path.relative_to(source_dir).as_posix())


def unique_delivery_name(package_dir: Path, project_id: int, project_name: str, timestamp: str) -> str:
    safe_name = export_service.safe_filename(project_name) or "project"
    base = f"project_delivery_{project_id}_{safe_name}_{timestamp}"
    file_name = f"{base}.zip"
    if not (package_dir / file_name).exists():
        return file_name
    return f"{base}_{datetime.now().microsecond}.zip"
