from datetime import datetime

from pydantic import BaseModel, ConfigDict


class DrawingIssueRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    batch_id: int
    file_id: int
    sheet_id: int
    issue_code: str
    severity: str
    message: str
    suggestion: str
    status: str
    created_at: datetime
    resolved_at: datetime | None
