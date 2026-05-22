from pydantic import BaseModel, Field

from backend.schemas.drawing_issue import DrawingIssueRead
from backend.schemas.field_value import FieldValueRead


class SheetFieldsUpdate(BaseModel):
    fields: dict[str, str | None] = Field(default_factory=dict)
    note: str | None = None


class AdoptCandidateRequest(BaseModel):
    candidate_id: int
    note: str | None = None


class RestoreRecommendedRequest(BaseModel):
    field_name: str
    note: str | None = None


class ConfirmSheetRequest(BaseModel):
    force: bool = False
    note: str | None = None


class IssueStatusUpdate(BaseModel):
    status: str
    note: str | None = None


class BatchConfirmRequest(BaseModel):
    sheet_ids: list[int] = Field(default_factory=list)
    confirm_mode: str = "trust_a"
    project_id: int | None = None
    only_without_errors: bool = True
    note: str | None = None


class ReviewUpdateResult(BaseModel):
    sheet_id: int
    updated_fields: list[FieldValueRead]
    confidence_score: int
    trust_level: str
    issues: list[DrawingIssueRead]


class AdoptCandidateResult(BaseModel):
    field_value: FieldValueRead
    confidence_score: int
    trust_level: str
    issues: list[DrawingIssueRead]


class ConfirmSheetResult(BaseModel):
    sheet_id: int
    status: str
    review_status: str
    forced_confirm: bool = False


class BatchConfirmResult(BaseModel):
    project_id: int | None = None
    requested_count: int
    confirmed_count: int
    skipped_count: int
    items: list[dict[str, str | int]]
    skipped: list[dict[str, str | int]] = Field(default_factory=list)
