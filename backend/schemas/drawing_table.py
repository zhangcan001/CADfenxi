"""DXF 表格抽取相关 Pydantic schema。"""
from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


ExtractionMethod = Literal["acad_table", "text_cluster"]
TableKind = Literal["equipment", "material", "drawing_index", "legend", "other"]


class ExtractTablesRequest(BaseModel):
    include_acad_table: bool = True
    include_text_cluster: bool = True
    force: bool = True


class ExtractTablesBatchRequest(BaseModel):
    include_acad_table: bool = True
    include_text_cluster: bool = True
    force: bool = True
    continue_on_error: bool = True


class ExtractTablesSummary(BaseModel):
    sheet_id: int
    acad_table_count: int = 0
    text_cluster_count: int = 0
    total_count: int = 0
    by_kind: dict[str, int] = Field(default_factory=dict)


class DrawingTableRecord(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    batch_id: int
    file_id: int
    sheet_id: int
    table_index: int
    extraction_method: ExtractionMethod
    table_kind: TableKind
    layer_name: str | None = None
    header: list[str] = Field(default_factory=list)
    rows: list[list[str]] = Field(default_factory=list)
    row_count: int
    col_count: int
    source_bbox: list[float] | None = None
    warnings: list[str] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime
