from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.core.database import get_db
from backend.schemas.cad_pipeline import CadPipelineRequest, CadPipelineResponse
from backend.services import cad_pipeline_service

router = APIRouter(prefix="/api", tags=["cad-pipeline"])


@router.post("/imports/{batch_id}/cad-pipeline", response_model=CadPipelineResponse)
def run_cad_pipeline(
    batch_id: int,
    payload: CadPipelineRequest,
    db: Session = Depends(get_db),
) -> CadPipelineResponse:
    return cad_pipeline_service.run_cad_pipeline(db, batch_id, payload)
