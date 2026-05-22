from fastapi import APIRouter, Depends, Query
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from backend.core.database import get_db
from backend.schemas.drawing_sheet import (
    BatchSplitResult,
    DrawingSheetListItem,
    DrawingSheetRead,
    FileSplitResult,
)
from backend.schemas.pagination import PaginatedResponse
from backend.schemas.sheet_query import SheetQueryParams
from backend.services import pdf_split_service, sheet_query_service

router = APIRouter(prefix="/api", tags=["sheets"])


@router.post("/files/{file_id}/split", response_model=FileSplitResult)
def split_file(file_id: int, db: Session = Depends(get_db)) -> FileSplitResult:
    return pdf_split_service.split_file(db, file_id)


@router.post("/imports/{batch_id}/split", response_model=BatchSplitResult)
def split_batch(batch_id: int, db: Session = Depends(get_db)) -> BatchSplitResult:
    return pdf_split_service.split_batch(db, batch_id)


@router.get("/projects/{project_id}/sheets", response_model=PaginatedResponse[DrawingSheetListItem])
def list_project_sheets(
    project_id: int,
    keyword: str | None = Query(default=None),
    file_id: int | None = Query(default=None),
    batch_id: int | None = Query(default=None),
    discipline: str | None = Query(default=None),
    status: str | None = Query(default=None),
    review_status: str | None = Query(default=None),
    trust_level: str | None = Query(default=None),
    source_format: str | None = Query(default=None),
    issue_severity: str | None = Query(default=None),
    issue_code: str | None = Query(default=None),
    has_issue: bool | None = Query(default=None),
    has_error: bool | None = Query(default=None),
    has_warning: bool | None = Query(default=None),
    low_confidence: bool | None = Query(default=None),
    missing_field: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    sort_by: str = Query(default="default"),
    sort_order: str = Query(default="asc"),
    db: Session = Depends(get_db),
) -> PaginatedResponse[DrawingSheetListItem]:
    return sheet_query_service.list_project_sheets(
        db,
        project_id,
        SheetQueryParams(
            keyword=keyword,
            file_id=file_id,
            batch_id=batch_id,
            discipline=discipline,
            status=status,
            review_status=review_status,
            trust_level=trust_level,
            source_format=source_format,
            issue_severity=issue_severity,
            issue_code=issue_code,
            has_issue=has_issue,
            has_error=has_error,
            has_warning=has_warning,
            low_confidence=low_confidence,
            missing_field=missing_field,
            page=page,
            page_size=page_size,
            sort_by=sort_by,
            sort_order=sort_order,
        ),
    )


@router.get("/sheets/{sheet_id}", response_model=DrawingSheetRead)
def get_sheet(sheet_id: int, db: Session = Depends(get_db)) -> DrawingSheetRead:
    return pdf_split_service.get_sheet_detail(db, sheet_id)


@router.get("/sheets/{sheet_id}/preview")
def get_sheet_preview(sheet_id: int, db: Session = Depends(get_db)) -> FileResponse:
    path = pdf_split_service.sheet_preview_path(db, sheet_id, "preview")
    return FileResponse(path, media_type="image/png")


@router.get("/sheets/{sheet_id}/thumbnail")
def get_sheet_thumbnail(sheet_id: int, db: Session = Depends(get_db)) -> FileResponse:
    path = pdf_split_service.sheet_preview_path(db, sheet_id, "thumbnail")
    return FileResponse(path, media_type="image/jpeg")
