from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from backend.models.drawing_issue import DrawingIssue
from backend.models.drawing_sheet import DrawingSheet
from backend.models.field_evidence import FieldEvidence
from backend.models.field_value import FieldValue
from backend.models.recognition_candidate import RecognitionCandidate
from backend.schemas.drawing_issue import DrawingIssueRead
from backend.schemas.field_value import FieldValueRead
from backend.schemas.review import (
    AdoptCandidateResult,
    BatchConfirmResult,
    ConfirmSheetResult,
    ReviewUpdateResult,
)
from backend.services import audit_service, fusion_service, scoring_service
from recognizer.fusion.field_fusion import choose_field_value
from recognizer.normalizer.date import normalize_issue_date
from recognizer.normalizer.discipline import infer_discipline
from recognizer.normalizer.drawing_no import normalize_drawing_no
from recognizer.normalizer.version import normalize_version

CORE_FIELDS = ["drawing_no", "drawing_name", "discipline", "version", "issue_date"]


def update_sheet_fields(
    db: Session,
    sheet_id: int,
    fields: dict[str, str | None],
    note: str | None = None,
) -> ReviewUpdateResult:
    sheet = get_sheet_or_404(db, sheet_id)
    updated = []
    for field_name, value in fields.items():
        if field_name not in CORE_FIELDS:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="字段名不合法")
        updated.append(
            upsert_field_value(
                db, sheet, field_name, value or "", "manual", 100, True, note, "field_edit"
            )
        )
    refresh_sheet_after_review(db, sheet)
    db.commit()
    return review_result(db, sheet.id, updated)


def adopt_candidate(
    db: Session,
    sheet_id: int,
    candidate_id: int,
    note: str | None = None,
) -> AdoptCandidateResult:
    sheet = get_sheet_or_404(db, sheet_id)
    candidate = db.get(RecognitionCandidate, candidate_id)
    if candidate is None or candidate.sheet_id != sheet_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="候选值不存在")
    value = candidate.normalized_value or candidate.candidate_value
    field_value = upsert_field_value(
        db,
        sheet,
        candidate.field_name,
        value,
        candidate.source_type,
        candidate.confidence,
        True,
        note,
        "candidate_adopted",
    )
    refresh_sheet_after_review(db, sheet)
    db.commit()
    db.refresh(field_value)
    db.refresh(sheet)
    issues = open_issues(db, sheet.id)
    return AdoptCandidateResult(
        field_value=FieldValueRead.model_validate(field_value),
        confidence_score=int(sheet.confidence_score or 0),
        trust_level=sheet.trust_level or "D",
        issues=[DrawingIssueRead.model_validate(issue) for issue in issues],
    )


def restore_recommended_field(
    db: Session,
    sheet_id: int,
    field_name: str,
    note: str | None = None,
) -> AdoptCandidateResult:
    sheet = get_sheet_or_404(db, sheet_id)
    if field_name not in CORE_FIELDS:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="字段名不合法")
    candidates = db.scalars(
        select(RecognitionCandidate)
        .where(RecognitionCandidate.sheet_id == sheet_id, RecognitionCandidate.field_name == field_name)
        .order_by(RecognitionCandidate.confidence.desc(), RecognitionCandidate.id.asc())
    ).all()
    choice = choose_field_value(fusion_service.filter_candidates_for_sheet(candidates))
    if choice is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="暂无机器推荐值")
    field_value = upsert_field_value(
        db,
        sheet,
        field_name,
        choice.display_value,
        choice.final_source,
        choice.confidence,
        True,
        note,
        "recommended_restored",
    )
    replace_evidence(db, field_value, choice.evidence_ids, candidates)
    refresh_sheet_after_review(db, sheet)
    db.commit()
    db.refresh(field_value)
    db.refresh(sheet)
    return AdoptCandidateResult(
        field_value=FieldValueRead.model_validate(field_value),
        confidence_score=int(sheet.confidence_score or 0),
        trust_level=sheet.trust_level or "D",
        issues=[DrawingIssueRead.model_validate(issue) for issue in open_issues(db, sheet.id)],
    )


