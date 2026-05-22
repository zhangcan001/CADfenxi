import json
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.core.config import settings
from backend.models.drawing_sheet import DrawingSheet
from backend.models.import_batch import ImportBatch
from backend.schemas.recognition_run import BatchRecognitionResult, RecognitionRunResult
from backend.services import issue_service, recognition_run_service
from recognizer.ocr_engine.mock_ocr import MockOcrEngine


def ocr_title_for_sheet(db: Session, sheet_id: int) -> RecognitionRunResult:
    sheet = db.get(DrawingSheet, sheet_id)
    if sheet is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="图纸页不存在")
    if not sheet.title_crop_path:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error_code": "TITLE_CROP_NOT_FOUND", "message": "标题栏裁剪图不存在"},
        )

    image_path = settings.root_dir / sheet.title_crop_path
    if not image_path.exists():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error_code": "TITLE_CROP_FILE_MISSING", "message": "标题栏裁剪图文件不存在"},
        )

    engine = MockOcrEngine()
    started_at = datetime.now(timezone.utc)
    try:
        result = engine.recognize(str(image_path))
        output_path = save_ocr_result(sheet, result.text, result.items, engine.engine_name)
        error_code = "OCR_TEXT_EMPTY" if not result.text.strip() else None
        if error_code:
            issue_service.add_issue_for_sheet(db, sheet, error_code)
        recognition_run_service.create_run(
            db,
            project_id=sheet.project_id,
            batch_id=sheet.batch_id,
            file_id=sheet.file_id,
            sheet_id=sheet.id,
            run_type="title_ocr",
            engine_name=result.engine_name,
            engine_version=result.engine_version,
            status="success",
            output_path=output_path,
            started_at=started_at,
            error_code=error_code,
            error_message="OCR 未识别到文字" if error_code else None,
        )
        return RecognitionRunResult(
            sheet_id=sheet.id,
            status="success",
            run_type="title_ocr",
            output_path=output_path,
            text_length=len(result.text),
            error_code=error_code,
            error_message="OCR 未识别到文字" if error_code else None,
        )
    except Exception as exc:
        recognition_run_service.create_run(
            db,
            project_id=sheet.project_id,
            batch_id=sheet.batch_id,
            file_id=sheet.file_id,
            sheet_id=sheet.id,
            run_type="title_ocr",
            engine_name=engine.engine_name,
            engine_version=engine.engine_version,
            status="failed",
            started_at=started_at,
            error_code="OCR_FAILED",
            error_message=str(exc)[:500],
        )
        return RecognitionRunResult(
            sheet_id=sheet.id,
            status="failed",
            run_type="title_ocr",
            output_path=None,
            text_length=0,
            error_code="OCR_FAILED",
            error_message=str(exc)[:500],
        )


def ocr_titles_for_batch(db: Session, batch_id: int) -> BatchRecognitionResult:
    batch = db.get(ImportBatch, batch_id)
    if batch is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="导入批次不存在")
    sheets = db.scalars(
        select(DrawingSheet).where(DrawingSheet.batch_id == batch_id).order_by(DrawingSheet.id)
    ).all()

    items = []
    for sheet in sheets:
        try:
            items.append(ocr_title_for_sheet(db, sheet.id))
        except HTTPException as exc:
            detail = exc.detail if isinstance(exc.detail, dict) else {}
            items.append(
                RecognitionRunResult(
                    sheet_id=sheet.id,
                    status="failed",
                    run_type="title_ocr",
                    output_path=None,
                    text_length=0,
                    error_code=detail.get("error_code", "OCR_FAILED"),
                    error_message=detail.get("message", str(exc.detail)),
                )
            )

    success_count = sum(1 for item in items if item.status == "success")
    return BatchRecognitionResult(
        batch_id=batch_id,
        total_count=len(items),
        success_count=success_count,
        failed_count=len(items) - success_count,
        items=items,
    )


def save_ocr_result(sheet: DrawingSheet, text: str, items: list, engine_name: str) -> str:
    ocr_dir = settings.projects_dir / f"project_{sheet.project_id}" / "ocr"
    ocr_dir.mkdir(parents=True, exist_ok=True)
    output = ocr_dir / f"sheet_{sheet.id}_title_ocr.json"
    payload = {
        "sheet_id": sheet.id,
        "page_no": sheet.page_no,
        "source": "title_ocr",
        "text": text,
        "items": [
            {"text": item.text, "confidence": item.confidence, "bbox": item.bbox}
            for item in items
        ],
        "engine": engine_name,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return str(output.relative_to(settings.root_dir))
