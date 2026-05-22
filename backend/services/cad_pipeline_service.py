import logging
from collections.abc import Callable
from datetime import UTC, datetime

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.core.config import settings
from backend.models.drawing_file import DrawingFile
from backend.models.drawing_issue import DrawingIssue
from backend.models.drawing_sheet import DrawingSheet
from backend.models.field_value import FieldValue
from backend.models.import_batch import ImportBatch
from backend.models.recognition_candidate import RecognitionCandidate
from backend.schemas.cad_pipeline import (
    CadPipelineError,
    CadPipelineItem,
    CadPipelineRequest,
    CadPipelineResponse,
    CadPipelineStatus,
    CadPipelineStepName,
    CadPipelineStepResult,
    CadPipelineSummary,
)
from backend.schemas.cad import CadPreviewBatchRequest
from backend.services import (
    cad_converter_service,
    cad_parse_service,
    cad_preview_service,
    cad_sheet_service,
    candidate_service,
    fusion_service,
)
from recognizer.cad_engine.cad_json_writer import cad_parse_output_path, read_cad_json

logger = logging.getLogger(__name__)


StepHandler = Callable[
    [Session, int, list[DrawingFile], CadPipelineRequest],
    tuple[CadPipelineStepResult, bool],
]


def run_cad_pipeline(db: Session, batch_id: int, payload: CadPipelineRequest) -> CadPipelineResponse:
    started_at = now()
    batch = db.get(ImportBatch, batch_id)
    if batch is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error_code": "IMPORT_BATCH_NOT_FOUND", "message": "导入批次不存在。"},
        )

    files = batch_files(db, batch_id)
    if not files:
        return CadPipelineResponse(
            batch_id=batch_id,
            status="skipped",
            summary=build_summary(files, [], [], started_at, now()),
            steps=[],
            errors=[],
        )

    steps: list[CadPipelineStepResult] = []
    errors: list[CadPipelineError] = []
    pipeline_status: CadPipelineStatus = "success"
    had_work = False

    for step_name in payload.steps:
        result, executed = run_step(db, batch_id, files, step_name, payload)
        steps.append(result)
        errors.extend(result.errors)
        had_work = had_work or executed
        pipeline_status = combine_status(pipeline_status, result.status)
        if result.status == "failed" and not payload.continue_on_error:
            break

    if not had_work and not errors:
        pipeline_status = "skipped"
    elif pipeline_status != "failed" and errors:
        pipeline_status = "completed_with_errors"

    finished_at = now()
    return CadPipelineResponse(
        batch_id=batch_id,
        status=pipeline_status,
        summary=build_summary(files, steps, errors, started_at, finished_at),
        steps=steps,
        errors=errors,
    )


def run_step(
    db: Session,
    batch_id: int,
    files: list[DrawingFile],
    step_name: CadPipelineStepName,
    payload: CadPipelineRequest,
) -> tuple[CadPipelineStepResult, bool]:
    handler = STEP_HANDLERS.get(step_name)
    if handler is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error_code": "CAD_PIPELINE_STEP_UNKNOWN", "message": f"未知的流水线步骤：{step_name}"},
        )
    return handler(db, batch_id, files, payload)


def _convert_handler(db, batch_id, files, payload):
    return run_convert_step(db, files, payload)


def _prepare_handler(db, batch_id, files, payload):
    return run_prepare_step(db, files, payload)


def _parse_handler(db, batch_id, files, payload):
    return run_parse_step(db, files, payload)


def _candidate_handler(db, batch_id, files, payload):
    return run_candidate_step(db, batch_id, payload)


def _fusion_handler(db, batch_id, files, payload):
    return run_fusion_step(db, batch_id, payload)


def _cad_preview_handler(db, batch_id, files, payload):
    return run_cad_preview_step(db, batch_id, payload)


STEP_HANDLERS: dict[CadPipelineStepName, StepHandler] = {
    "convert_dwg": _convert_handler,
    "prepare_dxf_sheet": _prepare_handler,
    "parse_dxf": _parse_handler,
    "generate_candidates": _candidate_handler,
    "fuse_fields": _fusion_handler,
    "generate_cad_preview": _cad_preview_handler,
}


