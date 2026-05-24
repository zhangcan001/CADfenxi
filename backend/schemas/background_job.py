from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel


class BackgroundJobStatus(BaseModel):
    id: int
    job_type: str
    scope_type: Literal["batch", "project", "sheet"]
    scope_id: int
    status: Literal["running", "completed", "failed"]
    total: int
    processed: int
    current_step: str | None = None
    message: str | None = None
    started_at: datetime
    finished_at: datetime | None = None
    result_summary: dict[str, Any] | None = None
