from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from backend.models.backup_record import BackupRecord
from backend.models.drawing_file import DrawingFile
from backend.models.drawing_issue import DrawingIssue
from backend.models.drawing_sheet import DrawingSheet
from backend.models.export_record import ExportRecord
from backend.schemas.project import ProjectWorkbenchSummary
from backend.services.project_service import get_project_or_404


def get_workbench_summary(db: Session, project_id: int) -> ProjectWorkbenchSummary:
    get_project_or_404(db, project_id)
    return ProjectWorkbenchSummary(
        project_id=project_id,
        drawing_file_count=count_files(db, project_id),
        drawing_sheet_count=count_sheets(db, project_id),
        unreviewed_count=count_unreviewed_sheets(db, project_id),
        low_confidence_count=count_low_confidence_sheets(db, project_id),
        missing_drawing_no_count=count_missing_field(db, project_id, DrawingSheet.drawing_no),
        missing_drawing_name_count=count_missing_field(db, project_id, DrawingSheet.drawing_name),
        open_error_count=count_open_issues(db, project_id, "error"),
        open_warning_count=count_open_issues(db, project_id, "warning"),
        cad_preview_missing_count=count_cad_preview_missing(db, project_id),
        last_import_at=latest_import_at(db, project_id),
        last_export_at=latest_export_at(db, project_id),
        last_backup_at=latest_backup_at(db, project_id),
    )


def count_files(db: Session, project_id: int) -> int:
    return int(
        db.scalar(
            select(func.count()).select_from(DrawingFile).where(DrawingFile.project_id == project_id)
        )
        or 0
    )


def count_sheets(db: Session, project_id: int) -> int:
    return int(
        db.scalar(
            select(func.count()).select_from(DrawingSheet).where(DrawingSheet.project_id == project_id)
        )
        or 0
    )


def count_unreviewed_sheets(db: Session, project_id: int) -> int:
    return int(
        db.scalar(
            select(func.count())
            .select_from(DrawingSheet)
            .where(DrawingSheet.project_id == project_id, DrawingSheet.review_status != "confirmed")
        )
        or 0
    )


def count_low_confidence_sheets(db: Session, project_id: int) -> int:
    return int(
        db.scalar(
            select(func.count())
            .select_from(DrawingSheet)
            .where(DrawingSheet.project_id == project_id, DrawingSheet.trust_level.in_(["C", "D"]))
        )
        or 0
    )


def count_missing_field(db: Session, project_id: int, column) -> int:
    return int(
        db.scalar(
            select(func.count())
            .select_from(DrawingSheet)
            .where(DrawingSheet.project_id == project_id, or_(column.is_(None), func.trim(column) == ""))
        )
        or 0
    )


def count_open_issues(db: Session, project_id: int, severity: str) -> int:
    return int(
        db.scalar(
            select(func.count(func.distinct(DrawingIssue.sheet_id)))
            .select_from(DrawingIssue)
            .where(
                DrawingIssue.project_id == project_id,
                DrawingIssue.status == "open",
                DrawingIssue.severity == severity,
            )
        )
        or 0
    )


def count_cad_preview_missing(db: Session, project_id: int) -> int:
    return int(
        db.scalar(
            select(func.count())
            .select_from(DrawingSheet)
            .join(DrawingFile, DrawingFile.id == DrawingSheet.file_id)
            .where(
                DrawingSheet.project_id == project_id,
                DrawingFile.source_format.in_(["dxf", "dwg"]),
                or_(
                    DrawingSheet.cad_preview_path.is_(None),
                    DrawingSheet.cad_preview_path == "",
                    DrawingSheet.cad_preview_status != "success",
                ),
            )
        )
        or 0
    )


def latest_export_at(db: Session, project_id: int):
    return db.scalar(
        select(func.max(ExportRecord.created_at)).where(ExportRecord.project_id == project_id)
    )


def latest_import_at(db: Session, project_id: int):
    return db.scalar(
        select(func.max(DrawingFile.created_at)).where(DrawingFile.project_id == project_id)
    )


def latest_backup_at(db: Session, project_id: int):
    return db.scalar(
        select(func.max(BackupRecord.created_at)).where(
            BackupRecord.project_id == project_id,
            BackupRecord.status == "success",
        )
    )
