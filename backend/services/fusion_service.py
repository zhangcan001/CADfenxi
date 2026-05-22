from collections import defaultdict
from datetime import date

from fastapi import HTTPException, status
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from backend.core.config import settings
from backend.models.drawing_file import DrawingFile
from backend.models.drawing_issue import DrawingIssue
from backend.models.drawing_sheet import DrawingSheet
from backend.models.field_evidence import FieldEvidence
from backend.models.field_value import FieldValue
from backend.models.import_batch import ImportBatch
from backend.models.recognition_candidate import RecognitionCandidate
from backend.schemas.drawing_issue import DrawingIssueRead
from backend.schemas.field_evidence import FieldEvidenceRead
from backend.schemas.field_value import BatchFusionResult, FieldValueRead, SheetFusionResult
from backend.services import cad_sheet_service, issue_service, scoring_service
from recognizer.cad_engine.cad_text_rules import (
    is_suspect_drawing_name_candidate,
    is_suspect_drawing_no_candidate,
)
from recognizer.cad_engine.cad_json_writer import cad_parse_output_path, read_cad_json
from recognizer.fusion.field_fusion import choose_field_value, value_key

CORE_FIELDS = ["drawing_no", "drawing_name", "discipline", "version", "issue_date"]


def fuse_fields_for_sheet(db: Session, sheet_id: int) -> SheetFusionResult:
    sheet = db.get(DrawingSheet, sheet_id)
    if sheet is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="图纸页不存在")

    candidates = db.scalars(
        select(RecognitionCandidate)
        .where(RecognitionCandidate.sheet_id == sheet_id)
        .order_by(RecognitionCandidate.field_name.asc(), RecognitionCandidate.confidence.desc())
    ).all()
    drawing_file = db.get(DrawingFile, sheet.file_id)
    is_dxf = drawing_file is not None and cad_sheet_service.is_dxf_file(drawing_file)
    candidates = filter_candidates_for_sheet(candidates)

    issue_service.clear_open_machine_issues(db, sheet.id)
    clear_unreviewed_field_values(db, sheet.id)

    by_field: dict[str, list[RecognitionCandidate]] = defaultdict(list)
    for candidate in candidates:
        by_field[candidate.field_name].append(candidate)

    selected_values: dict[str, FieldValue] = {}
    field_confidences: dict[str, float] = {}
    display_values: dict[str, str | None] = {}

    for field_name in CORE_FIELDS:
        reviewed = reviewed_field_value(db, sheet.id, field_name)
        if reviewed is not None:
            selected_values[field_name] = reviewed
            field_confidences[field_name] = reviewed.confidence
            display_values[field_name] = reviewed.display_value
            continue

        choice = choose_field_value(by_field.get(field_name, []))
        if choice is None:
            display_values[field_name] = None
            continue

        field_value = FieldValue(
            project_id=sheet.project_id,
            batch_id=sheet.batch_id,
            file_id=sheet.file_id,
            sheet_id=sheet.id,
            field_name=field_name,
            raw_value=choice.raw_value,
            normalized_value=choice.normalized_value,
            display_value=choice.display_value,
            final_source=choice.final_source,
            confidence=choice.confidence,
            is_reviewed=False,
        )
        db.add(field_value)
        db.flush()
        add_evidence(db, field_value, choice.evidence_ids, candidates)
        selected_values[field_name] = field_value
        field_confidences[field_name] = choice.confidence
        display_values[field_name] = choice.display_value

        if choice.conflict:
            conflict_values = sorted({value_key(candidate) for candidate in by_field[field_name] if value_key(candidate)})
            issue_service.add_conflict_issue(
                db, sheet, field_name, choice.conflict_sources, conflict_values
            )
        if choice.final_source in {"cad_text", "cad_mtext"} and choice.confidence < 70:
            issue_service.add_issue_for_sheet(db, sheet, "CAD_TEXT_LOW_CONFIDENCE")
        if field_name == "drawing_no" and choice.final_source in {"cad_text", "cad_mtext"}:
            selected_candidate = candidate_by_id(candidates, choice.evidence_ids[0] if choice.evidence_ids else None)
            if selected_candidate and is_suspect_drawing_no_candidate(selected_candidate.candidate_value, selected_candidate.source_type):
                issue_service.add_issue_for_sheet(db, sheet, "CAD_DRAWING_NO_SUSPECT")
        if field_name == "drawing_name" and choice.final_source in {"cad_text", "cad_mtext"}:
            selected_candidate = candidate_by_id(candidates, choice.evidence_ids[0] if choice.evidence_ids else None)
            if selected_candidate and is_suspect_drawing_name_candidate(selected_candidate.candidate_value, selected_candidate.source_type):
                issue_service.add_issue_for_sheet(db, sheet, "CAD_DRAWING_NAME_SUSPECT")
        if choice.final_source == "cad_layer":
            issue_service.add_issue_for_sheet(db, sheet, "CAD_ONLY_FROM_LAYER")
        if field_name in {"drawing_no", "drawing_name"} and choice.final_source == "cad_filename":
            issue_service.add_issue_for_sheet(db, sheet, "CAD_ONLY_FROM_FILENAME")
            issue_service.add_issue_for_sheet(db, sheet, "ONLY_FROM_FILENAME", severity="warning")
        if choice.final_source == "filename":
            issue_service.add_issue_for_sheet(
                db,
                sheet,
                "FIELD_ONLY_FROM_FILENAME",
                severity="info",
                message=f"{field_name} 仅来自文件名",
                suggestion="建议结合 PDF 文本或 OCR 结果复核。",
            )
            issue_service.add_issue_for_sheet(
                db,
                sheet,
                "ONLY_FROM_FILENAME",
                severity="warning",
                message=f"{field_name} 仅来自文件名",
                suggestion="建议结合 PDF 文本或 OCR 结果复核。",
            )
        if field_name in {"drawing_no", "drawing_name", "discipline"} and choice.final_source in {"filename", "cad_filename"}:
            issue_service.add_issue_for_sheet(
                db,
                sheet,
                "LOW_CONFIDENCE",
                severity="warning",
                message=f"{field_name} 主要依赖文件名，建议人工校核",
                suggestion="请结合 PDF 文本、OCR 或 CAD 块属性结果确认。",
            )
            issue_service.add_issue_for_sheet(
                db,
                sheet,
                "LOW_CONFIDENCE_NEED_REVIEW",
                severity="warning",
                message=f"{field_name} 主要依赖文件名，建议人工校核",
                suggestion="请结合 PDF 文本、OCR 或 CAD 块属性结果确认。",
            )
        if field_name == "discipline" and choice.confidence < 70:
            issue_service.add_issue_for_sheet(
                db,
                sheet,
                "DISCIPLINE_LOW_CONFIDENCE",
                severity="warning",
                message="专业候选置信度较低",
                suggestion="请结合图号前缀、图名和图层再确认专业。",
            )
        if field_name == "issue_date" and not parse_issue_date(choice.display_value):
            issue_service.add_issue_for_sheet(
                db,
                sheet,
                "ISSUE_DATE_INVALID",
                severity="warning",
                message=f"日期格式异常：{choice.display_value}",
                suggestion="请检查日期文本并修正为有效日期。",
            )

    issue_service.add_missing_field_issues(db, sheet, display_values)
    if is_dxf and cad_parse_empty(sheet):
        issue_service.add_issue_for_sheet(db, sheet, "CAD_PARSE_EMPTY_CONTENT")
    if is_dxf and cad_has_text_without_attribs(sheet):
        issue_service.add_issue_for_sheet(db, sheet, "CAD_BLOCK_ATTR_MISSING")
    score = scoring_service.score_sheet(field_confidences)
    if score < 50:
        issue_service.add_issue_for_sheet(db, sheet, "LOW_CONFIDENCE_NEED_REVIEW")

    db.flush()
    if display_values.get("drawing_no"):
        issue_service.add_duplicate_issues(db, sheet.project_id, display_values["drawing_no"])
        db.flush()

    issues = db.scalars(
        select(DrawingIssue)
        .where(DrawingIssue.sheet_id == sheet.id, DrawingIssue.status == "open")
        .order_by(DrawingIssue.severity.asc(), DrawingIssue.id.asc())
    ).all()
    severities = [issue.severity for issue in issues]
    trust_level = scoring_service.trust_level(score, display_values, severities)

    sync_sheet(sheet, display_values, score, trust_level, severities)
    update_batch_counts(db, sheet.batch_id)
    db.commit()
    db.refresh(sheet)

    values = list_field_values(db, sheet.id)
    issues = db.scalars(
        select(DrawingIssue)
        .where(DrawingIssue.sheet_id == sheet.id, DrawingIssue.status == "open")
        .order_by(DrawingIssue.id.asc())
    ).all()
    return SheetFusionResult(
        sheet_id=sheet.id,
        status=sheet.status,
        confidence_score=int(sheet.confidence_score or 0),
        trust_level=sheet.trust_level or "D",
        field_values=[FieldValueRead.model_validate(value) for value in values],
        issues=[DrawingIssueRead.model_validate(issue) for issue in issues],
    )


