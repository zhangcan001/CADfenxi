from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from backend.core.database import get_db
from backend.schemas.drawing_issue import DrawingIssueRead
from backend.schemas.pagination import PaginatedResponse
from backend.services import issue_service

router = APIRouter(prefix="/api", tags=["issues"])


@router.get("/projects/{project_id}/issues", response_model=PaginatedResponse[DrawingIssueRead])
def list_project_issues(
    project_id: int,
    severity: str | None = Query(default=None),
    status: str | None = Query(default=None),
    sheet_id: int | None = Query(default=None),
    issue_code: str | None = Query(default=None),
    keyword: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
) -> PaginatedResponse[DrawingIssueRead]:
    return issue_service.list_project_issues_paginated(
        db,
        project_id,
        severity=severity,
        issue_status=status,
        sheet_id=sheet_id,
        issue_code=issue_code,
        keyword=keyword,
        page=page,
        page_size=page_size,
    )


@router.get("/sheets/{sheet_id}/issues", response_model=list[DrawingIssueRead])
def list_sheet_issues(sheet_id: int, db: Session = Depends(get_db)) -> list[DrawingIssueRead]:
    return [
        DrawingIssueRead.model_validate(issue)
        for issue in issue_service.list_sheet_issues(db, sheet_id)
    ]
