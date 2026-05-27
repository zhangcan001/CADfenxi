from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class ExportCheckResult(BaseModel):
    can_export: bool = True
    is_complete_ledger: bool
    summary_message: str = ""
    sheet_count: int = 0
    unconfirmed_count: int
    open_error_count: int
    open_warning_count: int = 0
    open_error_sheet_count: int = 0
    open_warning_sheet_count: int = 0
    failed_count: int
    empty_drawing_no_count: int
    empty_drawing_name_count: int = 0
    empty_discipline_count: int = 0
    trust_level_d_count: int = 0
    duplicate_drawing_no_count: int
    drawing_table_count: int = 0
    low_confidence_table_count: int = 0
    block_stats_sheet_count: int = 0
    consistency_issue_count: int = 0
    warning_count: int = 0
    warnings: list[str]


class ExportExcelRequest(BaseModel):
    confirm_incomplete: bool = False
    include_issues: bool = True
    filter: dict[str, Any] | None = None


class ExportExcelResult(BaseModel):
    export_id: int
    project_id: int
    file_name: str
    file_path: str
    sheet_count: int
    ledger_row_count: int
    issue_row_count: int
    issue_count: int
    warning_count: int
    summary_sheet_count: int = 2
    precheck: dict[str, int]
    include_unconfirmed: bool
    has_open_errors: bool
    created_at: datetime
    download_url: str
    warning_summary: ExportCheckResult


class ExportRecordRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    export_id: int
    export_type: str
    file_name: str
    sheet_count: int
    issue_count: int
    include_unconfirmed: bool
    has_open_errors: bool
    created_at: datetime
    download_url: str
