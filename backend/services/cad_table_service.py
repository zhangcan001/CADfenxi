"""DXF 表格抽取服务层。

职责：
- 单 sheet 同步抽取（extract_tables_from_sheet）
- 批量异步抽取（start_extract_tables_batch_job + threading worker）
- 查询：sheet/project 维度

复用 background_job_service 做进度与 409 防重；模式参照 cad_pipeline_service。
"""
from __future__ import annotations

import json
import logging
import threading
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from backend.core.config import settings
from backend.core.database import SessionLocal
from backend.models.drawing_file import DrawingFile
from backend.models.drawing_sheet import DrawingSheet
from backend.models.drawing_table import DrawingTable
from backend.models.import_batch import ImportBatch
from backend.schemas.background_job import BackgroundJobStatus
from backend.schemas.drawing_table import (
    DrawingTableRecord,
    ExtractTablesBatchRequest,
    ExtractTablesRequest,
    ExtractTablesSummary,
)
from backend.services import background_job_service
from recognizer.cad_engine.cad_json_writer import cad_parse_output_path, read_cad_json
from recognizer.cad_engine.dxf_loader import DxfLoadError, load_dxf_document
from recognizer.cad_engine.table_classifier import classify_table_kind
from recognizer.cad_engine.table_extractor import (
    extract_acad_tables,
    extract_text_cluster_tables,
)
from recognizer.cad_engine.title_area import find_title_block_bbox

logger = logging.getLogger(__name__)


EXTRACT_TABLES_JOB_TYPE = "extract_tables"


def extract_tables_from_sheet(
    db: Session,
    sheet_id: int,
    *,
    payload: ExtractTablesRequest | None = None,
) -> ExtractTablesSummary:
    payload = payload or ExtractTablesRequest()

    sheet = db.get(DrawingSheet, sheet_id)
    if sheet is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error_code": "SHEET_NOT_FOUND", "message": "图纸页不存在。"},
        )
    drawing_file = db.get(DrawingFile, sheet.file_id)
    if drawing_file is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error_code": "FILE_NOT_FOUND", "message": "图纸文件不存在。"},
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
    try:
        cad_json = read_cad_json(output_path)
    except (OSError, ValueError) as exc:
        logger.warning("read cad_json failed sheet_id=%s: %s", sheet.id, exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error_code": "CAD_PARSE_READ_FAILED", "message": str(exc)[:200]},
        ) from exc

    acad_tables: list[dict] = []
    if payload.include_acad_table:
        acad_tables = _safe_extract_acad_tables(drawing_file)

    cluster_tables: list[dict] = []
    if payload.include_text_cluster:
        inserts: list[dict] = []
        for space in cad_json.get("spaces", []):
            inserts.extend(space.get("inserts", []) or [])
        title_bbox = find_title_block_bbox(inserts)
        exclude_bbox = list(title_bbox) if title_bbox else None
        cluster_tables = extract_text_cluster_tables(cad_json, exclude_bbox=exclude_bbox)

    combined = acad_tables + cluster_tables

    if payload.force:
        db.execute(delete(DrawingTable).where(DrawingTable.sheet_id == sheet.id))
        db.flush()

    by_kind: dict[str, int] = {}
    for idx, raw in enumerate(combined):
        header: list[str] = raw.get("header", []) or []
        rows: list[list[str]] = raw.get("rows", []) or []
        kind = classify_table_kind(header)
        by_kind[kind] = by_kind.get(kind, 0) + 1
        record = DrawingTable(
            project_id=sheet.project_id,
            batch_id=sheet.batch_id,
            file_id=sheet.file_id,
            sheet_id=sheet.id,
            table_index=idx,
            extraction_method=raw.get("extraction_method", "text_cluster"),
            table_kind=kind,
            layer_name=raw.get("layer") or None,
            header_json=json.dumps(header, ensure_ascii=False),
            rows_json=json.dumps(rows, ensure_ascii=False),
            row_count=int(raw.get("row_count", len(rows))),
            col_count=int(raw.get("col_count", len(header))),
            source_bbox_json=json.dumps(raw.get("bbox")) if raw.get("bbox") else None,
            warnings_json=json.dumps(raw.get("warnings", []), ensure_ascii=False)
            if raw.get("warnings")
            else None,
        )
        db.add(record)
    db.commit()

    return ExtractTablesSummary(
        sheet_id=sheet.id,
        acad_table_count=len(acad_tables),
        text_cluster_count=len(cluster_tables),
        total_count=len(combined),
        by_kind=by_kind,
    )


