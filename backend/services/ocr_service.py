import json
import logging
import threading
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeout
from datetime import UTC, datetime

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.core.config import settings
from backend.core.database import SessionLocal
from backend.models.drawing_sheet import DrawingSheet
from backend.models.import_batch import ImportBatch
from backend.models.recognition_run import RecognitionRun
from backend.schemas.recognition_run import (
    BatchRecognitionResult,
    OcrJobStatus,
    RecognitionRunResult,
)
from backend.services import issue_service, recognition_run_service
from recognizer.ocr_engine.factory import get_ocr_engine

logger = logging.getLogger(__name__)

OCR_PAGE_TIMEOUT_SECONDS = 60

_job_start_lock = threading.Lock()


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

    engine = get_ocr_engine()
    started_at = datetime.now(UTC)
    try:
        result = _recognize_with_timeout(engine, str(image_path))
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
    except (OSError, ValueError, RuntimeError) as exc:
        logger.exception("OCR failed sheet_id=%s", sheet.id)
        error_code = "OCR_TIMEOUT" if str(exc).startswith("OCR_TIMEOUT") else "OCR_FAILED"
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
            error_code=error_code,
            error_message=str(exc)[:500],
        )
        return RecognitionRunResult(
            sheet_id=sheet.id,
            status="failed",
            run_type="title_ocr",
            output_path=None,
            text_length=0,
            error_code=error_code,
            error_message=str(exc)[:500],
        )


def _recognize_with_timeout(engine, image_path: str):
    with ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(engine.recognize, image_path)
        try:
            return future.result(timeout=OCR_PAGE_TIMEOUT_SECONDS)
        except FuturesTimeout:
            future.cancel()
            raise RuntimeError(
                f"OCR_TIMEOUT: 单页 OCR 超过 {OCR_PAGE_TIMEOUT_SECONDS} 秒未返回"
            ) from None


def start_ocr_batch_job(db: Session, batch_id: int) -> OcrJobStatus:
    batch = db.get(ImportBatch, batch_id)
    if batch is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="导入批次不存在")

    sheets = db.scalars(
        select(DrawingSheet)
        .where(DrawingSheet.batch_id == batch_id)
        .where(DrawingSheet.title_crop_path.isnot(None))
        .order_by(DrawingSheet.id)
    ).all()
    total = len(sheets)
    if total == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error_code": "NO_SHEETS_TO_OCR", "message": "该批次下没有可识别的图纸页"},
        )

    with _job_start_lock:
        db.refresh(batch)
        if batch.ocr_job_status == "running":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={"error_code": "OCR_JOB_RUNNING", "message": "该批次正在执行 OCR 任务"},
            )
        batch.ocr_job_status = "running"
        batch.ocr_job_total = total
        batch.ocr_job_processed = 0
        batch.ocr_job_started_at = datetime.now(UTC)
        batch.ocr_job_finished_at = None
        batch.ocr_job_message = None
        db.commit()
        db.refresh(batch)

    threading.Thread(
        target=_run_ocr_batch_worker,
        args=(batch_id,),
        daemon=True,
        name=f"ocr-batch-{batch_id}",
    ).start()
    logger.info("Started OCR batch job batch_id=%s total=%s", batch_id, total)

    return _build_job_status(db, batch)


