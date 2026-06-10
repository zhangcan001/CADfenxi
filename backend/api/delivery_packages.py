from fastapi import APIRouter, Depends, Query
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from backend.core.database import get_db
from backend.schemas.delivery_package import DeliveryPackageRequest, DeliveryPackageResult
from backend.services import delivery_package_service

router = APIRouter(prefix="/api", tags=["delivery-packages"])


@router.post("/projects/{project_id}/delivery-package", response_model=DeliveryPackageResult)
def create_delivery_package(
    project_id: int,
    payload: DeliveryPackageRequest,
    db: Session = Depends(get_db),
) -> DeliveryPackageResult:
    return delivery_package_service.create_project_delivery_package(db, project_id, payload)


@router.get("/projects/{project_id}/delivery-package/download")
def download_delivery_package(
    project_id: int,
    package_id: str = Query(...),
    db: Session = Depends(get_db),
) -> FileResponse:
    path, file_name = delivery_package_service.delivery_package_file_path(db, project_id, package_id)
    return FileResponse(path, filename=file_name, media_type="application/zip")