def _safe_extract_acad_tables(drawing_file: DrawingFile) -> list[dict]:
    """打开 DXF 跑 ACAD_TABLE；失败只记录 warning。"""
    source_rel = (
        drawing_file.converted_file_path
        if drawing_file.source_format == "dwg" and drawing_file.converted_file_path
        else drawing_file.storage_path
    )
    if not source_rel:
        return []
    source_path = settings.root_dir / source_rel
    if not source_path.exists():
        logger.debug("ACAD_TABLE 源文件不存在 file_id=%s path=%s", drawing_file.id, source_path)
        return []
    try:
        load_result = load_dxf_document(str(source_path))
    except DxfLoadError as exc:
        logger.warning("ACAD_TABLE 加载 DXF 失败 file_id=%s: %s", drawing_file.id, exc.message)
        return []
    except Exception as exc:  # noqa: BLE001 — ezdxf 错误谱很宽
        logger.warning("ACAD_TABLE 加载异常 file_id=%s: %s", drawing_file.id, exc)
        return []
    try:
        return extract_acad_tables(load_result.document)
    except Exception as exc:  # noqa: BLE001
        logger.warning("ACAD_TABLE 抽取异常 file_id=%s: %s", drawing_file.id, exc)
        return []


def start_extract_tables_batch_job(
    db: Session, batch_id: int, payload: ExtractTablesBatchRequest
) -> BackgroundJobStatus:
    batch = db.get(ImportBatch, batch_id)
    if batch is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error_code": "IMPORT_BATCH_NOT_FOUND", "message": "导入批次不存在。"},
        )
    sheets = _eligible_sheets(db, batch_id)
    total = len(sheets)
    payload_dict = payload.model_dump(mode="json")
    job = background_job_service.create_job(
        db,
        job_type=EXTRACT_TABLES_JOB_TYPE,
        scope_type="batch",
        scope_id=batch_id,
        total=total,
        payload=payload_dict,
    )
    threading.Thread(
        target=_run_extract_tables_worker,
        args=(job.id, batch_id, payload_dict),
        daemon=True,
        name=f"extract-tables-{batch_id}-job-{job.id}",
    ).start()
    logger.info(
        "Started extract-tables job batch_id=%s job_id=%s sheets=%s",
        batch_id,
        job.id,
        total,
    )
    return background_job_service.to_status(job)


