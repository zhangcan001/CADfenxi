from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

HealthStatus = Literal["ok", "info", "warning", "error"]


class DataHealthItem(BaseModel):
    scope: str
    check_name: str
    status: HealthStatus
    message: str
    error_code: str | None = None
    path: str | None = None
    record_type: str | None = None
    record_id: int | None = None
    project_id: int | None = None
    suggestion: str | None = None
    is_checked_file: bool = Field(default=False, exclude=True)
    is_missing_file: bool = Field(default=False, exclude=True)


class OrphanFileItem(BaseModel):
    project_id: int
    path: str
    size_bytes: int
    suggestion: str = "该文件未被数据库记录引用。请确认不是人工保留文件后再手动处理。"


class DataHealthSummary(BaseModel):
    ok_count: int = 0
    info_count: int = 0
    warning_count: int = 0
    error_count: int = 0
    checked_file_count: int = 0
    missing_file_count: int = 0
    orphan_file_count: int = 0
    orphan_file_size_bytes: int = 0
    temp_file_count: int = 0
    temp_size_bytes: int = 0
    project_count: int = 0
    backup_count: int = 0
    export_count: int = 0
    restore_count: int = 0


class DataHealthGroupSummary(BaseModel):
    error: int = 0
    warning: int = 0
    info: int = 0


class SystemHealthResult(BaseModel):
    status: HealthStatus
    generated_at: datetime
    app_data_path: str
    summary: DataHealthSummary
    grouped_summary: dict[str, DataHealthGroupSummary] = Field(default_factory=dict)
    items: list[DataHealthItem] = Field(default_factory=list)


class ProjectHealthResult(BaseModel):
    project_id: int
    project_name: str
    status: HealthStatus
    generated_at: datetime
    project_path: str
    summary: DataHealthSummary
    grouped_summary: dict[str, DataHealthGroupSummary] = Field(default_factory=dict)
    items: list[DataHealthItem] = Field(default_factory=list)
    orphan_files: list[OrphanFileItem] = Field(default_factory=list)


class BackupRecordHealthResult(BaseModel):
    status: HealthStatus
    generated_at: datetime
    summary: DataHealthSummary
    grouped_summary: dict[str, DataHealthGroupSummary] = Field(default_factory=dict)
    items: list[DataHealthItem] = Field(default_factory=list)


class ExportRecordHealthResult(BaseModel):
    status: HealthStatus
    generated_at: datetime
    summary: DataHealthSummary
    grouped_summary: dict[str, DataHealthGroupSummary] = Field(default_factory=dict)
    items: list[DataHealthItem] = Field(default_factory=list)


class OrphanFileScanResult(BaseModel):
    project_id: int
    status: HealthStatus
    generated_at: datetime
    summary: DataHealthSummary
    grouped_summary: dict[str, DataHealthGroupSummary] = Field(default_factory=dict)
    orphan_files: list[OrphanFileItem] = Field(default_factory=list)


class TempCleanupResult(BaseModel):
    status: HealthStatus
    deleted_file_count: int
    deleted_dir_count: int
    freed_bytes: int
    errors: list[str] = Field(default_factory=list)


class DataSafetySummary(BaseModel):
    app_data_path: str
    database_exists: bool
    projects_dir_exists: bool
    backups_dir_exists: bool
    logs_dir_exists: bool
    temp_dir_exists: bool
    project_count: int
    backup_count: int
    export_count: int
    restore_count: int
    app_data_writable: bool


class MaintenanceReportResult(BaseModel):
    status: HealthStatus
    generated_at: datetime
    report_markdown: str
    system_health: SystemHealthResult