def fuse_fields_for_batch(db: Session, batch_id: int) -> BatchFusionResult:
    batch = db.get(ImportBatch, batch_id)
    if batch is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="导入批次不存在")
    sheets = db.scalars(
        select(DrawingSheet).where(DrawingSheet.batch_id == batch_id).order_by(DrawingSheet.id)
    ).all()
    items = []
    failed_count = 0
    for sheet in sheets:
        try:
            items.append(fuse_fields_for_sheet(db, sheet.id))
        except Exception:
            db.rollback()
            failed_count += 1
    return BatchFusionResult(
        batch_id=batch_id,
        total_count=len(sheets),
        success_count=len(items),
        failed_count=failed_count,
        issue_count=sum(len(item.issues) for item in items),
        items=items,
    )


def clear_unreviewed_field_values(db: Session, sheet_id: int) -> None:
    ids = db.scalars(
        select(FieldValue.id).where(FieldValue.sheet_id == sheet_id, FieldValue.is_reviewed.is_(False))
    ).all()
    if ids:
        db.execute(delete(FieldEvidence).where(FieldEvidence.field_value_id.in_(ids)))
        db.execute(delete(FieldValue).where(FieldValue.id.in_(ids)))


def filter_candidates_for_sheet(candidates: list[RecognitionCandidate]) -> list[RecognitionCandidate]:
    return [
        candidate
        for candidate in candidates
        if candidate.source_type != "cad_layer" or candidate.field_name == "discipline"
    ]


