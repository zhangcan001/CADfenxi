from datetime import datetime

from pydantic import BaseModel, ConfigDict

from backend.schemas.drawing_issue import DrawingIssueRead


class FieldValueRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    batch_id: int
    file_id: int
    sheet_id: int
    field_name: str
    raw_value: str
    normalized_value: str | None
    display_value: str
    final_source: str
    confidence: float
    is_reviewed: bool
    reviewed_at: datetime | None
    created_at: datetime
    updated_at: datetime


class SheetFusionResult(BaseModel):
    sheet_id: int
    status: str
    confidence_score: int
    trust_level: str
    field_values: list[FieldValueRead]
    issues: list[DrawingIssueRead]


class BatchFusionResult(BaseModel):
    batch_id: int
    total_count: int
    success_count: int
    failed_count: int
    issue_count: int
    items: list[SheetFusionResult]
