"""DXF 表格抽取相关 API：单表 + 批量异步 + 查询。"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from backend.core.database import get_db
from backend.schemas.background_job import BackgroundJobStatus
from backend.schemas.drawing_table import (
    DrawingTableRecord,
    ExtractTablesBatchRequest,
    ExtractTablesRequest,
    ExtractTablesSummary,
)
from backend.services import cad_table_service

router = APIRouter(prefix="/api", tags=["tables"])


@router.post("/sheets/{sheet_id}/extract-tables", response_model=ExtractTablesSummary)
def extract_tables(
    sheet_id: int,
    payload: ExtractTablesRequest | None = None,
    db: Session = Depends(get_db),
) -> ExtractTablesSummary:
    return cad_table_service.extract_tables_from_sheet(db, sheet_id, payload=payload)


@router.post("/imports/{batch_id}/extract-tables", response_model=BackgroundJobStatus)
def extract_tables_batch(
    batch_id: int,
    payload: ExtractTablesBatchRequest | None = None,
    db: Session = Depends(get_db),
) -> BackgroundJobStatus:
    return cad_table_service.start_extract_tables_batch_job(
        db, batch_id, payload or ExtractTablesBatchRequest()
    )


@router.get(
    "/imports/{batch_id}/extract-tables/job",
    response_model=BackgroundJobStatus | None,
)
def get_extract_tables_job(
    batch_id: int,
    db: Session = Depends(get_db),
) -> BackgroundJobStatus | None:
    return cad_table_service.get_extract_tables_job(db, batch_id)


@router.get("/sheets/{sheet_id}/tables", response_model=list[DrawingTableRecord])
def list_sheet_tables(
    sheet_id: int,
    db: Session = Depends(get_db),
) -> list[DrawingTableRecord]:
    return cad_table_service.list_tables_for_sheet(db, sheet_id)


@router.get("/projects/{project_id}/tables", response_model=list[DrawingTableRecord])
def list_project_tables(
    project_id: int,
    kind: str | None = Query(default=None, description="按表格类型筛选"),
    db: Session = Depends(get_db),
) -> list[DrawingTableRecord]:
    return cad_table_service.list_tables_for_project(db, project_id, kind=kind)