def run_convert_step(
    db: Session,
    files: list[DrawingFile],
    payload: CadPipelineRequest,
) -> tuple[CadPipelineStepResult, bool]:
    started_at = now()
    dwg_files = [file for file in files if is_dwg_source(file)]
    items: list[CadPipelineItem] = []
    errors: list[CadPipelineError] = []
    success_count = 0
    failed_count = 0
    skipped_count = 0
    executed = False

    if not dwg_files:
        return make_step("convert_dwg", "skipped", started_at, items, errors), False

    if payload.skip_completed and all(is_converted(file) for file in dwg_files):
        items = [item_for_file(file, "skipped") for file in dwg_files]
        return make_step("convert_dwg", "skipped", started_at, items, errors, skipped_count=len(items)), False

    try:
        cad_converter_service.active_converter_setting(db)
    except HTTPException as exc:
        detail = http_detail(exc, "CONVERTER_NOT_CONFIGURED", "未配置转换工具。")
        item = CadPipelineItem(status="failed", error_code=detail["error_code"], message=detail["message"])
        error = error_for_item(None, None, None, "convert_dwg", item)
        return make_step("convert_dwg", "failed", started_at, [item], [error], failed_count=1), False

    for drawing_file in dwg_files:
        if payload.skip_completed and is_converted(drawing_file):
            skipped_count += 1
            items.append(item_for_file(drawing_file, "skipped"))
            continue

        executed = True
        try:
            result = cad_converter_service.convert_dwg_file(db, drawing_file.id)
            if result.status == "success":
                success_count += 1
            else:
                failed_count += 1
                error = CadPipelineError(
                    file_id=drawing_file.id,
                    sheet_id=None,
                    file_name=drawing_file.original_name,
                    step="convert_dwg",
                    error_code=result.error_code or "DWG_CONVERT_FAILED",
                    message=result.error_message or "DWG 转 DXF 失败。",
                )
                errors.append(error)
            items.append(
                item_for_file(
                    drawing_file,
                    result.status,
                    error_code=result.error_code,
                    message=result.error_message,
                )
            )
        except HTTPException as exc:
            db.rollback()
            failed_count += 1
            detail = http_detail(exc, "DWG_CONVERT_FAILED", "DWG 转 DXF 失败。")
            item = item_for_file(
                drawing_file,
                "failed",
                error_code=detail["error_code"],
                message=detail["message"],
            )
            items.append(item)
            errors.append(error_for_item(drawing_file.id, None, drawing_file.original_name, "convert_dwg", item))

        if failed_count and not payload.continue_on_error:
            break

    status_value = step_status(success_count, failed_count, skipped_count, len(dwg_files), executed, payload.continue_on_error)
    return make_step(
        "convert_dwg",
        status_value,
        started_at,
        items,
        errors,
        success_count,
        failed_count,
        skipped_count,
    ), executed


def run_prepare_step(
    db: Session,
    files: list[DrawingFile],
    payload: CadPipelineRequest,
) -> tuple[CadPipelineStepResult, bool]:
    started_at = now()
    dxf_files = [file for file in files if cad_sheet_service.is_dxf_file(file)]
    items: list[CadPipelineItem] = []
    errors: list[CadPipelineError] = []
    success_count = 0
    failed_count = 0
    skipped_count = 0
    executed = False

    for drawing_file in dxf_files:
        existing = cad_sheet_service.get_existing_dxf_sheet(db, drawing_file.id)
        if existing is not None:
            skipped_count += 1
            items.append(item_for_file(drawing_file, "skipped", sheet_id=existing.id))
            continue

        executed = True
        try:
            result = cad_sheet_service.prepare_dxf_sheet(db, drawing_file.id)
            if result.created:
                success_count += 1
            else:
                skipped_count += 1
            items.append(
                item_for_file(
                    drawing_file,
                    "success" if result.created else "skipped",
                    sheet_id=result.sheet_id,
                )
            )
        except HTTPException as exc:
            db.rollback()
            failed_count += 1
            detail = http_detail(exc, "DXF_SHEET_PREPARE_FAILED", "DXF 图纸页准备失败。")
            item = item_for_file(
                drawing_file,
                "failed",
                error_code=detail["error_code"],
                message=detail["message"],
            )
            items.append(item)
            errors.append(error_for_item(drawing_file.id, None, drawing_file.original_name, "prepare_dxf_sheet", item))

        if failed_count and not payload.continue_on_error:
            break

    status_value = step_status(success_count, failed_count, skipped_count, len(dxf_files), executed, payload.continue_on_error)
    return make_step(
        "prepare_dxf_sheet",
        status_value,
        started_at,
        items,
        errors,
        success_count,
        failed_count,
        skipped_count,
    ), executed


