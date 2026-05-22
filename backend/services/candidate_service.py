import json
import logging
from pathlib import Path

from fastapi import HTTPException, status
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from backend.core.config import settings
from backend.models.drawing_file import DrawingFile
from backend.models.drawing_sheet import DrawingSheet
from backend.models.import_batch import ImportBatch
from backend.models.recognition_candidate import RecognitionCandidate
from backend.models.recognition_run import RecognitionRun
from backend.schemas.recognition_candidate import (
    BatchCandidateGenerateResult,
    CandidateGenerateResult,
    RecognitionCandidateRead,
)
from backend.services import cad_candidate_service, cad_sheet_service
from recognizer.filename_parser.parser import parse_filename
from recognizer.rules.discipline_rules import generate_discipline_candidates
from recognizer.text_parser.parser import parse_text

logger = logging.getLogger(__name__)

MACHINE_SOURCES = [
    "filename",
    "pdf_text",
    "title_ocr",
    "rule",
    "cad_text",
    "cad_mtext",
    "cad_block_attr",
    "cad_layer",
    "cad_filename",
]


def generate_candidates_for_sheet(db: Session, sheet_id: int) -> CandidateGenerateResult:
    sheet = db.get(DrawingSheet, sheet_id)
    if sheet is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="图纸页不存在")
    drawing_file = db.get(DrawingFile, sheet.file_id)
    if drawing_file is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="图纸文件不存在")

    clear_machine_candidates(db, sheet_id, commit=False)

    if cad_sheet_service.is_dxf_file(drawing_file):
        raw_candidates = cad_candidate_service.load_cad_candidates(db, sheet, drawing_file)
    else:
        raw_candidates = load_pdf_candidates(sheet, drawing_file)

    saved = []
    seen = set()
    for item in raw_candidates:
        key = (
            item["field_name"],
            item["candidate_value"],
            item.get("normalized_value"),
            item["source_type"],
        )
        if key in seen:
            continue
        seen.add(key)
        run_id = latest_run_id(db, sheet.id, item["source_type"])
        candidate = RecognitionCandidate(
            project_id=sheet.project_id,
            batch_id=sheet.batch_id,
            file_id=sheet.file_id,
            sheet_id=sheet.id,
            field_name=item["field_name"],
            candidate_value=item["candidate_value"],
            normalized_value=item.get("normalized_value"),
            source_type=item["source_type"],
            confidence=float(item["confidence"]),
            raw_text=item["raw_text"],
            bbox=item.get("bbox"),
            run_id=run_id,
            parser_name=item["parser_name"],
            parser_version=item["parser_version"],
        )
        db.add(candidate)
        saved.append(candidate)

    db.commit()
    for candidate in saved:
        db.refresh(candidate)

    reads = [RecognitionCandidateRead.model_validate(candidate) for candidate in saved]
    return CandidateGenerateResult(
        sheet_id=sheet.id,
        candidate_count=len(reads),
        candidates=reads,
    )


def generate_candidates_for_batch(db: Session, batch_id: int) -> BatchCandidateGenerateResult:
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
            items.append(generate_candidates_for_sheet(db, sheet.id))
        except HTTPException as exc:
            db.rollback()
            failed_count += 1
            logger.warning("Candidate generation HTTP error sheet_id=%s detail=%s", sheet.id, exc.detail)
        except Exception:
            db.rollback()
            failed_count += 1
            logger.exception("Candidate generation failed sheet_id=%s", sheet.id)

    return BatchCandidateGenerateResult(
        batch_id=batch_id,
        total_count=len(sheets),
        success_count=len(items),
        failed_count=failed_count,
        candidate_count=sum(item.candidate_count for item in items),
        items=items,
    )


def load_pdf_candidates(sheet: DrawingSheet, drawing_file: DrawingFile) -> list[dict]:
    raw_candidates: list[dict] = []
    raw_candidates.extend(parse_filename(drawing_file.original_name))

    pdf_text = load_result_text(pdf_text_path(sheet))
    if pdf_text is not None:
        raw_candidates.extend(parse_text(pdf_text, "pdf_text"))

    ocr_payload = load_json(ocr_path(sheet))
    ocr_text = ocr_payload.get("text", "") if ocr_payload else None
    if ocr_text is not None:
        raw_candidates.extend(parse_text(ocr_text, "title_ocr"))

    raw_candidates.extend(
        generate_discipline_candidates([drawing_file.original_name, pdf_text or "", ocr_text or ""])
    )
    return raw_candidates


def list_candidates(
    db: Session,
    sheet_id: int,
    field_name: str | None = None,
) -> list[RecognitionCandidateRead]:
    if db.get(DrawingSheet, sheet_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="图纸页不存在")
    query = select(RecognitionCandidate).where(RecognitionCandidate.sheet_id == sheet_id)
    if field_name:
        query = query.where(RecognitionCandidate.field_name == field_name)
    candidates = db.scalars(
        query.order_by(
            RecognitionCandidate.field_name.asc(),
            RecognitionCandidate.confidence.desc(),
            RecognitionCandidate.id.asc(),
        )
    ).all()
    return [RecognitionCandidateRead.model_validate(candidate) for candidate in candidates]


def clear_machine_candidates(db: Session, sheet_id: int, commit: bool = True) -> int:
    result = db.execute(
        delete(RecognitionCandidate).where(
            RecognitionCandidate.sheet_id == sheet_id,
            RecognitionCandidate.source_type.in_(MACHINE_SOURCES),
        )
    )
    if commit:
        db.commit()
    return result.rowcount or 0


def pdf_text_path(sheet: DrawingSheet) -> Path:
    return settings.projects_dir / f"project_{sheet.project_id}" / "text" / f"sheet_{sheet.id}_pdf_text.json"


def ocr_path(sheet: DrawingSheet) -> Path:
    return settings.projects_dir / f"project_{sheet.project_id}" / "ocr" / f"sheet_{sheet.id}_title_ocr.json"


def load_json(path: Path) -> dict | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def load_result_text(path: Path) -> str | None:
    payload = load_json(path)
    if payload is None:
        return None
    return payload.get("text", "")


def latest_run_id(db: Session, sheet_id: int, source_type: str) -> int | None:
    run_type = {
        "pdf_text": "pdf_text",
        "title_ocr": "title_ocr",
        "cad_text": "cad_parse",
        "cad_mtext": "cad_parse",
        "cad_block_attr": "cad_parse",
        "cad_layer": "cad_parse",
        "cad_filename": "cad_parse",
    }.get(source_type)
    if not run_type:
        return None
    return db.scalar(
        select(RecognitionRun.id)
        .where(RecognitionRun.sheet_id == sheet_id, RecognitionRun.run_type == run_type)
        .order_by(RecognitionRun.id.desc())
    )
