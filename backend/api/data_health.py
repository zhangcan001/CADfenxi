from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.core.database import get_db
from backend.schemas.data_health import (
    BackupRecordHealthResult,
    DataSafetySummary,
    ExportRecordHealthResult,
    MaintenanceReportResult,
    OrphanFileScanResult,
    ProjectHealthResult,
    SystemHealthResult,
    TempCleanupResult,
)
from backend.services import data_health_service

router = APIRouter(prefix="/api", tags=["data-health"])


@router.get("/system/health-check", response_model=SystemHealthResult)
def run_system_health_check(db: Session = Depends(get_db)) -> SystemHealthResult:
    return data_health_service.run_system_health_check(db)


@router.get("/system/data-safety-summary", response_model=DataSafetySummary)
def data_safety_summary(db: Session = Depends(get_db)) -> DataSafetySummary:
    return data_health_service.data_safety_summary(db)


@router.get("/system/maintenance-report", response_model=MaintenanceReportResult)
def maintenance_report(db: Session = Depends(get_db)) -> MaintenanceReportResult:
    return data_health_service.build_maintenance_report(db)


@router.post("/system/cleanup-temp", response_model=TempCleanupResult)
def cleanup_temp() -> TempCleanupResult:
    return TempCleanupResult.model_validate(data_health_service.cleanup_temp_files())


@router.get("/projects/{project_id}/health-check", response_model=ProjectHealthResult)
def run_project_integrity_check(project_id: int, db: Session = Depends(get_db)) -> ProjectHealthResult:
    return data_health_service.run_project_integrity_check(db, project_id)


@router.get("/projects/{project_id}/orphan-files", response_model=OrphanFileScanResult)
def scan_orphan_project_files(project_id: int, db: Session = Depends(get_db)) -> OrphanFileScanResult:
    orphan_files = data_health_service.scan_orphan_project_files(db, project_id)
    item = data_health_service.warning_item(
        "project",
        "orphan_files",
        f"发现 {len(orphan_files)} 个数据库未引用的项目文件。",
        "ORPHAN_FILE_FOUND",
        project_id=project_id,
        suggestion="请人工确认这些文件是否为历史残留或手动保存文件。本版本不会自动删除项目文件。",
    ) if orphan_files else None
    summary = data_health_service.build_summary(
        [item] if item else [],
        project_count=1,
        orphan_files=orphan_files,
    )
    return OrphanFileScanResult(
        project_id=project_id,
        status="warning" if orphan_files else "ok",
        generated_at=data_health_service.now(),
        summary=summary,
        grouped_summary=data_health_service.build_grouped_summary([item] if item else []),
        orphan_files=orphan_files,
    )


@router.get("/backups/health-check", response_model=BackupRecordHealthResult)
def run_backup_records_check(db: Session = Depends(get_db)) -> BackupRecordHealthResult:
    return data_health_service.check_backup_records(db)


@router.get("/exports/health-check", response_model=ExportRecordHealthResult)
def run_export_records_check(db: Session = Depends(get_db)) -> ExportRecordHealthResult:
    return data_health_service.check_export_records(db)