def _run_extract_tables_worker(job_id: int, batch_id: int, payload_dict: dict) -> None:
    session: Session = SessionLocal()
    try:
        payload = ExtractTablesBatchRequest(**payload_dict)
        sheet_payload = ExtractTablesRequest(
            include_acad_table=payload.include_acad_table,
            include_text_cluster=payload.include_text_cluster,
            force=payload.force,
        )
        sheets = _eligible_sheets(session, batch_id)
        total = len(sheets)
        processed_ok = 0
        processed_fail = 0
        kind_totals: dict[str, int] = {}
        for index, sheet_id in enumerate(sheets, start=1):
            background_job_service.update_progress(
                session,
                job_id,
                processed=index - 1,
                current_step=f"sheet {index}/{total}",
                message=f"抽取图纸 {index}/{total}",
            )
            try:
                summary = extract_tables_from_sheet(session, sheet_id, payload=sheet_payload)
                processed_ok += 1
                for kind, count in (summary.by_kind or {}).items():
                    kind_totals[kind] = kind_totals.get(kind, 0) + count
            except HTTPException as exc:
                detail = exc.detail if isinstance(exc.detail, dict) else {"message": str(exc.detail)}
                logger.warning(
                    "extract_tables sheet failed sheet_id=%s: %s",
                    sheet_id,
                    detail.get("message"),
                )
                processed_fail += 1
                if not payload.continue_on_error:
                    background_job_service.mark_failed(
                        session, job_id, message=str(detail.get("message", "抽取失败"))[:500]
                    )
                    return
            except Exception as exc:  # noqa: BLE001
                logger.exception("extract_tables worker sheet failure sheet_id=%s", sheet_id)
                processed_fail += 1
                if not payload.continue_on_error:
                    background_job_service.mark_failed(
                        session, job_id, message=str(exc)[:500] or "未知错误"
                    )
                    return
        background_job_service.mark_completed(
            session,
            job_id,
            message=f"完成 {processed_ok}/{total}，失败 {processed_fail}",
            result_summary={
                "batch_id": batch_id,
                "total_sheets": total,
                "success_count": processed_ok,
                "failed_count": processed_fail,
                "by_kind": kind_totals,
            },
        )
    except HTTPException as exc:
        detail = exc.detail if isinstance(exc.detail, dict) else {"message": str(exc.detail)}
        logger.exception("extract-tables worker HTTPException job_id=%s", job_id)
        background_job_service.mark_failed(
            session, job_id, message=str(detail.get("message", exc.detail))[:500]
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception("extract-tables worker top-level failure job_id=%s", job_id)
        background_job_service.mark_failed(session, job_id, message=str(exc)[:500] or "未知错误")
    finally:
        session.close()


def get_extract_tables_job(db: Session, batch_id: int) -> BackgroundJobStatus | None:
    job = background_job_service.find_active(
        db, EXTRACT_TABLES_JOB_TYPE, "batch", batch_id
    ) or background_job_service.find_latest(
        db, EXTRACT_TABLES_JOB_TYPE, "batch", batch_id
    )
    return background_job_service.to_status(job) if job else None


def list_tables_for_sheet(db: Session, sheet_id: int) -> list[DrawingTableRecord]:
    rows = db.scalars(
        select(DrawingTable)
        .where(DrawingTable.sheet_id == sheet_id)
        .order_by(DrawingTable.table_index.asc(), DrawingTable.id.asc())
    ).all()
    return [_to_record(row) for row in rows]


def list_tables_for_project(
    db: Session, project_id: int, *, kind: str | None = None
) -> list[DrawingTableRecord]:
    stmt = select(DrawingTable).where(DrawingTable.project_id == project_id)
    if kind:
        stmt = stmt.where(DrawingTable.table_kind == kind)
    stmt = stmt.order_by(
        DrawingTable.sheet_id.asc(),
        DrawingTable.table_index.asc(),
        DrawingTable.id.asc(),
    )
    rows = db.scalars(stmt).all()
    return [_to_record(row) for row in rows]


def _to_record(row: DrawingTable) -> DrawingTableRecord:
    return DrawingTableRecord(
        id=row.id,
        project_id=row.project_id,
        batch_id=row.batch_id,
        file_id=row.file_id,
        sheet_id=row.sheet_id,
        table_index=row.table_index,
        extraction_method=row.extraction_method,  # type: ignore[arg-type]
        table_kind=row.table_kind,  # type: ignore[arg-type]
        layer_name=row.layer_name,
        header=_load_json_list(row.header_json),
        rows=_load_json_rows(row.rows_json),
        row_count=row.row_count,
        col_count=row.col_count,
        source_bbox=_load_json_bbox(row.source_bbox_json),
        warnings=_load_json_list(row.warnings_json) if row.warnings_json else [],
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _load_json_list(value: str | None) -> list[str]:
    if not value:
        return []
    try:
        data = json.loads(value)
    except json.JSONDecodeError:
        return []
    return [str(item) for item in data] if isinstance(data, list) else []


def _load_json_rows(value: str | None) -> list[list[str]]:
    if not value:
        return []
    try:
        data = json.loads(value)
    except json.JSONDecodeError:
        return []
    if not isinstance(data, list):
        return []
    out: list[list[str]] = []
    for row in data:
        if isinstance(row, list):
            out.append([str(cell) for cell in row])
    return out


def _load_json_bbox(value: str | None) -> list[float] | None:
    if not value:
        return None
    try:
        data = json.loads(value)
    except json.JSONDecodeError:
        return None
    if not isinstance(data, list) or len(data) < 4:
        return None
    try:
        return [float(x) for x in data[:4]]
    except (TypeError, ValueError):
        return None


def _eligible_sheets(db: Session, batch_id: int) -> list[int]:
    """batch 内 parse 成功的 sheet ids（按 id 升序）。"""
    rows = db.execute(
        select(DrawingSheet.id)
        .join(DrawingFile, DrawingFile.id == DrawingSheet.file_id)
        .where(DrawingSheet.batch_id == batch_id)
        .where(DrawingFile.parse_status == "success")
        .order_by(DrawingSheet.id.asc())
    ).all()
    return [row[0] for row in rows]


def get_kind_summary(rows: list[DrawingTableRecord]) -> dict[str, Any]:
    summary: dict[str, int] = {}
    for row in rows:
        summary[row.table_kind] = summary.get(row.table_kind, 0) + 1
    return summary
