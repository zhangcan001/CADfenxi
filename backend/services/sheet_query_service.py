from math import ceil

from sqlalchemy import asc, case, desc, func, or_, select
from sqlalchemy.orm import Session

from backend.models.drawing_file import DrawingFile
from backend.models.drawing_issue import DrawingIssue
from backend.models.drawing_sheet import DrawingSheet
from backend.schemas.drawing_sheet import DrawingSheetListItem
from backend.schemas.pagination import PaginatedResponse
from backend.schemas.sheet_query import SheetQueryParams

SORT_COLUMNS = {
    "page_no": DrawingSheet.page_no,
    "drawing_no": DrawingSheet.drawing_no,
    "discipline": DrawingSheet.discipline,
    "confidence_score": DrawingSheet.confidence_score,
    "trust_level": DrawingSheet.trust_level,
    "status": DrawingSheet.status,
    "created_at": DrawingSheet.created_at,
    "updated_at": DrawingSheet.updated_at,
    "file_name": DrawingFile.original_name,
    "original_file_name": DrawingFile.original_name,
}

MISSING_FIELDS = {
    "drawing_no": DrawingSheet.drawing_no,
    "drawing_name": DrawingSheet.drawing_name,
    "discipline": DrawingSheet.discipline,
    "issue_date": DrawingSheet.issue_date,
    "version": DrawingSheet.version,
}


def list_project_sheets(
    db: Session,
    project_id: int,
    params: SheetQueryParams,
) -> PaginatedResponse[DrawingSheetListItem]:
    issue_counts = issue_counts_subquery()
    query = (
        select(
            DrawingSheet,
            DrawingFile.original_name,
            DrawingFile.source_format,
            func.coalesce(issue_counts.c.issue_count, 0).label("issue_count"),
            func.coalesce(issue_counts.c.error_count, 0).label("error_count"),
            func.coalesce(issue_counts.c.warning_count, 0).label("warning_count"),
            func.coalesce(issue_counts.c.info_count, 0).label("info_count"),
        )
        .join(DrawingFile, DrawingFile.id == DrawingSheet.file_id)
        .outerjoin(issue_counts, issue_counts.c.sheet_id == DrawingSheet.id)
        .where(DrawingSheet.project_id == project_id)
    )
    query = apply_filters(query, params, issue_counts)

    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    if params.sort_by == "default":
        query = query.order_by(
            (DrawingSheet.review_status == "confirmed").asc(),
            desc(func.coalesce(issue_counts.c.error_count, 0)),
            asc(case((DrawingSheet.trust_level == "D", 0), (DrawingSheet.trust_level == "C", 1), (DrawingSheet.trust_level == "B", 2), (DrawingSheet.trust_level == "A", 3), else_=4)),
            asc(DrawingSheet.drawing_no),
            DrawingSheet.id.asc(),
        )
    else:
        sort_expression = sort_column(params.sort_by, issue_counts)
        if params.sort_order.lower() == "asc":
            query = query.order_by(asc(sort_expression), DrawingSheet.id.asc())
        else:
            query = query.order_by(desc(sort_expression), DrawingSheet.id.desc())

    offset = (params.page - 1) * params.page_size
    rows = db.execute(query.offset(offset).limit(params.page_size)).all()
    items = [
        sheet_item(
            sheet,
            original_name,
            source_format,
            issue_count,
            error_count,
            warning_count,
            info_count,
        )
        for sheet, original_name, source_format, issue_count, error_count, warning_count, info_count in rows
    ]
    return PaginatedResponse[DrawingSheetListItem](
        items=items,
        total=total,
        page=params.page,
        page_size=params.page_size,
        total_pages=ceil(total / params.page_size) if total else 0,
    )


def issue_counts_subquery():
    return (
        select(
            DrawingIssue.sheet_id.label("sheet_id"),
            func.count(DrawingIssue.id).label("issue_count"),
            func.sum(case((DrawingIssue.severity == "error", 1), else_=0)).label("error_count"),
            func.sum(case((DrawingIssue.severity == "warning", 1), else_=0)).label("warning_count"),
            func.sum(case((DrawingIssue.severity == "info", 1), else_=0)).label("info_count"),
        )
        .where(DrawingIssue.status == "open")
        .group_by(DrawingIssue.sheet_id)
        .subquery()
    )


