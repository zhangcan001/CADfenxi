from datetime import datetime

from pydantic import BaseModel, ConfigDict


class BackupRecordRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    backup_id: int
    project_id: int
    backup_type: str = "project"
    file_name: str
    file_path: str
    file_size: int
    status: str
    created_at: datetime
    error_code: str | None = None
    error_message: str | None = None
    download_url: str


class ProjectBackupResult(BaseModel):
    backup_id: int
    project_id: int
    file_name: str
    file_path: str
    file_size: int
    created_at: datetime
    download_url: str


class RestoreBackupRequest(BaseModel):
    restore_mode: str = "new_project"


class RestoreBackupResult(BaseModel):
    restore_id: int
    backup_id: int
    source_project_name: str
    new_project_id: int
    new_project_name: str
    status: str
    restored_counts: dict[str, int]
    created_at: datetime


class RestoreRecordRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    restore_id: int
    source_backup_id: int | None
    source_project_name: str | None
    new_project_id: int | None
    restore_mode: str
    status: str
    created_at: datetime
    error_code: str | None = None
    error_message: str | None = None


class BackupVerifyResult(BaseModel):
    backup_id: int | None = None
    valid: bool
    warnings: list[str]
    errors: list[str]
    counts: dict[str, int]
    summary: dict[str, bool | int] = {}


class ProjectPathCheck(BaseModel):
    invalid_paths: int = 0
    missing_files: int = 0


class ProjectIntegrityResult(BaseModel):
    project_id: int
    valid: bool
    warnings: list[str]
    errors: list[str]
    path_check: ProjectPathCheck
    counts: dict[str, int]
