from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from backend.schemas.drawing_file import ImportedFileRead


class ImportItemRead(BaseModel):
    file_name: str
    file_type: str
    status: str
    warning: str | None = None
    error_code: str | None = None
    message: str | None = None


class ImportBatchRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    batch_name: str
    file_count: int
    sheet_count: int
    recognized_count: int
    failed_count: int
    confirmed_count: int
    remark: str | None
    created_at: datetime
    updated_at: datetime
    files: list[ImportedFileRead]
    total_selected: int = 0
    imported_count: int = 0
    duplicate_count: int = 0
    unsupported_count: int = 0
    file_type_counts: dict[str, int] = Field(default_factory=dict)
    items: list[ImportItemRead] = Field(default_factory=list)
    next_actions: list[str] = Field(default_factory=list)
