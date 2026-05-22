from datetime import datetime

from pydantic import BaseModel, ConfigDict


class RecognitionCandidateRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    batch_id: int
    file_id: int
    sheet_id: int
    field_name: str
    candidate_value: str
    normalized_value: str | None
    source_type: str
    confidence: float
    raw_text: str
    bbox: str | None
    run_id: int | None
    parser_name: str
    parser_version: str
    created_at: datetime


class CandidateGenerateResult(BaseModel):
    sheet_id: int
    candidate_count: int
    candidates: list[RecognitionCandidateRead]


class BatchCandidateGenerateResult(BaseModel):
    batch_id: int
    total_count: int
    success_count: int
    failed_count: int
    candidate_count: int
    items: list[CandidateGenerateResult]