def candidate_by_id(candidates: list[RecognitionCandidate], candidate_id: int | None) -> RecognitionCandidate | None:
    if candidate_id is None:
        return None
    return next((candidate for candidate in candidates if candidate.id == candidate_id), None)


def cad_parse_empty(sheet: DrawingSheet) -> bool:
    output_path = cad_parse_output_path(settings.root_dir, sheet.project_id, sheet.id)
    if not output_path.exists():
        return False
    try:
        counts = read_cad_json(output_path).get("counts", {})
    except Exception:
        return False
    return (
        int(counts.get("text_count", 0) or 0) == 0
        and int(counts.get("mtext_count", 0) or 0) == 0
        and int(counts.get("attrib_count", 0) or 0) == 0
    )


def cad_has_text_without_attribs(sheet: DrawingSheet) -> bool:
    output_path = cad_parse_output_path(settings.root_dir, sheet.project_id, sheet.id)
    if not output_path.exists():
        return False
    try:
        counts = read_cad_json(output_path).get("counts", {})
    except Exception:
        return False
    return (
        int(counts.get("attrib_count", 0) or 0) == 0
        and (
            int(counts.get("text_count", 0) or 0) > 0
            or int(counts.get("mtext_count", 0) or 0) > 0
        )
    )


def reviewed_field_value(db: Session, sheet_id: int, field_name: str) -> FieldValue | None:
    return db.scalar(
        select(FieldValue).where(
            FieldValue.sheet_id == sheet_id,
            FieldValue.field_name == field_name,
            FieldValue.is_reviewed.is_(True),
        )
    )