def run_parse_step(
    db: Session,
    files: list[DrawingFile],
    payload: CadPipelineRequest,
) -> tuple[CadPipelineStepResult, bool]:
    started_at = now()
    items: list[CadPipelineItem] = []
    errors: list[CadPipelineError] = []
    success_count = 0
    failed_count = 0
    skipped_count = 0
    executed = False

    processable: list[tuple[DrawingFile, DrawingSheet]] = []
    for drawing_file in files:
        if not cad_sheet_service.is_dxf_file(drawing_file):
            continue
        sheet = sheet_for_file(db, drawing_file.id)
        if sheet is None:
            continue
        processable.append((drawing_file, sheet))

    for drawing_file, sheet in processable:
        if payload.skip_completed and drawing_file.parse_status == "success":
            skipped_count += 1
            items.append(item_for_file(drawing_file, "skipped", sheet_id=sheet.id))
            continue

        executed = True
        try:
            result = cad_parse_service.parse_prepared_dxf(db, drawing_file, sheet)
            if result.status == "success":
                success_count += 1
            else:
                failed_count += 1
                errors.append(
                    CadPipelineError(
                        file_id=drawing_file.id,
                        sheet_id=sheet.id,
                        file_name=drawing_file.original_name,
                        step="parse_dxf",
                        error_code=result.error_code or "DXF_PARSE_FAILED",
                        message=result.error_message or "DXF 解析失败。",
                    )
                )
            items.append(
                item_for_file(
                    drawing_file,
                    result.status,
                    sheet_id=sheet.id,
                    error_code=result.error_code,
                    message=result.error_message,
                )
            )
        except HTTPException as exc:
            db.rollback()
            failed_count += 1
            detail = http_detail(exc, "DXF_PARSE_FAILED", "DXF 解析失败。")
            item = item_for_file(
                drawing_file,
                "failed",
                sheet_id=sheet.id,
                error_code=detail["error_code"],
                message=detail["message"],
            )
            items.append(item)
            errors.append(error_for_item(drawing_file.id, sheet.id, drawing_file.original_name, "parse_dxf", item))
        except Exception as exc:
            logger.exception("Pipeline parse_dxf failed file_id=%s sheet_id=%s", drawing_file.id, sheet.id)
            db.rollback()
            failed_count += 1
            item = item_for_file(
                drawing_file,
                "failed",
                sheet_id=sheet.id,
                error_code="DXF_PARSE_FAILED",
                message=str(exc)[:500] or "DXF 解析失败。",
            )
            items.append(item)
            errors.append(error_for_item(drawing_file.id, sheet.id, drawing_file.original_name, "parse_dxf", item))

        if failed_count and not payload.continue_on_error:
            break

    status_value = step_status(success_count, failed_count, skipped_count, len(processable), executed, payload.continue_on_error)
    return make_step(
        "parse_dxf",
        status_value,
        started_at,
        items,
        errors,
        success_count,
        failed_count,
        skipped_count,
    ), executed


