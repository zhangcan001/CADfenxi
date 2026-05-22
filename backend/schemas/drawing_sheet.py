from datetime import datetime

from pydantic import BaseModel, ConfigDict


class DrawingSheetListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    batch_id: int
    file_id: int
    page_no: int
    sheet_type: str
    drawing_no: str | None = None
    drawing_name: str | None = None
    discipline: str | None = None
    version: str | None = None
    issue_date: str | None = None
    confidence_score: float | None = None
    trust_level: str | None = None
    status: str
    review_status: str
    thumbnail_path: str | None
    preview_path: str | None
    title_crop_path: str | None
    title_crop_status: str | None
    title_crop_error_code: str | None
    title_crop_error_message: str | None
    issue_count: int = 0
    error_count: int = 0
    warning_count: int = 0
    info_count: int = 0
    thumbnail_url: str | None = None
    preview_url: str | None = None
    original_file_name: str
    source_format: str
    created_at: datetime
    updated_at: datetime


class DrawingSheetRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    batch_id: int
    file_id: int
    page_no: int
    sheet_type: str
    drawing_no: str | None
    drawing_name: str | None
    discipline: str | None
    version: str | None
    issue_date: str | None
    confidence_score: float | None
    trust_level: str | None
    status: str
    review_status: str
    thumbnail_path: str | None
    preview_path: str | None
    title_crop_path: str | None
    title_crop_bbox: str | None
    title_crop_status: str | None
    title_crop_error_code: str | None
    title_crop_error_message: str | None
    error_code: str | None
    error_message: str | None
    created_at: datetime
    updated_at: datetime
    original_file_name: str
    source_format: str


class SplitSheetRead(BaseModel):
    id: int
    page_no: int
    status: str
    preview_path: str | None
    thumbnail_path: str | None


class FileSplitResult(BaseModel):
    file_id: int
    project_id: int
    batch_id: int
    page_count: int
    created_count: int
    failed_count: int
    sheets: list[SplitSheetRead]


class BatchFileSplitResult(BaseModel):
    file_id: int
    page_count: int
    sheet_count: int
    failed_count: int


class BatchSplitResult(BaseModel):
    batch_id: int
    file_count: int
    sheet_count: int
    failed_count: int
    files: list[BatchFileSplitResult]


class TitleCropBBox(BaseModel):
    x: int
    y: int
    width: int
    height: int


class TitleCropResult(BaseModel):
    sheet_id: int
    status: str
    title_crop_path: str | None = None
    title_crop_bbox: TitleCropBBox | None = None
    error_code: str | None = None
    error_message: str | None = None


class BatchTitleCropResult(BaseModel):
    batch_id: int
    total_count: int
    success_count: int
    failed_count: int
    items: list[TitleCropResult]
