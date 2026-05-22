from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ConverterSettingBase(BaseModel):
    converter_name: str = "ODA File Converter"
    converter_exe_path: str
    output_version: str = "ACAD2018"
    output_type: str = "DXF"
    is_enabled: bool = True


class ConverterSettingCreate(ConverterSettingBase):
    pass


class ConverterSettingUpdate(BaseModel):
    converter_name: str | None = None
    converter_exe_path: str | None = None
    output_version: str | None = None
    output_type: str | None = None
    is_enabled: bool | None = None


class ConverterSettingRead(ConverterSettingBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    last_check_status: str | None
    last_check_message: str | None
    created_at: datetime
    updated_at: datetime


class ConverterCheckResult(BaseModel):
    setting_id: int
    status: str
    message: str


class CadConversionRunRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    batch_id: int
    source_file_id: int
    source_format: str
    target_format: str
    source_path: str
    target_path: str | None
    converter_name: str
    converter_exe_path: str
    status: str
    started_at: datetime
    finished_at: datetime | None
    error_code: str | None
    error_message: str | None
    stdout_log: str | None
    stderr_log: str | None
    created_at: datetime


class DwgConvertResult(BaseModel):
    file_id: int
    status: str
    run_id: int | None = None
    converted_file_path: str | None = None
    error_code: str | None = None
    error_message: str | None = None
    warning_code: str | None = None
    warning_message: str | None = None


class BatchDwgConvertResult(BaseModel):
    batch_id: int
    total_count: int
    success_count: int
    failed_count: int
    skipped_count: int = 0
    items: list[DwgConvertResult]
