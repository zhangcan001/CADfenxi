from fastapi import APIRouter, Depends, File, Form, UploadFile, status
from sqlalchemy.orm import Session

from backend.core.database import get_db
from backend.schemas.drawing_file import DrawingFileRead
from backend.schemas.import_batch import ImportBatchRead
from backend.services import import_service

router = APIRouter(prefix="/api", tags=["imports"])


@router.post(
    "/projects/{project_id}/imports",
    response_model=ImportBatchRead,
    status_code=status.HTTP_201_CREATED,
)
def upload_project_pdfs(
    project_id: int,
    batch_name: str | None = Form(default=None),
    remark: str | None = Form(default=None),
    files: list[UploadFile] = File(default=[]),
    db: Session = Depends(get_db),
) -> ImportBatchRead:
    return import_service.create_import_batch(db, project_id, files, batch_name, remark)


@router.get("/imports/{batch_id}", response_model=ImportBatchRead)
def get_import_batch(batch_id: int, db: Session = Depends(get_db)) -> ImportBatchRead:
    return import_service.get_import_batch(db, batch_id)


@router.get("/projects/{project_id}/files", response_model=list[DrawingFileRead])
def list_project_files(
    project_id: int,
    db: Session = Depends(get_db),
) -> list[DrawingFileRead]:
    return import_service.list_project_files(db, project_id)
