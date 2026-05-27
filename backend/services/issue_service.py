from datetime import UTC, datetime
from math import ceil

from sqlalchemy import delete, func, or_, select
from sqlalchemy.orm import Session

from backend.models.drawing_issue import DrawingIssue
from backend.models.drawing_sheet import DrawingSheet
from backend.models.field_value import FieldValue
from backend.schemas.drawing_issue import DrawingIssueRead
from backend.schemas.pagination import PaginatedResponse
from backend.services import audit_service
from recognizer.rules.issue_rules import conflict_code, issue_template

PERSISTENT_MACHINE_ISSUE_PREFIXES = ("CAD_TABLE_EXTRACT_", "CAD_BLOCK_STATS_")


def clear_open_machine_issues(db: Session, sheet_id: int) -> None:
    db.execute(
        delete(DrawingIssue).where(
            DrawingIssue.sheet_id == sheet_id,
            DrawingIssue.status == "open",
            DrawingIssue.issue_code.not_like("CAD_TABLE_EXTRACT_%"),
            DrawingIssue.issue_code.not_like("CAD_BLOCK_STATS_%"),
        )
    )


def add_issue(
    db: Session,
    *,
    project_id: int,
    batch_id: int,
    file_id: int,
    sheet_id: int,
    issue_code: str,
    severity: str | None = None,
    message: str | None = None,
    suggestion: str | None = None,
) -> DrawingIssue:
    default_severity, default_message, default_suggestion = issue_template(issue_code)
    issue = DrawingIssue(
        project_id=project_id,
        batch_id=batch_id,
        file_id=file_id,
        sheet_id=sheet_id,
        issue_code=issue_code,
        severity=severity or default_severity,
        message=message or default_message,
        suggestion=suggestion or default_suggestion,
        status="open",
    )
    if issue_code in {"LOW_CONFIDENCE", "OCR_TEXT_EMPTY", "PDF_TEXT_EMPTY"} and message is None:
        issue.message = default_message
    db.add(issue)
    return issue


def add_missing_field_issues(db: Session, sheet, values: dict[str, str | None]) -> None:
    missing_codes = {
        "drawing_no": "DRAWING_NO_EMPTY",
        "drawing_name": "DRAWING_NAME_EMPTY",
        "discipline": "DISCIPLINE_EMPTY",
        "version": "VERSION_EMPTY",
        "issue_date": "ISSUE_DATE_EMPTY",
    }
    for field_name, code in missing_codes.items():
        if not values.get(field_name):
            add_issue_for_sheet(db, sheet, code)


def add_conflict_issue(db: Session, sheet, field_name: str, sources: list[str], values: list[str]) -> None:
    code = conflict_code(field_name, sources)
    add_issue_for_sheet(
        db,
        sheet,
        code,
        severity="warning" if code != "FIELD_CONFLICT_HIGH" else "error",
        message=f"{field_name} 候选值存在冲突：{' / '.join(values)}",
        suggestion="请在后续校核阶段结合来源证据确认字段值。",
    )


def add_duplicate_issues(db: Session, project_id: int, drawing_no: str | None) -> None:
    if not drawing_no:
        return
    rows = db.scalars(
        select(FieldValue).where(
            FieldValue.project_id == project_id,
            FieldValue.field_name == "drawing_no",
            FieldValue.normalized_value == drawing_no,
        )
    ).all()
    sheet_ids = sorted({row.sheet_id for row in rows})
    if len(sheet_ids) <= 1:
        return
    for field_value in rows:
        exists = db.scalar(
            select(DrawingIssue.id).where(
                DrawingIssue.sheet_id == field_value.sheet_id,
                DrawingIssue.issue_code == "DRAWING_NO_DUPLICATE",
                DrawingIssue.status == "open",
            )
        )
        if exists:
            continue
        add_issue(
            db,
            project_id=field_value.project_id,
            batch_id=field_value.batch_id,
            file_id=field_value.file_id,
            sheet_id=field_value.sheet_id,
            issue_code="DRAWING_NO_DUPLICATE",
            severity="error",
            message=f"发现重复图号：{drawing_no}",
            suggestion="请检查是否为不同版本图纸，或在后续校核阶段修正图号/版本。",
        )


def add_issue_for_sheet(
    db: Session,
    sheet,
    issue_code: str,
    severity: str | None = None,
    message: str | None = None,
    suggestion: str | None = None,
) -> DrawingIssue:
    return add_issue(
        db,
        project_id=sheet.project_id,
        batch_id=sheet.batch_id,
        file_id=sheet.file_id,
        sheet_id=sheet.id,
        issue_code=issue_code,
        severity=severity,
        message=message,
        suggestion=suggestion,
    )


def list_project_issues(
    db: Session,
    project_id: int,
    severity: str | None = None,
    issue_status: str | None = None,
    sheet_id: int | None = None,
    issue_code: str | None = None,
) -> list[DrawingIssue]:
    query = select(DrawingIssue).where(DrawingIssue.project_id == project_id)
    if severity:
        query = query.where(DrawingIssue.severity == severity)
    if issue_status:
        query = query.where(DrawingIssue.status == issue_status)
    if sheet_id is not None:
        query = query.where(DrawingIssue.sheet_id == sheet_id)
    if issue_code:
        query = query.where(DrawingIssue.issue_code == issue_code)
    return db.scalars(query.order_by(DrawingIssue.created_at.desc(), DrawingIssue.id.desc())).all()


def list_sheet_issues(db: Session, sheet_id: int) -> list[DrawingIssue]:
    return db.scalars(
        select(DrawingIssue)
        .where(DrawingIssue.sheet_id == sheet_id)
        .order_by(DrawingIssue.created_at.desc(), DrawingIssue.id.desc())
    ).all()


def list_project_issues_paginated(
    db: Session,
    project_id: int,
    severity: str | None = None,
    issue_status: str | None = None,
    sheet_id: int | None = None,
    issue_code: str | None = None,
    keyword: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> PaginatedResponse[DrawingIssueRead]:
    query = select(DrawingIssue).where(DrawingIssue.project_id == project_id)
    if severity:
        query = query.where(DrawingIssue.severity == severity)
    if issue_status:
        query = query.where(DrawingIssue.status == issue_status)
    if sheet_id is not None:
        query = query.where(DrawingIssue.sheet_id == sheet_id)
    if issue_code:
        query = query.where(DrawingIssue.issue_code == issue_code)
    if keyword:
        like = f"%{keyword.strip()}%"
        query = query.where(
            or_(
                DrawingIssue.issue_code.ilike(like),
                DrawingIssue.message.ilike(like),
                DrawingIssue.suggestion.ilike(like),
            )
        )

    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    rows = db.scalars(
        query.order_by(DrawingIssue.created_at.desc(), DrawingIssue.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return PaginatedResponse[DrawingIssueRead](
        items=[DrawingIssueRead.model_validate(issue) for issue in rows],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=ceil(total / page_size) if total else 0,
    )


def update_issue_status(db: Session, issue_id: int, new_status: str, note: str | None = None) -> DrawingIssue:
    if new_status not in {"open", "resolved", "ignored", "reopened"}:
        from fastapi import HTTPException, status

        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="问题状态不合法")
    issue = db.get(DrawingIssue, issue_id)
    if issue is None:
        from fastapi import HTTPException, status

        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="问题不存在")
    sheet = db.get(DrawingSheet, issue.sheet_id)
    old_status = issue.status
    issue.status = "open" if new_status == "reopened" else new_status
    issue.resolved_at = datetime.now(UTC) if new_status == "resolved" else None
    action_type = {
        "resolved": "issue_resolved",
        "ignored": "issue_ignored",
        "reopened": "issue_reopened",
        "open": "issue_reopened",
    }[new_status]
    if sheet is not None:
        audit_service.write_log(
            db,
            sheet=sheet,
            action_type=action_type,
            old_value=old_status,
            new_value=issue.status,
            note=note,
        )
    db.commit()
    db.refresh(issue)
    return issue
