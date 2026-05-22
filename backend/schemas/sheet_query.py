from pydantic import BaseModel, Field


class SheetQueryParams(BaseModel):
    keyword: str | None = None
    batch_id: int | None = None
    file_id: int | None = None
    discipline: str | None = None
    status: str | None = None
    review_status: str | None = None
    trust_level: str | None = None
    source_format: str | None = None
    issue_severity: str | None = None
    issue_code: str | None = None
    has_issue: bool | None = None
    has_error: bool | None = None
    has_warning: bool | None = None
    low_confidence: bool | None = None
    missing_field: str | None = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)
    sort_by: str = "created_at"
    sort_order: str = "desc"
