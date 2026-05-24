from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict


class RecognitionRunRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    batch_id: int
    file_id: int | None
    sheet_id: int
    run_type: str
    engine_name: str
    engine_version: str
    status: str
    output_path: str | None
    started_at: datetime
    finished_at: datetime
    error_code: str | None
    error_message: str | None
    created_at: datetime


class RecognitionRunResult(BaseModel):
    sheet_id: int
    status: str
    run_type: str
    output_path: str | None
    text_length: int
    error_code: str | None = None
    error_message: str | None = None


class BatchRecognitionResult(BaseModel):
    batch_id: int
    total_count: int
    success_count: int
    failed_count: int
    items: list[RecognitionRunResult]


class OcrJobStatus(BaseModel):
    batch_id: int
    status: Literal["idle", "running", "completed", "failed"]
    total: int
    processed: int
    success_count: int
    failed_count: int
    started_at: datetime | None = None
    finished_at: datetime | None = None
    message: str | None = None
