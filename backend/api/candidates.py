from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from backend.core.database import get_db
from backend.schemas.recognition_candidate import (
    BatchCandidateGenerateResult,
    CandidateGenerateResult,
    RecognitionCandidateRead,
)
from backend.services import candidate_service

router = APIRouter(prefix="/api", tags=["candidates"])


@router.post("/sheets/{sheet_id}/generate-candidates", response_model=CandidateGenerateResult)
def generate_sheet_candidates(
    sheet_id: int,
    db: Session = Depends(get_db),
) -> CandidateGenerateResult:
    return candidate_service.generate_candidates_for_sheet(db, sheet_id)


@router.post("/imports/{batch_id}/generate-candidates", response_model=BatchCandidateGenerateResult)
def generate_batch_candidates(
    batch_id: int,
    db: Session = Depends(get_db),
) -> BatchCandidateGenerateResult:
    return candidate_service.generate_candidates_for_batch(db, batch_id)


@router.get("/sheets/{sheet_id}/candidates", response_model=list[RecognitionCandidateRead])
def list_sheet_candidates(
    sheet_id: int,
    field_name: str | None = Query(default=None),
    db: Session = Depends(get_db),
) -> list[RecognitionCandidateRead]:
    return candidate_service.list_candidates(db, sheet_id, field_name)


@router.delete("/sheets/{sheet_id}/candidates")
def clear_sheet_candidates(sheet_id: int, db: Session = Depends(get_db)) -> dict[str, int]:
    deleted_count = candidate_service.clear_machine_candidates(db, sheet_id)
    return {"deleted_count": deleted_count}
