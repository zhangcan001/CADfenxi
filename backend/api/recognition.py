from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.core.database import get_db
from backend.schemas.recognition_run import (
    BatchRecognitionResult,
    RecognitionRunRead,
    RecognitionRunResult,
)
from backend.services import ocr_service, pdf_text_service, recognition_run_service

router = APIRouter(prefix="/api", tags=["recognition"])


@router.post("/sheets/{sheet_id}/extract-text", response_model=RecognitionRunResult)
def extract_sheet_text(sheet_id: int, db: Session = Depends(get_db)) -> RecognitionRunResult:
    return pdf_text_service.extract_text_for_sheet(db, sheet_id)


@router.post("/sheets/{sheet_id}/ocr-title", response_model=RecognitionRunResult)
def ocr_sheet_title(sheet_id: int, db: Session = Depends(get_db)) -> RecognitionRunResult:
    return ocr_service.ocr_title_for_sheet(db, sheet_id)


@router.post("/imports/{batch_id}/extract-text", response_model=BatchRecognitionResult)
def extract_batch_text(batch_id: int, db: Session = Depends(get_db)) -> BatchRecognitionResult:
    return pdf_text_service.extract_text_for_batch(db, batch_id)


@router.post("/imports/{batch_id}/ocr-titles", response_model=BatchRecognitionResult)
def ocr_batch_titles(batch_id: int, db: Session = Depends(get_db)) -> BatchRecognitionResult:
    return ocr_service.ocr_titles_for_batch(db, batch_id)


@router.get("/sheets/{sheet_id}/recognition-runs", response_model=list[RecognitionRunRead])
def list_sheet_recognition_runs(
    sheet_id: int,
    db: Session = Depends(get_db),
) -> list[RecognitionRunRead]:
    return recognition_run_service.list_sheet_runs(db, sheet_id)
