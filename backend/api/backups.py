from fastapi import APIRouter, Depends, Response, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from backend.core.database import get_db
from backend.schemas.backup import (
    BackupRecordRead,
    BackupVerifyResult,
    ProjectIntegrityResult,
    ProjectBackupResult,
    RestoreBackupRequest,
    RestoreBackupResult,
    RestoreRecordRead,
)
from backend.services import backup_integrity_service, backup_service, restore_service

router = APIRouter(prefix="/api", tags=["backups"])


@router.post("/projects/{project_id}/backup", response_model=ProjectBackupResult)
def create_project_backup(project_id: int, db: Session = Depends(get_db)) -> ProjectBackupResult:
    return backup_service.create_project_backup(db, project_id)


@router.get("/backups", response_model=list[BackupRecordRead])
def list_backups(db: Session = Depends(get_db)) -> list[BackupRecordRead]:
    return backup_service.list_backups(db)


@router.get("/projects/{project_id}/backups", response_model=list[BackupRecordRead])
def list_project_backups(project_id: int, db: Session = Depends(get_db)) -> list[BackupRecordRead]:
    return backup_service.list_project_backups(db, project_id)


@router.get("/backups/{backup_id}/download")
def download_backup(backup_id: int, db: Session = Depends(get_db)) -> FileResponse:
    path, file_name = backup_service.backup_file_path(db, backup_id)
    return FileResponse(path, filename=file_name, media_type="application/zip")


@router.get("/backups/{backup_id}/verify", response_model=BackupVerifyResult)
def verify_backup(backup_id: int, db: Session = Depends(get_db)) -> BackupVerifyResult:
    return backup_integrity_service.verify_backup_record(db, backup_id)


@router.get("/projects/{project_id}/integrity-check", response_model=ProjectIntegrityResult)
def check_project_integrity(project_id: int, db: Session = Depends(get_db)) -> ProjectIntegrityResult:
    return backup_integrity_service.check_project_integrity(db, project_id)


@router.delete("/backups/{backup_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_backup(backup_id: int, db: Session = Depends(get_db)) -> Response:
    backup_service.delete_backup(db, backup_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/backups/{backup_id}/restore", response_model=RestoreBackupResult)
def restore_backup(
    backup_id: int,
    payload: RestoreBackupRequest,
    db: Session = Depends(get_db),
) -> RestoreBackupResult:
    return restore_service.restore_project_backup_as_new_project(db, backup_id, payload.restore_mode)


@router.get("/restores", response_model=list[RestoreRecordRead])
def list_restores(db: Session = Depends(get_db)) -> list[RestoreRecordRead]:
    return restore_service.list_restores(db)
