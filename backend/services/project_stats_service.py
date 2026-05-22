from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.models.drawing_file import DrawingFile
from backend.models.drawing_issue import DrawingIssue
from backend.models.drawing_sheet import DrawingSheet
from backend.schemas.project import ProjectStats


def get_project_stats(db: Session, project_id: int) -> ProjectStats:
    return ProjectStats(
        file_count=count_files(db, project_id),
        sheet_count=count_sheets(db, project_id),
        preprocessed_count=count_sheets(db, project_id, "preprocessed"),
        recognized_count=count_sheets(db, project_id, "recognized"),
        need_review_count=count_sheets(db, project_id, "need_review"),
        failed_count=count_sheets(db, project_id, "failed"),
        confirmed_count=count_sheets(db, project_id, "confirmed"),
        issue_count=count_issues(db, project_id),
        error_issue_count=count_issues(db, project_id, "error"),
        warning_issue_count=count_issues(db, project_id, "warning"),
        trust_level_a_count=count_trust_level(db, project_id, "A"),
        trust_level_b_count=count_trust_level(db, project_id, "B"),
        trust_level_c_count=count_trust_level(db, project_id, "C"),
        trust_level_d_count=count_trust_level(db, project_id, "D"),
    )


def count_files(db: Session, project_id: int) -> int:
    return db.scalar(
        select(func.count()).select_from(DrawingFile).where(DrawingFile.project_id == project_id)
    ) or 0


def count_sheets(db: Session, project_id: int, status: str | None = None) -> int:
    query = select(func.count()).select_from(DrawingSheet).where(DrawingSheet.project_id == project_id)
    if status:
        query = query.where(DrawingSheet.status == status)
    return db.scalar(query) or 0


def count_issues(db: Session, project_id: int, severity: str | None = None) -> int:
    query = (
        select(func.count())
        .select_from(DrawingIssue)
        .where(DrawingIssue.project_id == project_id, DrawingIssue.status == "open")
    )
    if severity:
        query = query.where(DrawingIssue.severity == severity)
    return db.scalar(query) or 0


def count_trust_level(db: Session, project_id: int, trust_level: str) -> int:
    return db.scalar(
        select(func.count())
        .select_from(DrawingSheet)
        .where(DrawingSheet.project_id == project_id, DrawingSheet.trust_level == trust_level)
    ) or 0