def confirm_sheet(db: Session, sheet_id: int, force: bool = False, note: str | None = None) -> ConfirmSheetResult:
    sheet = get_sheet_or_404(db, sheet_id)
    missing = [field for field in ["drawing_no", "drawing_name", "discipline"] if not getattr(sheet, field)]
    if missing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"缺少必填字段：{', '.join(missing)}")
    errors = [issue for issue in open_issues(db, sheet.id) if issue.severity == "error"]
    if errors and not force:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"message": "存在阻断问题，暂不能确认", "errors": [issue.issue_code for issue in errors]},
        )
    now = datetime.now(timezone.utc)
    for field_value in field_values(db, sheet.id):
        if field_value.field_name in CORE_FIELDS and field_value.display_value:
            field_value.is_reviewed = True
            field_value.reviewed_at = now
    sheet.status = "confirmed"
    sheet.review_status = "confirmed"
    audit_service.write_log(
        db,
        sheet=sheet,
        action_type="sheet_confirmed",
        old_value=None,
        new_value="confirmed",
        note=note if not force else f"{note or ''} force=true".strip(),
    )
    db.commit()
    db.refresh(sheet)
    return ConfirmSheetResult(
        sheet_id=sheet.id,
        status=sheet.status,
        review_status=sheet.review_status,
        forced_confirm=force,
    )


def batch_confirm_project(
    db: Session,
    project_id: int | None,
    sheet_ids: list[int],
    note: str | None = None,
    confirm_mode: str = "selected",
    only_without_errors: bool = True,
) -> BatchConfirmResult:
    confirmed = 0
    items = []
    requested_ids = list(dict.fromkeys(sheet_ids))
    if not requested_ids:
        return BatchConfirmResult(
            project_id=project_id,
            requested_count=0,
            confirmed_count=0,
            skipped_count=0,
            items=[],
            skipped=[],
        )
    query = select(DrawingSheet).where(DrawingSheet.id.in_(requested_ids)).order_by(DrawingSheet.id)
    if project_id is not None:
        query = query.where(DrawingSheet.project_id == project_id)
    sheets = db.scalars(query).all()
    found_ids = {sheet.id for sheet in sheets}
    for sheet_id in requested_ids:
        if sheet_id not in found_ids:
            items.append({"sheet_id": sheet_id, "status": "skipped", "reason": "图纸页不存在"})
    for sheet in sheets:
        skip_reason = batch_confirm_skip_reason(db, sheet, confirm_mode, only_without_errors)
        if skip_reason:
            items.append({"sheet_id": sheet.id, "status": "skipped", "reason": skip_reason})
            continue
        old_status = sheet.review_status
        sheet.status = "confirmed"
        sheet.review_status = "confirmed"
        audit_service.write_log(
            db,
            sheet=sheet,
            action_type="sheet_batch_confirmed",
            old_value=old_status,
            new_value="confirmed",
            note=note,
        )
        confirmed += 1
        items.append({"sheet_id": sheet.id, "status": "confirmed"})
    db.commit()
    skipped = [item for item in items if item["status"] == "skipped"]
    return BatchConfirmResult(
        project_id=project_id,
        requested_count=len(requested_ids),
        confirmed_count=confirmed,
        skipped_count=len(skipped),
        items=items,
        skipped=skipped,
    )


def batch_confirm_skip_reason(
    db: Session,
    sheet: DrawingSheet,
    confirm_mode: str,
    only_without_errors: bool,
) -> str | None:
    if sheet.status == "failed":
        return "已标记为 failed"
    if not sheet.drawing_no:
        return "drawing_no 缺失"
    if not sheet.drawing_name:
        return "drawing_name 缺失"
    errors = [issue for issue in open_issues(db, sheet.id) if issue.severity == "error"]
    open_error_codes = {issue.issue_code for issue in errors}
    if "OPEN_ERROR" in open_error_codes or "DXF_OPEN_FAILED" in open_error_codes or sheet.error_code:
        return "存在 open error"
    if only_without_errors and errors:
        return "存在未处理错误"
    if confirm_mode == "trust_a" and sheet.trust_level != "A":
        return "可信等级不是 A"
    if confirm_mode == "trust_b_or_above" and sheet.trust_level not in {"A", "B"}:
        return "可信等级不是 A/B"
    if confirm_mode == "complete_fields" and not all(
        getattr(sheet, field) for field in ["drawing_no", "drawing_name", "discipline", "issue_date"]
    ):
        return "字段不完整"
    return None


