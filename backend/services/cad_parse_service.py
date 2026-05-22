import logging
from datetime import UTC, datetime
from pathlib import Path

import ezdxf
from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.core.config import settings
from backend.models.drawing_file import DrawingFile
from backend.models.drawing_sheet import DrawingSheet
from backend.models.import_batch import ImportBatch
from backend.schemas.cad import BatchCadParseResult, CadParseResult, CadParseSummary
from backend.services import cad_sheet_service, recognition_run_service
from recognizer.cad_engine.cad_json_writer import (
    cad_parse_output_path,
    read_cad_json,
    write_cad_json,
)
from recognizer.cad_engine.dxf_loader import DxfLoadError, load_dxf_document
from recognizer.cad_engine.entity_extractor import extract_cad_entities

logger = logging.getLogger(__name__)


def parse_dxf_file(db: Session, file_id: int) -> CadParseResult:
    drawing_file = db.get(DrawingFile, file_id)
    if drawing_file is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error_code": "FILE_NOT_FOUND", "message": "图纸文件不存在。"},
        )
    if drawing_file.source_format == "dwg" and drawing_file.convert_status != "success":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error_code": "DWG_NOT_CONVERTED",
                "message": "该 DWG 尚未转换为 DXF，请先执行 DWG 转 DXF。",
            },
        )
    if not cad_sheet_service.is_dxf_file(drawing_file):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error_code": "UNSUPPORTED_CAD_FORMAT",
                "message": "该接口仅支持 DXF 文件。",
            },
        )

    prepare_result = cad_sheet_service.prepare_dxf_sheet(db, file_id)
    drawing_file = db.get(DrawingFile, file_id)
    sheet = db.get(DrawingSheet, prepare_result.sheet_id)
    if drawing_file is None or sheet is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error_code": "FILE_NOT_FOUND", "message": "图纸文件不存在。"},
        )

    return parse_prepared_dxf(db, drawing_file, sheet)


def parse_dxf_batch(db: Session, batch_id: int) -> BatchCadParseResult:
    batch = db.get(ImportBatch, batch_id)
    if batch is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error_code": "IMPORT_BATCH_NOT_FOUND", "message": "导入批次不存在。"},
        )
    dxf_files = db.scalars(
        select(DrawingFile)
        .where(
            DrawingFile.batch_id == batch_id,
            (
                (DrawingFile.source_format == "dxf")
                | (DrawingFile.file_ext == ".dxf")
                | (
                    (DrawingFile.source_format == "dwg")
                    & (DrawingFile.convert_status == "success")
                    & (DrawingFile.converted_file_path.is_not(None))
                )
            ),
        )
        .order_by(DrawingFile.id.asc())
    ).all()

    items: list[CadParseResult] = []
    success_count = 0
    failed_count = 0
    for drawing_file in dxf_files:
        try:
            result = parse_dxf_file(db, drawing_file.id)
        except HTTPException as exc:
            db.rollback()
            detail = exc.detail if isinstance(exc.detail, dict) else {}
            result = CadParseResult(
                file_id=drawing_file.id,
                status="failed",
                error_code=detail.get("error_code", "DXF_PARSE_FAILED"),
                error_message=detail.get("message", "DXF 解析失败。"),
            )
        if result.status == "success":
            success_count += 1
        else:
            failed_count += 1
        items.append(result)

    total_files = db.scalar(
        select(func.count()).select_from(DrawingFile).where(DrawingFile.batch_id == batch_id)
    )
    skipped_count = max((total_files or 0) - len(dxf_files), 0)
    return BatchCadParseResult(
        batch_id=batch_id,
        total_count=len(dxf_files),
        success_count=success_count,
        failed_count=failed_count,
        skipped_count=skipped_count,
        items=items,
    )