def run_candidate_step(
    db: Session,
    batch_id: int,
    payload: CadPipelineRequest,
) -> tuple[CadPipelineStepResult, bool]:
    started_at = now()
    sheets = dxf_sheets_for_batch(db, batch_id)
    items: list[CadPipelineItem] = []
    errors: list[CadPipelineError] = []
    success_count = 0
    failed_count = 0
    skipped_count = 0
    executed = False

    for sheet, drawing_file in sheets:
        if payload.skip_completed and has_candidates(db, sheet.id):
            skipped_count += 1
            items.append(item_for_file(drawing_file, "skipped", sheet_id=sheet.id))
            continue
        if drawing_file.parse_status != "success":
            skipped_count += 1
            items.append(item_for_file(drawing_file, "skipped", sheet_id=sheet.id, message="DXF 尚未解析。"))
            continue

        executed = True
        try:
            result = candidate_service.generate_candidates_for_sheet(db, sheet.id)
            if result.candidate_count <= 0 or cad_parse_empty(sheet):
                failed_count += 1
                item = item_for_file(
                    drawing_file,
                    "failed",
                    sheet_id=sheet.id,
                    error_code="NO_CANDIDATES",
                    message="未生成候选值。",
                )
                items.append(item)
                errors.append(error_for_item(drawing_file.id, sheet.id, drawing_file.original_name, "generate_candidates", item))
            else:
                success_count += 1
                items.append(item_for_file(drawing_file, "success", sheet_id=sheet.id))
        except HTTPException as exc:
            db.rollback()
            failed_count += 1
            detail = http_detail(exc, "DXF_CANDIDATE_EMPTY", "候选值生成失败。")
            item = item_for_file(
                drawing_file,
                "failed",
                sheet_id=sheet.id,
                error_code=detail["error_code"],
                message=detail["message"],
            )
            items.append(item)
            errors.append(error_for_item(drawing_file.id, sheet.id, drawing_file.original_name, "generate_candidates", item))
        except Exception as exc:
            logger.exception("Pipeline generate_candidates failed file_id=%s sheet_id=%s", drawing_file.id, sheet.id)
            db.rollback()
            failed_count += 1
            item = item_for_file(
                drawing_file,
                "failed",
                sheet_id=sheet.id,
                error_code="DXF_CANDIDATE_EMPTY",
                message=str(exc)[:500] or "候选值生成失败。",
            )
            items.append(item)
            errors.append(error_for_item(drawing_file.id, sheet.id, drawing_file.original_name, "generate_candidates", item))

        if failed_count and not payload.continue_on_error:
            break

    status_value = step_status(success_count, failed_count, skipped_count, len(sheets), executed, payload.continue_on_error)
    return make_step(
        "generate_candidates",
        status_value,
        started_at,
        items,
        errors,
        success_count,
        failed_count,
        skipped_count,
    ), executed


def run_fusion_step(
    db: Session,
    batch_id: int,
    payload: CadPipelineRequest,
) -> tuple[CadPipelineStepResult, bool]:
    started_at = now()
    sheets = dxf_sheets_for_batch(db, batch_id)
    items: list[CadPipelineItem] = []
    errors: list[CadPipelineError] = []
    success_count = 0
    failed_count = 0
    skipped_count = 0
    executed = False

    for sheet, drawing_file in sheets:
        if payload.skip_completed and has_field_values(db, sheet.id):
            skipped_count += 1
            items.append(item_for_file(drawing_file, "skipped", sheet_id=sheet.id))
            continue
        if not has_candidates(db, sheet.id):
            skipped_count += 1
            items.append(item_for_file(drawing_file, "skipped", sheet_id=sheet.id, message="尚未生成候选值。"))
            continue

        executed = True
        try:
            fusion_service.fuse_fields_for_sheet(db, sheet.id)
            success_count += 1
            items.append(item_for_file(drawing_file, "success", sheet_id=sheet.id))
        except HTTPException as exc:
            db.rollback()
            failed_count += 1
            detail = http_detail(exc, "FIELD_FUSION_FAILED", "推荐字段融合失败。")
            item = item_for_file(
                drawing_file,
                "failed",
                sheet_id=sheet.id,
                error_code=detail["error_code"],
                message=detail["message"],
            )
            items.append(item)
            errors.append(error_for_item(drawing_file.id, sheet.id, drawing_file.original_name, "fuse_fields", item))
        except Exception as exc:
            logger.exception("Pipeline fuse_fields failed file_id=%s sheet_id=%s", drawing_file.id, sheet.id)
            db.rollback()
            failed_count += 1
            item = item_for_file(
                drawing_file,
                "failed",
                sheet_id=sheet.id,
                error_code="FIELD_FUSION_FAILED",
                message=str(exc)[:500] or "推荐字段融合失败。",
            )
            items.append(item)
            errors.append(error_for_item(drawing_file.id, sheet.id, drawing_file.original_name, "fuse_fields", item))

        if failed_count and not payload.continue_on_error:
            break

    status_value = step_status(success_count, failed_count, skipped_count, len(sheets), executed, payload.continue_on_error)
    return make_step(
        "fuse_fields",
        status_value,
        started_at,
        items,
        errors,
        success_count,
        failed_count,
        skipped_count,
    ), executed


