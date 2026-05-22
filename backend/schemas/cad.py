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
