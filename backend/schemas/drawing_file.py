from datetime import datetime

from pydantic import BaseModel, ConfigDict


class DrawingFileRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    batch_id: int
    original_name: str
    file_ext: str
    source_format: str
    file_size: int
    file_hash: str
    page_count: int
    storage_path: str
    status: str
    error_code: str | None
    error_message: str | None
    parse_status: str | None
    parse_error_code: str | None
    parse_error_message: str | None
    converted_format: str | None
    converted_file_path: str | None
    convert_status: str | None
    convert_error_code: str | None
    convert_error_message: str | None
    created_at: datetime
    updated_at: datetime


class ImportedFileRead(BaseModel):
    id: int
    original_name: str
    file_ext: str
    source_format: str
    file_size: int
    file_hash: str
    page_count: int
    status: str
    storage_path: str
    converted_format: str | None = None
    converted_file_path: str | None = None
    convert_status: str | None = None
    convert_error_code: str | None = None
    convert_error_message: str | None = None
    warnings: list[str] = []