def run_cad_preview_step(
    db: Session,
    batch_id: int,
    payload: CadPipelineRequest,
) -> tuple[CadPipelineStepResult, bool]:
    started_at = now()
    batch_result = cad_preview_service.generate_cad_preview_for_batch(
        db,
        batch_id,
        CadPreviewBatchRequest(
            skip_completed=payload.skip_completed,
            force=False,
            continue_on_error=payload.continue_on_error,
        ),
    )
    items = [
        CadPipelineItem(
            file_id=result.file_id,
            sheet_id=result.sheet_id,
            file_name=result.file_name,
            status=result.status,
            error_code=result.error_code,
            message=result.error_message,
        )
        for result in batch_result.items
    ]
    errors = [
        CadPipelineError(
            file_id=next((item.file_id for item in items if item.sheet_id == error.sheet_id), None),
            sheet_id=error.sheet_id,
            file_name=error.file_name,
            step="generate_cad_preview",
            error_code=error.error_code,
            message=error.message,
        )
        for error in batch_result.errors
    ]
    executed = batch_result.success_count > 0 or batch_result.failed_count > 0
    status_value = batch_result.status
    return make_step(
        "generate_cad_preview",
        status_value,
        started_at,
        items,
        errors,
        batch_result.success_count,
        batch_result.failed_count,
        batch_result.skipped_count,
        batch_result.warning_count,
    ), executed


def make_step(
    step: CadPipelineStepName,
    status_value: CadPipelineStatus,
    started_at: datetime,
    items: list[CadPipelineItem],
    errors: list[CadPipelineError],
    success_count: int = 0,
    failed_count: int = 0,
    skipped_count: int = 0,
    warning_count: int = 0,
) -> CadPipelineStepResult:
    return CadPipelineStepResult(
        step=step,
        status=status_value,
        duration_seconds=duration(started_at, now()),
        success_count=success_count,
        failed_count=failed_count,
        skipped_count=skipped_count,
        warning_count=warning_count,
        items=items,
        errors=errors,
    )


def build_summary(
    files: list[DrawingFile],
    steps: list[CadPipelineStepResult],
    errors: list[CadPipelineError],
    started_at: datetime,
    finished_at: datetime,
) -> CadPipelineSummary:
    summary = CadPipelineSummary(
        duration_seconds=duration(started_at, finished_at),
        start_time=started_at,
        finish_time=finished_at,
        total_files=len(files),
        pdf_files=sum(1 for file in files if file.source_format == "pdf"),
        dwg_files=sum(1 for file in files if is_dwg_source(file)),
        dxf_files=sum(1 for file in files if file.source_format == "dxf" or file.file_ext.lower() == ".dxf"),
        skipped_count=sum(step.skipped_count for step in steps),
        error_count=len(errors),
        warning_count=sum(1 for step in steps if step.status == "completed_with_errors"),
    )
    for step in steps:
        if step.step == "convert_dwg":
            summary.converted_success = step.success_count
            summary.converted_failed = step.failed_count
        elif step.step == "prepare_dxf_sheet":
            summary.sheet_prepared_success = step.success_count
            summary.sheet_prepared_failed = step.failed_count
        elif step.step == "parse_dxf":
            summary.parse_success = step.success_count
            summary.parse_failed = step.failed_count
        elif step.step == "generate_candidates":
            summary.candidate_success = step.success_count
            summary.candidate_failed = step.failed_count
        elif step.step == "fuse_fields":
            summary.fusion_success = step.success_count
            summary.fusion_failed = step.failed_count
        elif step.step == "generate_cad_preview":
            summary.cad_preview_success = step.success_count
            summary.cad_preview_failed = step.failed_count
            summary.cad_preview_skipped = step.skipped_count
            summary.cad_preview_warning_count = step.warning_count
    return summary


def step_status(
    success_count: int,
    failed_count: int,
    skipped_count: int,
    total: int,
    executed: bool,
    continue_on_error: bool,
) -> CadPipelineStatus:
    if total == 0 or (not executed and skipped_count == total):
        return "skipped"
    if failed_count > 0:
        if continue_on_error:
            return "completed_with_errors"
        return "completed_with_errors" if success_count > 0 or skipped_count > 0 else "failed"
    return "success"


def combine_status(current: CadPipelineStatus, next_status: CadPipelineStatus) -> CadPipelineStatus:
    if current == "failed" or next_status == "failed":
        return "failed"
    if current == "completed_with_errors" or next_status == "completed_with_errors":
        return "completed_with_errors"
    if next_status == "skipped":
        return current
    if current == "skipped":
        return next_status
    return next_status if current == "success" else current


