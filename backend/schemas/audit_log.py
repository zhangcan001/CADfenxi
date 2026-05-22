from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ReviewAuditLogRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    batch_id: int
    file_id: int
    sheet_id: int
    field_name: str | None
    old_value: str | None
    new_value: str | None
    action_type: str
    operator: str
    note: str | None
    created_at: datetime