def parse_prepared_dxf(
    db: Session,
    drawing_file: DrawingFile,
    sheet: DrawingSheet,
) -> CadParseResult:
    started_at = datetime.now(UTC)
    source_path = settings.root_dir / (
        drawing_file.converted_file_path
        if drawing_file.source_format == "dwg" and drawing_file.converted_file_path
        else drawing_file.storage_path
    )
    output_path = cad_parse_output_path(settings.root_dir, drawing_file.project_id, sheet.id)
    try:
        load_result = load_dxf_document(str(source_path))
        cad_json = extract_cad_entities(
            load_result.document,
            project_id=drawing_file.project_id,
            file_id=drawing_file.id,
            sheet_id=sheet.id,
            source_file=drawing_file.storage_path,
            warnings=load_result.warnings,
        )
        warnings = list(cad_json.get("warnings", []))
        counts = cad_json["counts"]
        if counts["text_count"] + counts["mtext_count"] + counts["attrib_count"] == 0:
            warnings.append("DXF_EMPTY_CONTENT")
            cad_json["warnings"] = warnings
        relative_output_path = write_output_json(cad_json, output_path)

        drawing_file.parse_status = "success"
        drawing_file.parse_error_code = None
        drawing_file.parse_error_message = None
        drawing_file.status = "cad_parsed"
        sheet.status = "cad_parsed"
        sheet.error_code = None
        sheet.error_message = None
        db.flush()
        run = recognition_run_service.create_run(
            db,
            project_id=drawing_file.project_id,
            batch_id=drawing_file.batch_id,
            file_id=drawing_file.id,
            sheet_id=sheet.id,
            run_type="cad_parse",
            engine_name="ezdxf",
            engine_version=ezdxf.__version__,
            status="success",
            started_at=started_at,
            output_path=relative_output_path,
        )
        return CadParseResult(
            file_id=drawing_file.id,
            sheet_id=sheet.id,
            status="success",
            run_id=run.id,
            output_path=relative_output_path,
            counts=counts,
            warnings=warnings,
        )
    except DxfLoadError as exc:
        return failed_parse_result(db, drawing_file, sheet, started_at, exc.error_code, exc.message)
    except (OSError, RuntimeError, ValueError, ezdxf.DXFError) as exc:
        logger.exception("DXF parse failed file_id=%s sheet_id=%s", drawing_file.id, sheet.id)
        return failed_parse_result(
            db, drawing_file, sheet, started_at, "DXF_PARSE_FAILED", str(exc)[:500]
        )


def get_cad_parse_summary(db: Session, sheet_id: int) -> CadParseSummary:
    sheet = db.get(DrawingSheet, sheet_id)
    if sheet is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error_code": "SHEET_NOT_FOUND", "message": "图纸页不存在。"},
        )
    output_path = cad_parse_output_path(settings.root_dir, sheet.project_id, sheet.id)
    if not output_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error_code": "CAD_PARSE_NOT_FOUND",
                "message": "未找到 CAD 解析结果，请先执行 DXF 解析。",
            },
        )
    data = read_cad_json(output_path)
    modelspace = next(
        (space for space in data.get("spaces", []) if space.get("space") == "modelspace"),
        {},
    )
    sample_attribs = []
    for insert in modelspace.get("inserts", []):
        for attrib in insert.get("attribs", []):
            sample_attribs.append(attrib)
            if len(sample_attribs) >= 20:
                break
        if len(sample_attribs) >= 20:
            break
    return CadParseSummary(
        sheet_id=sheet.id,
        file_id=sheet.file_id,
        output_path=relative_to_root(output_path),
        counts=data.get("counts", {}),
        sample_texts=modelspace.get("texts", [])[:20],
        sample_mtexts=modelspace.get("mtexts", [])[:20],
        sample_attribs=sample_attribs,
        layers=data.get("layers", [])[:200],
        warnings=data.get("warnings", []),
    )


def failed_parse_result(
    db: Session,
    drawing_file: DrawingFile,
    sheet: DrawingSheet,
    started_at: datetime,
    error_code: str,
    error_message: str,
) -> CadParseResult:
    drawing_file.parse_status = "failed"
    drawing_file.parse_error_code = error_code
    drawing_file.parse_error_message = error_message
    sheet.status = "failed"
    sheet.error_code = error_code
    sheet.error_message = error_message
    db.flush()
    run = recognition_run_service.create_run(
        db,
        project_id=drawing_file.project_id,
        batch_id=drawing_file.batch_id,
        file_id=drawing_file.id,
        sheet_id=sheet.id,
        run_type="cad_parse",
        engine_name="ezdxf",
        engine_version=ezdxf.__version__,
        status="failed",
        started_at=started_at,
        error_code=error_code,
        error_message=error_message,
    )
    return CadParseResult(
        file_id=drawing_file.id,
        sheet_id=sheet.id,
        status="failed",
        run_id=run.id,
        error_code=error_code,
        error_message=error_message,
    )


def write_output_json(cad_json: dict, output_path: Path) -> str:
    write_cad_json(cad_json, output_path)
    return relative_to_root(output_path)


def relative_to_root(path: Path) -> str:
    return path.relative_to(settings.root_dir).as_posix()