def item_for_file(
    drawing_file: DrawingFile,
    status_value: str,
    sheet_id: int | None = None,
    error_code: str | None = None,
    message: str | None = None,
) -> CadPipelineItem:
    return CadPipelineItem(
        file_id=drawing_file.id,
        sheet_id=sheet_id,
        file_name=drawing_file.original_name,
        status=status_value,
        error_code=error_code,
        message=message,
    )


def error_for_item(
    file_id: int | None,
    sheet_id: int | None,
    file_name: str | None,
    step: CadPipelineStepName,
    item: CadPipelineItem,
) -> CadPipelineError:
    return CadPipelineError(
        file_id=file_id,
        sheet_id=sheet_id,
        file_name=file_name,
        step=step,
        error_code=item.error_code or "CAD_PIPELINE_FAILED",
        message=item.message or "CAD 批量处理失败。",
    )


def http_detail(exc: HTTPException, default_code: str, default_message: str) -> dict[str, str]:
    detail = exc.detail if isinstance(exc.detail, dict) else {}
    return {
        "error_code": str(detail.get("error_code", default_code)),
        "message": str(detail.get("message", default_message)),
    }


def batch_files(db: Session, batch_id: int) -> list[DrawingFile]:
    return db.scalars(
        select(DrawingFile)
        .where(DrawingFile.batch_id == batch_id)
        .order_by(DrawingFile.id.asc())
    ).all()


def sheets_for_batch(db: Session, batch_id: int) -> list[DrawingSheet]:
    return db.scalars(
        select(DrawingSheet).where(DrawingSheet.batch_id == batch_id).order_by(DrawingSheet.id.asc())
    ).all()


def dxf_sheets_for_batch(db: Session, batch_id: int) -> list[tuple[DrawingSheet, DrawingFile]]:
    rows = db.execute(
        select(DrawingSheet, DrawingFile)
        .join(DrawingFile, DrawingFile.id == DrawingSheet.file_id)
        .where(DrawingSheet.batch_id == batch_id)
        .order_by(DrawingSheet.id.asc())
    ).all()
    return [(sheet, drawing_file) for sheet, drawing_file in rows if cad_sheet_service.is_dxf_file(drawing_file)]


def sheet_for_file(db: Session, file_id: int) -> DrawingSheet | None:
    return db.scalar(
        select(DrawingSheet).where(DrawingSheet.file_id == file_id).order_by(DrawingSheet.id.asc())
    )


def has_candidates(db: Session, sheet_id: int) -> bool:
    return db.scalar(select(RecognitionCandidate.id).where(RecognitionCandidate.sheet_id == sheet_id)) is not None


def has_field_values(db: Session, sheet_id: int) -> bool:
    return db.scalar(select(FieldValue.id).where(FieldValue.sheet_id == sheet_id)) is not None


def cad_parse_empty(sheet: DrawingSheet) -> bool:
    output_path = cad_parse_output_path(settings.root_dir, sheet.project_id, sheet.id)
    if not output_path.exists():
        return False
    try:
        counts = read_cad_json(output_path).get("counts", {})
    except (OSError, ValueError) as exc:
        logger.warning("Failed reading CAD parse output sheet_id=%s: %s", sheet.id, exc)
        return False
    return (
        int(counts.get("text_count", 0) or 0) == 0
        and int(counts.get("mtext_count", 0) or 0) == 0
        and int(counts.get("attrib_count", 0) or 0) == 0
    )


def open_issue_count(db: Session, sheet_id: int) -> int:
    return db.scalar(
        select(func.count())
        .select_from(DrawingIssue)
        .where(DrawingIssue.sheet_id == sheet_id, DrawingIssue.status == "open")
    ) or 0


def is_dwg_source(drawing_file: DrawingFile) -> bool:
    return drawing_file.source_format == "dwg" or drawing_file.file_ext.lower() == ".dwg"


def is_converted(drawing_file: DrawingFile) -> bool:
    return drawing_file.convert_status == "success" and bool(drawing_file.converted_file_path)


def now() -> datetime:
    return datetime.now(UTC)


def duration(started_at: datetime, finished_at: datetime) -> float:
    return round(max((finished_at - started_at).total_seconds(), 0), 3)
