"""INSERT 块统计 API：单 sheet + 批量异步 + 查询。"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from backend.core.database import get_db
from backend.schemas.background_job import BackgroundJobStatus
from backend.schemas.drawing_block_stat import (
    BlockStatsSummary,
    DrawingBlockStatRecord,
    ExtractBlockStatsBatchRequest,
    ExtractBlockStatsRequest,
)
from backend.services import block_stats_service

router = APIRouter(prefix="/api", tags=["block_stats"])


@router.post("/sheets/{sheet_id}/extract-blocks", response_model=BlockStatsSummary)
def extract_blocks(
    sheet_id: int,
    payload: ExtractBlockStatsRequest | None = None,
    db: Session = Depends(get_db),
) -> BlockStatsSummary:
    return block_stats_service.extract_block_stats_from_sheet(db, sheet_id, payload=payload)


@router.post("/imports/{batch_id}/extract-blocks", response_model=BackgroundJobStatus)
def extract_blocks_batch(
    batch_id: int,
    payload: ExtractBlockStatsBatchRequest | None = None,
    db: Session = Depends(get_db),
) -> BackgroundJobStatus:
    return block_stats_service.start_block_stats_batch_job(
        db, batch_id, payload or ExtractBlockStatsBatchRequest()
    )


@router.get(
    "/imports/{batch_id}/extract-blocks/job",
    response_model=BackgroundJobStatus | None,
)
def get_block_stats_job(
    batch_id: int,
    db: Session = Depends(get_db),
) -> BackgroundJobStatus | None:
    return block_stats_service.get_block_stats_job(db, batch_id)


@router.get("/sheets/{sheet_id}/block-stats", response_model=list[DrawingBlockStatRecord])
def list_sheet_block_stats(
    sheet_id: int,
    db: Session = Depends(get_db),
) -> list[DrawingBlockStatRecord]:
    return block_stats_service.list_block_stats_for_sheet(db, sheet_id)


@router.get("/projects/{project_id}/block-stats", response_model=list[DrawingBlockStatRecord])
def list_project_block_stats(
    project_id: int,
    discipline: str | None = Query(default=None, description="按推断专业筛选"),
    db: Session = Depends(get_db),
) -> list[DrawingBlockStatRecord]:
    return block_stats_service.list_block_stats_for_project(db, project_id, discipline=discipline)
