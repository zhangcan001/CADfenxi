"""INSERT 块统计服务层。

职责：
- 单 sheet 同步聚合（extract_block_stats_from_sheet）
- 批量异步聚合（start_block_stats_batch_job + threading worker）
- 查询：sheet / project 维度

模式与 cad_table_service 一致；复用 background_job_service 做进度与 409 防重。
"""
from __future__ import annotations

import json
import logging
import threading

from fastapi import HTTPException, status
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from backend.core.config import settings
from backend.core.database import SessionLocal
from backend.models.drawing_block_stat import DrawingBlockStat
from backend.models.drawing_file import DrawingFile
from backend.models.drawing_sheet import DrawingSheet
from backend.models.import_batch import ImportBatch
from backend.schemas.background_job import BackgroundJobStatus
from backend.schemas.drawing_block_stat import (
    BlockStatsSummary,
    DrawingBlockStatRecord,
    ExtractBlockStatsBatchRequest,
    ExtractBlockStatsRequest,
)
from backend.services import background_job_service
from recognizer.cad_engine.block_aggregator import aggregate_inserts
from recognizer.cad_engine.cad_json_writer import cad_parse_output_path, read_cad_json

logger = logging.getLogger(__name__)


EXTRACT_BLOCKS_JOB_TYPE = "extract_blocks"


def extract_block_stats_from_sheet(
    db: Session,
    sheet_id: int,
    *,
    payload: ExtractBlockStatsRequest | None = None,
) -> BlockStatsSummary:
    payload = payload or ExtractBlockStatsRequest()
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
    try:
        cad_json = read_cad_json(output_path)
    except (OSError, ValueError) as exc:
        logger.warning("read cad_json failed sheet_id=%s: %s", sheet.id, exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error_code": "CAD_PARSE_READ_FAILED", "message": str(exc)[:200]},
        ) from exc

    aggregated = aggregate_inserts(cad_json)

    if payload.force:
        db.execute(delete(DrawingBlockStat).where(DrawingBlockStat.sheet_id == sheet.id))
        db.flush()

    by_discipline: dict[str, int] = {}
    total = 0
    for row in aggregated:
        count = int(row.get("count", 0))
        total += count
        discipline = row.get("discipline_guess") or "未识别"
        by_discipline[discipline] = by_discipline.get(discipline, 0) + count
        sample_bbox = row.get("sample_bbox")
        attribs = row.get("attribs_summary") or {}
        record = DrawingBlockStat(
            project_id=sheet.project_id,
            batch_id=sheet.batch_id,
            file_id=sheet.file_id,
            sheet_id=sheet.id,
            block_name=row["block_name"][:100],
            layer_name=(row.get("layer_name") or "")[:100] or None,
            discipline_guess=row.get("discipline_guess"),
            count=count,
            sample_bbox_json=json.dumps(sample_bbox) if sample_bbox else None,
            attribs_summary_json=json.dumps(attribs, ensure_ascii=False) if attribs else None,
        )
        db.add(record)
    db.commit()

    return BlockStatsSummary(
        sheet_id=sheet.id,
        total_block_count=total,
        distinct_blocks=len(aggregated),
        by_discipline=by_discipline,
    )


def start_block_stats_batch_job(
    db: Session, batch_id: int, payload: ExtractBlockStatsBatchRequest
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
        job_type=EXTRACT_BLOCKS_JOB_TYPE,
        scope_type="batch",
        scope_id=batch_id,
        total=total,
        payload=payload_dict,
    )
    threading.Thread(
        target=_run_block_stats_worker,
        args=(job.id, batch_id, payload_dict),
        daemon=True,
        name=f"extract-blocks-{batch_id}-job-{job.id}",
    ).start()
    logger.info(
        "Started extract-blocks job batch_id=%s job_id=%s sheets=%s",
        batch_id,
        job.id,
        total,
    )
    return background_job_service.to_status(job)


