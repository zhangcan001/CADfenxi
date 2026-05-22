import json
import logging
from datetime import UTC, datetime

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.core.config import settings
from backend.models.drawing_file import DrawingFile
from backend.models.drawing_sheet import DrawingSheet
from backend.models.import_batch import ImportBatch
from backend.schemas.recognition_run import BatchRecognitionResult, RecognitionRunResult
from backend.services import issue_service, recognition_run_service
from recognizer.pdf_engine.text_extractor import extract_page_text

logger = logging.getLogger(__name__)


def extract_text_for_sheet(db: Session, sheet_id: int) -> RecognitionRunResult:
    sheet = db.get(DrawingSheet, sheet_id)
    if sheet is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="图纸页不存在")
    drawing_file = db.get(DrawingFile, sheet.file_id)
    if drawing_file is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="PDF 文件不存在")

    started_at = datetime.now(UTC)
    source_path = settings.root_dir / drawing_file.storage_path
    try:
        result = extract_page_text(source_path, sheet.page_no)
        output_path = save_text_result(sheet, result.text, result.blocks)
        error_code = "PDF_TEXT_EMPTY" if not result.text.strip() else None
        if error_code:
            issue_service.add_issue_for_sheet(db, sheet, error_code)
        recognition_run_service.create_run(
            db,
            project_id=sheet.project_id,
            batch_id=sheet.batch_id,
            file_id=sheet.file_id,
            sheet_id=sheet.id,
            run_type="pdf_text",
            engine_name=result.engine_name,
            engine_version=result.engine_version,
            status="success",
            output_path=output_path,
            started_at=started_at,
            error_code=error_code,
            error_message="PDF 页面无可提取文本" if error_code else None,
        )
        return RecognitionRunResult(
            sheet_id=sheet.id,
            status="success",
            run_type="pdf_text",
            output_path=output_path,
            text_length=len(result.text),
            error_code=error_code,
            error_message="PDF 页面无可提取文本" if error_code else None,
        )
    except IndexError:
        return failed_result(db, sheet, started_at, "PDF_PAGE_NOT_FOUND", "PDF 页码不存在")
    except (OSError, RuntimeError, ValueError) as exc:
        logger.warning("PDF text extract failed sheet_id=%s: %s", sheet.id, exc)
        return failed_result(db, sheet, started_at, "PDF_OPEN_FAILED", str(exc)[:500])


def extract_text_for_batch(db: Session, batch_id: int) -> BatchRecognitionResult:
    batch = db.get(ImportBatch, batch_id)
    if batch is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="导入批次不存在")
    sheets = db.scalars(
        select(DrawingSheet).where(DrawingSheet.batch_id == batch_id).order_by(DrawingSheet.id)
    ).all()
    items = [extract_text_for_sheet(db, sheet.id) for sheet in sheets]
    success_count = sum(1 for item in items if item.status == "success")
    return BatchRecognitionResult(
        batch_id=batch_id,
        total_count=len(items),
        success_count=success_count,
        failed_count=len(items) - success_count,
        items=items,
    )


def save_text_result(sheet: DrawingSheet, text: str, blocks: list[dict]) -> str:
    text_dir = settings.projects_dir / f"project_{sheet.project_id}" / "text"
    text_dir.mkdir(parents=True, exist_ok=True)
    output = text_dir / f"sheet_{sheet.id}_pdf_text.json"
    payload = {
        "sheet_id": sheet.id,
        "page_no": sheet.page_no,
        "source": "pdf_text",
        "text": text,
        "blocks": blocks,
        "engine": "pymupdf",
        "created_at": datetime.now(UTC).isoformat(),
    }
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return str(output.relative_to(settings.root_dir))


def failed_result(
    db: Session,
    sheet: DrawingSheet,
    started_at: datetime,
    error_code: str,
    error_message: str,
) -> RecognitionRunResult:
    recognition_run_service.create_run(
        db,
        project_id=sheet.project_id,
        batch_id=sheet.batch_id,
        file_id=sheet.file_id,
        sheet_id=sheet.id,
        run_type="pdf_text",
        engine_name="pymupdf",
        engine_version="unknown",
        status="failed",
        started_at=started_at,
        error_code=error_code,
        error_message=error_message,
    )
    return RecognitionRunResult(
        sheet_id=sheet.id,
        status="failed",
        run_type="pdf_text",
        output_path=None,
        text_length=0,
        error_code=error_code,
        error_message=error_message,
    )