def upsert_field_value(
    db: Session,
    sheet: DrawingSheet,
    field_name: str,
    value: str,
    final_source: str,
    confidence: float,
    is_reviewed: bool,
    note: str | None,
    action_type: str,
) -> FieldValue:
    normalized = normalize_field(field_name, value)
    display = normalized or value
    existing = db.scalar(select(FieldValue).where(FieldValue.sheet_id == sheet.id, FieldValue.field_name == field_name))
    old_value = existing.display_value if existing else None
    now = datetime.now(timezone.utc)
    if existing is None:
        existing = FieldValue(
            project_id=sheet.project_id,
            batch_id=sheet.batch_id,
            file_id=sheet.file_id,
            sheet_id=sheet.id,
            field_name=field_name,
            raw_value=value,
            normalized_value=normalized,
            display_value=display,
            final_source=final_source,
            confidence=confidence,
            is_reviewed=is_reviewed,
            reviewed_at=now if is_reviewed else None,
        )
        db.add(existing)
        db.flush()
    else:
        existing.raw_value = value
        existing.normalized_value = normalized
        existing.display_value = display
        existing.final_source = final_source
        existing.confidence = confidence
        existing.is_reviewed = is_reviewed
        existing.reviewed_at = now if is_reviewed else existing.reviewed_at
    setattr(sheet, field_name, fusion_service.parse_issue_date(display) if field_name == "issue_date" else display)
    if sheet.status == "confirmed" and action_type in {"field_edit", "candidate_adopted"}:
        sheet.status = "need_review"
        sheet.review_status = "unreviewed"
    audit_service.write_log(
        db,
        sheet=sheet,
        field_name=field_name,
        old_value=old_value,
        new_value=display,
        action_type=action_type,
        note=note,
    )
    return existing


def replace_evidence(
    db: Session,
    field_value: FieldValue,
    evidence_ids: list[int],
    candidates: list[RecognitionCandidate],
) -> None:
    db.execute(delete(FieldEvidence).where(FieldEvidence.field_value_id == field_value.id))
    fusion_service.add_evidence(db, field_value, evidence_ids, candidates)


def refresh_sheet_after_review(db: Session, sheet: DrawingSheet) -> None:
    values = {value.field_name: value.display_value for value in field_values(db, sheet.id)}
    confidences = {value.field_name: value.confidence for value in field_values(db, sheet.id)}
    score = scoring_service.score_sheet(confidences)
    sheet.confidence_score = score
    issues = open_issues(db, sheet.id)
    severities = [issue.severity for issue in issues]
    sheet.trust_level = scoring_service.trust_level(score, values, severities)
    if sheet.status != "confirmed":
        sheet.review_status = "unreviewed"
        sheet.status = "need_review" if severities else "recognized"


def review_result(db: Session, sheet_id: int, updated: list[FieldValue]) -> ReviewUpdateResult:
    sheet = get_sheet_or_404(db, sheet_id)
    for value in updated:
        db.refresh(value)
    issues = open_issues(db, sheet_id)
    return ReviewUpdateResult(
        sheet_id=sheet_id,
        updated_fields=[FieldValueRead.model_validate(value) for value in updated],
        confidence_score=int(sheet.confidence_score or 0),
        trust_level=sheet.trust_level or "D",
        issues=[DrawingIssueRead.model_validate(issue) for issue in issues],
    )


def normalize_field(field_name: str, value: str) -> str | None:
    if field_name == "drawing_no":
        return normalize_drawing_no(value)
    if field_name == "version":
        return normalize_version(value)
    if field_name == "issue_date":
        return normalize_issue_date(value)
    if field_name == "discipline":
        return infer_discipline(value) or value.strip() or None
    return value.strip() or None


def get_sheet_or_404(db: Session, sheet_id: int) -> DrawingSheet:
    sheet = db.get(DrawingSheet, sheet_id)
    if sheet is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="图纸页不存在")
    return sheet


def field_values(db: Session, sheet_id: int) -> list[FieldValue]:
    return db.scalars(select(FieldValue).where(FieldValue.sheet_id == sheet_id)).all()


def open_issues(db: Session, sheet_id: int) -> list[DrawingIssue]:
    return db.scalars(
        select(DrawingIssue).where(DrawingIssue.sheet_id == sheet_id, DrawingIssue.status == "open")
    ).all()