def _run_block_stats_worker(job_id: int, batch_id: int, payload_dict: dict) -> None:
    session: Session = SessionLocal()
    try:
        payload = ExtractBlockStatsBatchRequest(**payload_dict)
        sheet_payload = ExtractBlockStatsRequest(force=payload.force)
        sheets = _eligible_sheets(session, batch_id)
        total = len(sheets)
        processed_ok = 0
        processed_fail = 0
        block_total = 0
        for index, sheet_id in enumerate(sheets, start=1):
            background_job_service.update_progress(
                session,
                job_id,
                processed=index - 1,
                current_step=f"sheet {index}/{total}",
                message=f"块统计 {index}/{total}",
            )
            try:
                summary = extract_block_stats_from_sheet(
                    session, sheet_id, payload=sheet_payload
                )
                processed_ok += 1
                block_total += summary.total_block_count
            except HTTPException as exc:
                detail = exc.detail if isinstance(exc.detail, dict) else {"message": str(exc.detail)}
                logger.warning(
                    "extract_blocks sheet failed sheet_id=%s: %s",
                    sheet_id,
                    detail.get("message"),
                )
                processed_fail += 1
                if not payload.continue_on_error:
                    background_job_service.mark_failed(
                        session, job_id, message=str(detail.get("message", "块统计失败"))[:500]
                    )
                    return
            except Exception as exc:  # noqa: BLE001
                logger.exception("extract_blocks worker sheet failure sheet_id=%s", sheet_id)
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
                "total_block_count": block_total,
            },
        )
    except HTTPException as exc:
        detail = exc.detail if isinstance(exc.detail, dict) else {"message": str(exc.detail)}
        logger.exception("extract-blocks worker HTTPException job_id=%s", job_id)
        background_job_service.mark_failed(
            session, job_id, message=str(detail.get("message", exc.detail))[:500]
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception("extract-blocks worker top-level failure job_id=%s", job_id)
        background_job_service.mark_failed(session, job_id, message=str(exc)[:500] or "未知错误")
    finally:
        session.close()


def get_block_stats_job(db: Session, batch_id: int) -> BackgroundJobStatus | None:
    job = background_job_service.find_active(
        db, EXTRACT_BLOCKS_JOB_TYPE, "batch", batch_id
    ) or background_job_service.find_latest(
        db, EXTRACT_BLOCKS_JOB_TYPE, "batch", batch_id
    )
    return background_job_service.to_status(job) if job else None


def list_block_stats_for_sheet(db: Session, sheet_id: int) -> list[DrawingBlockStatRecord]:
    rows = db.scalars(
        select(DrawingBlockStat)
        .where(DrawingBlockStat.sheet_id == sheet_id)
        .order_by(DrawingBlockStat.count.desc(), DrawingBlockStat.id.asc())
    ).all()
    return [_to_record(row) for row in rows]


def list_block_stats_for_project(
    db: Session, project_id: int, *, discipline: str | None = None
) -> list[DrawingBlockStatRecord]:
    stmt = select(DrawingBlockStat).where(DrawingBlockStat.project_id == project_id)
    if discipline:
        stmt = stmt.where(DrawingBlockStat.discipline_guess == discipline)
    stmt = stmt.order_by(
        DrawingBlockStat.sheet_id.asc(),
        DrawingBlockStat.count.desc(),
        DrawingBlockStat.id.asc(),
    )
    rows = db.scalars(stmt).all()
    return [_to_record(row) for row in rows]


def _to_record(row: DrawingBlockStat) -> DrawingBlockStatRecord:
    return DrawingBlockStatRecord(
        id=row.id,
        project_id=row.project_id,
        batch_id=row.batch_id,
        file_id=row.file_id,
        sheet_id=row.sheet_id,
        block_name=row.block_name,
        layer_name=row.layer_name,
        discipline_guess=row.discipline_guess,
        count=row.count,
        sample_bbox=_load_json_bbox(row.sample_bbox_json),
        attribs_summary=_load_json_attribs(row.attribs_summary_json),
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


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


def _load_json_attribs(value: str | None) -> dict[str, list[str]]:
    if not value:
        return {}
    try:
        data = json.loads(value)
    except json.JSONDecodeError:
        return {}
    if not isinstance(data, dict):
        return {}
    out: dict[str, list[str]] = {}
    for key, val in data.items():
        if isinstance(val, list):
            out[str(key)] = [str(v) for v in val]
    return out


def _eligible_sheets(db: Session, batch_id: int) -> list[int]:
    rows = db.execute(
        select(DrawingSheet.id)
        .join(DrawingFile, DrawingFile.id == DrawingSheet.file_id)
        .where(DrawingSheet.batch_id == batch_id)
        .where(DrawingFile.parse_status == "success")
        .order_by(DrawingSheet.id.asc())
    ).all()
    return [row[0] for row in rows]
