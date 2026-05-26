"""DXF INSERT 块统计相关 Pydantic schema。"""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ExtractBlockStatsRequest(BaseModel):
    force: bool = True


class ExtractBlockStatsBatchRequest(BaseModel):
    force: bool = True
    continue_on_error: bool = True


class BlockStatsSummary(BaseModel):
    sheet_id: int
    total_block_count: int = 0
    distinct_blocks: int = 0
    by_discipline: dict[str, int] = Field(default_factory=dict)


class DrawingBlockStatRecord(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    batch_id: int
    file_id: int
    sheet_id: int
    block_name: str
    layer_name: str | None = None
    discipline_guess: str | None = None
    count: int
    sample_bbox: list[float] | None = None
    attribs_summary: dict[str, list[str]] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime
