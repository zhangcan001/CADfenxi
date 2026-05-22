from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.models.review_audit_log import ReviewAuditLog


def write_log(
    db: Session,
    *,
    sheet,
    action_type: str,
    field_name: str | None = None,
    old_value: str | None = None,
    new_value: str | None = None,
    note: str | None = None,
    operator: str = "default_user",
) -> ReviewAuditLog:
    log = ReviewAuditLog(
        project_id=sheet.project_id,
        batch_id=sheet.batch_id,
        file_id=sheet.file_id,
        sheet_id=sheet.id,
        field_name=field_name,
        old_value=old_value,
        new_value=new_value,
        action_type=action_type,
        operator=operator,
        note=note,
    )
    db.add(log)
    return log


def list_sheet_logs(db: Session, sheet_id: int) -> list[ReviewAuditLog]:
    return db.scalars(
        select(ReviewAuditLog)
        .where(ReviewAuditLog.sheet_id == sheet_id)
        .order_by(ReviewAuditLog.created_at.desc(), ReviewAuditLog.id.desc())
    ).all()
