from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.core.database import get_db
from backend.schemas.background_job import BackgroundJobStatus
from backend.schemas.cad_pipeline import CadPipelineRequest
from backend.services import cad_pipeline_service

router = APIRouter(prefix="/api", tags=["cad-pipeline"])


@router.post("/imports/{batch_id}/cad-pipeline", response_model=BackgroundJobStatus)
def start_cad_pipeline(
    batch_id: int,
    payload: CadPipelineRequest,
    db: Session = Depends(get_db),
) -> BackgroundJobStatus:
    return cad_pipeline_service.start_cad_pipeline_job(db, batch_id, payload)


@router.get(
    "/imports/{batch_id}/cad-pipeline/job",
    response_model=BackgroundJobStatus | None,
)
def get_cad_pipeline_job(
    batch_id: int,
    db: Session = Depends(get_db),
) -> BackgroundJobStatus | None:
    return cad_pipeline_service.get_cad_pipeline_job(db, batch_id)