def add_evidence(
    db: Session,
    field_value: FieldValue,
    evidence_ids: list[int],
    candidates: list[RecognitionCandidate],
) -> None:
    by_id = {candidate.id: candidate for candidate in candidates}
    for candidate_id in evidence_ids:
        candidate = by_id.get(candidate_id)
        if candidate is None:
            continue
        db.add(
            FieldEvidence(
                field_value_id=field_value.id,
                candidate_id=candidate.id,
                source_type=candidate.source_type,
                raw_text=candidate.raw_text,
                bbox=candidate.bbox,
                confidence=candidate.confidence,
            )
        )


def sync_sheet(
    sheet: DrawingSheet,
    values: dict[str, str | None],
    score: int,
    trust_level: str,
    severities: list[str],
) -> None:
    was_confirmed = sheet.review_status == "confirmed"
    sheet.drawing_no = values.get("drawing_no")
    sheet.drawing_name = values.get("drawing_name")
    sheet.discipline = values.get("discipline")
    sheet.version = values.get("version")
    issue_date = values.get("issue_date")
    sheet.issue_date = parse_issue_date(issue_date) if issue_date else None
    sheet.confidence_score = score
    sheet.trust_level = trust_level
    if was_confirmed:
        sheet.review_status = "confirmed"
        sheet.status = "confirmed"
        return
    sheet.review_status = "unreviewed"
    if not any(values.get(field) for field in ["drawing_no", "drawing_name", "discipline"]):
        sheet.status = "failed" if score < 20 else "need_review"
    elif "error" in severities or "warning" in severities:
        sheet.status = "need_review"
    else:
        sheet.status = "recognized"


def parse_issue_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def list_field_values(db: Session, sheet_id: int) -> list[FieldValue]:
    if db.get(DrawingSheet, sheet_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="图纸页不存在")
    return db.scalars(
        select(FieldValue).where(FieldValue.sheet_id == sheet_id).order_by(FieldValue.id.asc())
    ).all()


def list_field_evidence(db: Session, sheet_id: int) -> list[FieldEvidenceRead]:
    if db.get(DrawingSheet, sheet_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="图纸页不存在")
    rows = db.execute(
        select(FieldEvidence, FieldValue.field_name)
        .join(FieldValue, FieldValue.id == FieldEvidence.field_value_id)
        .where(FieldValue.sheet_id == sheet_id)
        .order_by(FieldValue.field_name.asc(), FieldEvidence.id.asc())
    ).all()
    return [
        FieldEvidenceRead.model_validate({**evidence.__dict__, "field_name": field_name})
        for evidence, field_name in rows
    ]


def update_batch_counts(db: Session, batch_id: int) -> None:
    batch = db.get(ImportBatch, batch_id)
    if batch is None:
        return
    batch.recognized_count = len(
        db.scalars(
            select(DrawingSheet).where(
                DrawingSheet.batch_id == batch_id,
                DrawingSheet.status.in_(["recognized", "need_review"]),
            )
        ).all()
    )
    batch.failed_count = len(
        db.scalars(
            select(DrawingSheet).where(DrawingSheet.batch_id == batch_id, DrawingSheet.status == "failed")
        ).all()
    )