def apply_filters(query, params: SheetQueryParams, issue_counts):
    if params.keyword:
        keyword = f"%{params.keyword.strip()}%"
        query = query.where(
            or_(
                DrawingSheet.drawing_no.ilike(keyword),
                DrawingSheet.drawing_name.ilike(keyword),
                DrawingFile.original_name.ilike(keyword),
            )
        )
    if params.batch_id is not None:
        query = query.where(DrawingSheet.batch_id == params.batch_id)
    if params.file_id is not None:
        query = query.where(DrawingSheet.file_id == params.file_id)
    if params.discipline:
        query = query.where(DrawingSheet.discipline == params.discipline)
    if params.status:
        query = query.where(DrawingSheet.status == params.status)
    if params.review_status:
        query = query.where(DrawingSheet.review_status == params.review_status)
    if params.trust_level:
        levels = [level.strip() for level in params.trust_level.split(",") if level.strip()]
        query = query.where(DrawingSheet.trust_level.in_(levels))
    if params.low_confidence is True:
        query = query.where(DrawingSheet.trust_level.in_(["C", "D"]))
    if params.low_confidence is False:
        query = query.where(DrawingSheet.trust_level.in_(["A", "B"]))
    if params.source_format:
        query = query.where(DrawingFile.source_format == params.source_format)
    if params.issue_severity:
        query = query.where(open_issue_exists(severity=params.issue_severity))
    if params.issue_code:
        query = query.where(open_issue_exists(issue_code=params.issue_code))
    if params.has_error is True:
        query = query.where(func.coalesce(issue_counts.c.error_count, 0) > 0)
    if params.has_error is False:
        query = query.where(func.coalesce(issue_counts.c.error_count, 0) == 0)
    if params.has_warning is True:
        query = query.where(func.coalesce(issue_counts.c.warning_count, 0) > 0)
    if params.has_warning is False:
        query = query.where(func.coalesce(issue_counts.c.warning_count, 0) == 0)
    if params.has_issue is True:
        query = query.where(func.coalesce(issue_counts.c.issue_count, 0) > 0)
    if params.has_issue is False:
        query = query.where(func.coalesce(issue_counts.c.issue_count, 0) == 0)
    if params.missing_field:
        column = MISSING_FIELDS.get(params.missing_field)
        if column is not None:
            if params.missing_field == "issue_date":
                query = query.where(column.is_(None))
            else:
                query = query.where(or_(column.is_(None), func.trim(column) == ""))
    return query


def open_issue_exists(severity: str | None = None, issue_code: str | None = None):
    exists_query = select(DrawingIssue.id).where(
        DrawingIssue.sheet_id == DrawingSheet.id,
        DrawingIssue.status == "open",
    )
    if severity:
        exists_query = exists_query.where(DrawingIssue.severity == severity)
    if issue_code:
        exists_query = exists_query.where(DrawingIssue.issue_code == issue_code)
    return exists_query.exists()


def sort_column(sort_by: str, issue_counts):
    if sort_by == "issue_count":
        return func.coalesce(issue_counts.c.issue_count, 0)
    if sort_by == "error_count":
        return func.coalesce(issue_counts.c.error_count, 0)
    if sort_by == "warning_count":
        return func.coalesce(issue_counts.c.warning_count, 0)
    if sort_by == "unconfirmed_first":
        return DrawingSheet.review_status == "confirmed"
    return SORT_COLUMNS.get(sort_by, DrawingSheet.created_at)


def sheet_item(
    sheet: DrawingSheet,
    original_name: str,
    source_format: str,
    issue_count: int,
    error_count: int,
    warning_count: int,
    info_count: int,
) -> DrawingSheetListItem:
    return DrawingSheetListItem.model_validate(
        {
            **sheet.__dict__,
            "issue_date": sheet.issue_date.isoformat() if sheet.issue_date else None,
            "issue_count": issue_count,
            "error_count": error_count,
            "warning_count": warning_count,
            "info_count": info_count,
            "thumbnail_url": f"/api/sheets/{sheet.id}/thumbnail" if sheet.thumbnail_path else None,
            "preview_url": f"/api/sheets/{sheet.id}/preview" if sheet.preview_path else None,
            "cad_preview_url": f"/api/sheets/{sheet.id}/cad-preview-image" if sheet.cad_preview_path else None,
            "original_file_name": original_name,
            "source_format": source_format,
        }
    )
