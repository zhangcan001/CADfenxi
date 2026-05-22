from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

CadPipelineStepName = Literal[
    "convert_dwg",
    "prepare_dxf_sheet",
    "parse_dxf",
    "generate_candidates",
    "fuse_fields",
    "generate_cad_preview",
]

CadPipelineStatus = Literal["success", "completed_with_errors", "failed", "skipped"]


class CadPipelineRequest(BaseModel):
    steps: list[CadPipelineStepName] = Field(
        default_factory=lambda: [
            "convert_dwg",
            "prepare_dxf_sheet",
            "parse_dxf",
            "generate_candidates",
            "fuse_fields",
        ]
    )
    skip_completed: bool = True
    continue_on_error: bool = True


class CadPipelineError(BaseModel):
    file_id: int | None = None
    sheet_id: int | None = None
    file_name: str | None = None
    step: CadPipelineStepName
    error_code: str
    message: str


class CadPipelineItem(BaseModel):
    file_id: int | None = None
    sheet_id: int | None = None
    file_name: str | None = None
    status: str
    error_code: str | None = None
    message: str | None = None


class CadPipelineStepResult(BaseModel):
    step: CadPipelineStepName
    status: CadPipelineStatus
    duration_seconds: float = 0
    success_count: int = 0
    failed_count: int = 0
    skipped_count: int = 0
    warning_count: int = 0
    items: list[CadPipelineItem] = Field(default_factory=list)
    errors: list[CadPipelineError] = Field(default_factory=list)


class CadPipelineSummary(BaseModel):
    duration_seconds: float = 0
    start_time: datetime | None = None
    finish_time: datetime | None = None
    total_files: int
    pdf_files: int = 0
    dwg_files: int
    dxf_files: int
    converted_success: int = 0
    converted_failed: int = 0
    sheet_prepared_success: int = 0
    sheet_prepared_failed: int = 0
    parse_success: int = 0
    parse_failed: int = 0
    candidate_success: int = 0
    candidate_failed: int = 0
    fusion_success: int = 0
    fusion_failed: int = 0
    cad_preview_success: int = 0
    cad_preview_failed: int = 0
    cad_preview_skipped: int = 0
    cad_preview_warning_count: int = 0
    skipped_count: int = 0
    error_count: int = 0
    warning_count: int = 0


class CadPipelineResponse(BaseModel):
    batch_id: int
    status: CadPipelineStatus
    summary: CadPipelineSummary
    steps: list[CadPipelineStepResult]
    errors: list[CadPipelineError] = Field(default_factory=list)
