from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ProjectStats(BaseModel):
    file_count: int = 0
    sheet_count: int = 0
    preprocessed_count: int = 0
    recognized_count: int = 0
    need_review_count: int = 0
    confirmed_count: int = 0
    failed_count: int = 0
    issue_count: int = 0
    error_issue_count: int = 0
    warning_issue_count: int = 0
    trust_level_a_count: int = 0
    trust_level_b_count: int = 0
    trust_level_c_count: int = 0
    trust_level_d_count: int = 0


class ProjectCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    description: str | None = None

    @field_validator("name")
    @classmethod
    def name_must_not_be_blank(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("项目名称不能为空")
        return stripped

    @field_validator("description")
    @classmethod
    def normalize_description(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        return stripped or None


class ProjectUpdate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    description: str | None = None

    @field_validator("name")
    @classmethod
    def name_must_not_be_blank(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("项目名称不能为空")
        return stripped

    @field_validator("description")
    @classmethod
    def normalize_description(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        return stripped or None


class ProjectRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str | None
    status: str
    created_at: datetime
    updated_at: datetime
    last_opened_at: datetime | None
    stats: ProjectStats