def _run_ocr_batch_worker(batch_id: int) -> None:
    session: Session = SessionLocal()
    try:
        batch = session.get(ImportBatch, batch_id)
        if batch is None:
            logger.error("OCR worker: batch %s vanished", batch_id)
            return
        sheets = session.scalars(
            select(DrawingSheet)
            .where(DrawingSheet.batch_id == batch_id)
            .where(DrawingSheet.title_crop_path.isnot(None))
            .order_by(DrawingSheet.id)
        ).all()

        for sheet in sheets:
            try:
                ocr_title_for_sheet(session, sheet.id)
            except HTTPException as exc:
                logger.warning("OCR worker skip sheet %s: %s", sheet.id, exc.detail)
            except Exception:
                logger.exception("OCR worker unexpected error sheet_id=%s", sheet.id)
            try:
                batch = session.get(ImportBatch, batch_id)
                if batch is not None:
                    batch.ocr_job_processed = (batch.ocr_job_processed or 0) + 1
                    session.commit()
            except Exception:
                logger.exception("OCR worker progress commit failed batch_id=%s", batch_id)
                session.rollback()

        try:
            batch = session.get(ImportBatch, batch_id)
            if batch is not None:
                batch.ocr_job_status = "completed"
                batch.ocr_job_finished_at = datetime.now(UTC)
                session.commit()
            logger.info("OCR batch job completed batch_id=%s", batch_id)
        except Exception as exc:
            logger.exception("OCR worker finalize failed batch_id=%s", batch_id)
            session.rollback()
            _mark_job_failed(session, batch_id, f"finalize failed: {exc}")
    except Exception as exc:
        logger.exception("OCR worker top-level failure batch_id=%s", batch_id)
        _mark_job_failed(session, batch_id, str(exc))
    finally:
        session.close()


def _mark_job_failed(session: Session, batch_id: int, message: str) -> None:
    try:
        batch = session.get(ImportBatch, batch_id)
        if batch is not None:
            batch.ocr_job_status = "failed"
            batch.ocr_job_finished_at = datetime.now(UTC)
            batch.ocr_job_message = message[:500]
            session.commit()
    except Exception:
        logger.exception("OCR worker mark-failed errored batch_id=%s", batch_id)
        session.rollback()


def reset_orphaned_ocr_jobs() -> None:
    """启动时把残留 running 状态标记为 failed（进程被强杀后的清理）。"""
    session: Session = SessionLocal()
    try:
        running = session.scalars(
            select(ImportBatch).where(ImportBatch.ocr_job_status == "running")
        ).all()
        for batch in running:
            batch.ocr_job_status = "failed"
            batch.ocr_job_finished_at = datetime.now(UTC)
            batch.ocr_job_message = "进程重启，任务被中断"
        if running:
            session.commit()
            logger.info("Reset %s orphaned OCR jobs to failed", len(running))
    except Exception:
        logger.exception("reset_orphaned_ocr_jobs failed")
        session.rollback()
    finally:
        session.close()


def get_ocr_batch_job(db: Session, batch_id: int) -> OcrJobStatus:
    batch = db.get(ImportBatch, batch_id)
    if batch is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="导入批次不存在")
    return _build_job_status(db, batch)


def _build_job_status(db: Session, batch: ImportBatch) -> OcrJobStatus:
    success_count = db.scalar(
        select(func.count())
        .select_from(RecognitionRun)
        .where(RecognitionRun.batch_id == batch.id)
        .where(RecognitionRun.run_type == "title_ocr")
        .where(RecognitionRun.status == "success")
    ) or 0
    failed_count = db.scalar(
        select(func.count())
        .select_from(RecognitionRun)
        .where(RecognitionRun.batch_id == batch.id)
        .where(RecognitionRun.run_type == "title_ocr")
        .where(RecognitionRun.status == "failed")
    ) or 0
    return OcrJobStatus(
        batch_id=batch.id,
        status=batch.ocr_job_status or "idle",
        total=batch.ocr_job_total or 0,
        processed=batch.ocr_job_processed or 0,
        success_count=int(success_count),
        failed_count=int(failed_count),
        started_at=batch.ocr_job_started_at,
        finished_at=batch.ocr_job_finished_at,
        message=batch.ocr_job_message,
    )


def ocr_titles_for_batch(db: Session, batch_id: int) -> BatchRecognitionResult:
    """同步版本：仅供测试与脚本直接调用，不再通过 HTTP 路由暴露。"""
    batch = db.get(ImportBatch, batch_id)
    if batch is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="导入批次不存在")
    sheets = db.scalars(
        select(DrawingSheet).where(DrawingSheet.batch_id == batch_id).order_by(DrawingSheet.id)
    ).all()

    items: list[RecognitionRunResult] = []
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
        "created_at": datetime.now(UTC).isoformat(),
    }
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return str(output.relative_to(settings.root_dir))
