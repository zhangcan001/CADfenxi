from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from backend.core.database import get_db
from backend.schemas.export import ExportCheckResult, ExportExcelRequest, ExportExcelResult, ExportRecordRead
from backend.services import export_check_service, export_service

router = APIRouter(prefix="/api", tags=["exports"])


@router.post("/projects/{project_id}/exports/check", response_model=ExportCheckResult)
def check_export(project_id: int, db: Session = Depends(get_db)) -> ExportCheckResult:
    return export_check_service.check_project_export(db, project_id)


@router.post("/projects/{project_id}/exports/excel", response_model=ExportExcelResult)
def export_excel(
    project_id: int,
    payload: ExportExcelRequest,
    db: Session = Depends(get_db),
) -> ExportExcelResult:
    return export_service.export_project_excel(db, project_id, payload)


@router.get("/projects/{project_id}/exports", response_model=list[ExportRecordRead])
def list_project_exports(project_id: int, db: Session = Depends(get_db)) -> list[ExportRecordRead]:
    return export_service.list_exports(db, project_id)


@router.get("/exports/{export_id}/download")
def download_export(export_id: int, db: Session = Depends(get_db)) -> FileResponse:
    path, file_name = export_service.export_file_path(db, export_id)
    return FileResponse(
        path,
        filename=file_name,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
