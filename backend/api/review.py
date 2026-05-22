from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.core.database import get_db
from backend.schemas.audit_log import ReviewAuditLogRead
from backend.schemas.drawing_issue import DrawingIssueRead
from backend.schemas.review import (
    AdoptCandidateRequest,
    AdoptCandidateResult,
    BatchConfirmRequest,
    BatchConfirmResult,
    ConfirmSheetRequest,
    ConfirmSheetResult,
    IssueStatusUpdate,
    RestoreRecommendedRequest,
    ReviewUpdateResult,
    SheetFieldsUpdate,
)
from backend.services import audit_service, issue_service, review_service

router = APIRouter(prefix="/api", tags=["review"])


@router.patch("/sheets/{sheet_id}/fields", response_model=ReviewUpdateResult)
def update_sheet_fields(
    sheet_id: int,
    payload: SheetFieldsUpdate,
    db: Session = Depends(get_db),
) -> ReviewUpdateResult:
    return review_service.update_sheet_fields(db, sheet_id, payload.fields, payload.note)


@router.post("/review/sheets/{sheet_id}/update-fields", response_model=ReviewUpdateResult)
def update_sheet_fields_review_api(
    sheet_id: int,
    payload: SheetFieldsUpdate,
    db: Session = Depends(get_db),
) -> ReviewUpdateResult:
    return review_service.update_sheet_fields(db, sheet_id, payload.fields, payload.note)


@router.post("/sheets/{sheet_id}/adopt-candidate", response_model=AdoptCandidateResult)
def adopt_candidate(
    sheet_id: int,
    payload: AdoptCandidateRequest,
    db: Session = Depends(get_db),
) -> AdoptCandidateResult:
    return review_service.adopt_candidate(db, sheet_id, payload.candidate_id, payload.note)


@router.post("/sheets/{sheet_id}/restore-recommended", response_model=AdoptCandidateResult)
def restore_recommended_field(
    sheet_id: int,
    payload: RestoreRecommendedRequest,
    db: Session = Depends(get_db),
) -> AdoptCandidateResult:
    return review_service.restore_recommended_field(db, sheet_id, payload.field_name, payload.note)


@router.post("/sheets/{sheet_id}/confirm", response_model=ConfirmSheetResult)
def confirm_sheet(
    sheet_id: int,
    payload: ConfirmSheetRequest,
    db: Session = Depends(get_db),
) -> ConfirmSheetResult:
    return review_service.confirm_sheet(db, sheet_id, payload.force, payload.note)


@router.post("/review/sheets/{sheet_id}/confirm", response_model=ConfirmSheetResult)
def confirm_sheet_review_api(
    sheet_id: int,
    payload: ConfirmSheetRequest,
    db: Session = Depends(get_db),
) -> ConfirmSheetResult:
    return review_service.confirm_sheet(db, sheet_id, payload.force, payload.note)


@router.patch("/issues/{issue_id}", response_model=DrawingIssueRead)
def update_issue_status(
    issue_id: int,
    payload: IssueStatusUpdate,
    db: Session = Depends(get_db),
) -> DrawingIssueRead:
    return DrawingIssueRead.model_validate(
        issue_service.update_issue_status(db, issue_id, payload.status, payload.note)
    )


@router.get("/sheets/{sheet_id}/audit-logs", response_model=list[ReviewAuditLogRead])
def list_audit_logs(sheet_id: int, db: Session = Depends(get_db)) -> list[ReviewAuditLogRead]:
    return [ReviewAuditLogRead.model_validate(log) for log in audit_service.list_sheet_logs(db, sheet_id)]


@router.post("/projects/{project_id}/batch-confirm", response_model=BatchConfirmResult)
def batch_confirm_project(
    project_id: int,
    payload: BatchConfirmRequest,
    db: Session = Depends(get_db),
) -> BatchConfirmResult:
    return review_service.batch_confirm_project(
        db,
        project_id,
        payload.sheet_ids,
        payload.note,
        payload.confirm_mode,
        payload.only_without_errors,
    )


@router.post("/review/batch-confirm", response_model=BatchConfirmResult)
def batch_confirm(
    payload: BatchConfirmRequest,
    db: Session = Depends(get_db),
) -> BatchConfirmResult:
    return review_service.batch_confirm_project(
        db,
        payload.project_id,
        payload.sheet_ids,
        payload.note,
        payload.confirm_mode,
        payload.only_without_errors,
    )
