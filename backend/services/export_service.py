import json
import re
from datetime import datetime
from pathlib import Path
from uuid import uuid4

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.core.config import settings
from backend.models.export_record import ExportRecord
from backend.models.project import Project
from backend.schemas.export import ExportExcelRequest, ExportExcelResult, ExportRecordRead
from backend.services import excel_export_service, export_check_service

EXPORT_TYPE = "excel_ledger"


def export_project_excel(
    db: Session,
    project_id: int,
    payload: ExportExcelRequest,
) -> ExportExcelResult:
    project = db.get(Project, project_id)
    if project is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="项目不存在")
    check_result = export_check_service.check_project_export(db, project_id)
    if not check_result.can_export:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=check_result.model_dump(),
        )

    export_dir = settings.projects_dir / f"project_{project_id}" / "exports"
    export_dir.mkdir(parents=True, exist_ok=True)
    file_name = unique_export_name(export_dir, project.name)
    output_path = export_dir / file_name
    relative_path = output_path.relative_to(settings.root_dir).as_posix()

    try:
        sheet_count, issue_count = excel_export_service.build_excel(db, project, output_path, check_result)
        record = ExportRecord(
            project_id=project_id,
            export_type=EXPORT_TYPE,
            file_path=relative_path,
            file_name=file_name,
            sheet_count=sheet_count,
            issue_count=issue_count,
            include_unconfirmed=check_result.unconfirmed_count > 0,
            has_open_errors=check_result.open_error_count > 0,
            filter_json=json.dumps(payload.filter, ensure_ascii=False) if payload.filter else None,
            warning_summary=check_result.model_dump_json(),
        )
        db.add(record)
        db.commit()
        db.refresh(record)
    except Exception:
        if output_path.exists():
            output_path.unlink(missing_ok=True)
        raise

    return ExportExcelResult(
        export_id=record.id,
        project_id=project_id,
        file_name=file_name,
        file_path=relative_path,
        sheet_count=record.sheet_count,
        ledger_row_count=record.sheet_count,
        issue_row_count=record.issue_count,
        issue_count=record.issue_count,
        warning_count=check_result.warning_count,
        summary_sheet_count=2,
        precheck=precheck_payload(check_result),
        include_unconfirmed=record.include_unconfirmed,
        has_open_errors=record.has_open_errors,
        created_at=record.created_at,
        download_url=f"/api/exports/{record.id}/download",
        warning_summary=check_result,
    )


def list_exports(db: Session, project_id: int) -> list[ExportRecordRead]:
    rows = db.scalars(
        select(ExportRecord)
        .where(ExportRecord.project_id == project_id)
        .order_by(ExportRecord.created_at.desc(), ExportRecord.id.desc())
    ).all()
    return [
        ExportRecordRead(
            export_id=row.id,
            export_type=row.export_type,
            file_name=row.file_name,
            sheet_count=row.sheet_count,
            issue_count=row.issue_count,
            include_unconfirmed=row.include_unconfirmed,
            has_open_errors=row.has_open_errors,
            created_at=row.created_at,
            download_url=f"/api/exports/{row.id}/download",
        )
        for row in rows
    ]


def export_file_path(db: Session, export_id: int) -> tuple[Path, str]:
    record = db.get(ExportRecord, export_id)
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="导出记录不存在")
    path = settings.root_dir / record.file_path
    if not path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="导出文件不存在")
    return path, record.file_name


def unique_export_name(export_dir: Path, project_name: str) -> str:
    safe_name = safe_filename(project_name) or "project"
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    file_name = f"{safe_name}_图纸台账_{timestamp}.xlsx"
    if not (export_dir / file_name).exists():
        return file_name
    return f"{safe_name}_图纸台账_{timestamp}_{uuid4().hex[:8]}.xlsx"


def safe_filename(value: str) -> str:
    text = re.sub(r'[<>:"/\\|?*\s]+', "_", value.strip())
    return text.strip("._")[:80]


def precheck_payload(check_result) -> dict[str, int]:
    return {
        "total_sheets": check_result.sheet_count,
        "unreviewed_count": check_result.unconfirmed_count,
        "missing_drawing_no_count": check_result.empty_drawing_no_count,
        "missing_drawing_name_count": check_result.empty_drawing_name_count,
        "open_error_count": check_result.open_error_count,
        "open_warning_count": check_result.open_warning_count,
        "d_level_count": check_result.trust_level_d_count,
    }
