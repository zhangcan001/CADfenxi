from pydantic import BaseModel


class DxfSheetPrepareResult(BaseModel):
    file_id: int
    sheet_id: int
    project_id: int
    batch_id: int
    page_no: int
    sheet_type: str
    status: str
    review_status: str
    created: bool


class BatchDxfSheetPrepareItem(BaseModel):
    file_id: int
    sheet_id: int | None = None
    status: str
    created: bool = False
    error_code: str | None = None
    message: str | None = None


class BatchDxfSheetPrepareResult(BaseModel):
    batch_id: int
    total_dxf_count: int
    created_count: int
    existing_count: int
    failed_count: int
    items: list[BatchDxfSheetPrepareItem]


class CadParseResult(BaseModel):
    file_id: int
    sheet_id: int | None = None
    status: str
    run_id: int | None = None
    output_path: str | None = None
    counts: dict[str, int] = {}
    warnings: list[str] = []
    error_code: str | None = None
    error_message: str | None = None


class BatchCadParseResult(BaseModel):
    batch_id: int
    total_count: int
    success_count: int
    failed_count: int
    skipped_count: int
    items: list[CadParseResult]


class CadParseSummary(BaseModel):
    sheet_id: int
    file_id: int
    output_path: str
    counts: dict[str, int]
    sample_texts: list[dict]
    sample_mtexts: list[dict]
    sample_attribs: list[dict]
    layers: list[str]
    warnings: list[str] = []


class CadPreviewResult(BaseModel):
    file_id: int | None = None
    sheet_id: int
    file_name: str | None = None
    status: str
    cad_preview_path: str | None = None
    preview_url: str | None = None
    warnings: list[str] = []
    duration_seconds: float = 0
    skipped_entity_count: int = 0
    error_code: str | None = None
    error_message: str | None = None


class CadPreviewBatchRequest(BaseModel):
    skip_completed: bool = True
    force: bool = False
    continue_on_error: bool = True


class CadPreviewBatchSummary(BaseModel):
    total_count: int
    success_count: int
    failed_count: int
    skipped_count: int = 0
    warning_count: int = 0
    duration_seconds: float = 0


class CadPreviewBatchError(BaseModel):
    sheet_id: int | None = None
    file_name: str | None = None
    error_code: str
    message: str


class BatchCadPreviewResult(BaseModel):
    scope: str = "batch"
    project_id: int | None = None
    batch_id: int | None = None
    status: str = "success"
    summary: CadPreviewBatchSummary
    total_count: int
    success_count: int
    failed_count: int
    skipped_count: int = 0
    warning_count: int = 0
    duration_seconds: float = 0
    items: list[CadPreviewResult]
    errors: list[CadPreviewBatchError] = []
    warnings: list[str] = []
