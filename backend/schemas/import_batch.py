from datetime import datetime

from pydantic import BaseModel, ConfigDict

from backend.schemas.drawing_file import ImportedFileRead


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
