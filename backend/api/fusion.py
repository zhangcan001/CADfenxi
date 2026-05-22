from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.core.database import get_db
from backend.schemas.field_evidence import FieldEvidenceRead
from backend.schemas.field_value import BatchFusionResult, FieldValueRead, SheetFusionResult
from backend.services import fusion_service

router = APIRouter(prefix="/api", tags=["fusion"])


@router.post("/sheets/{sheet_id}/fuse-fields", response_model=SheetFusionResult)
def fuse_sheet_fields(sheet_id: int, db: Session = Depends(get_db)) -> SheetFusionResult:
    return fusion_service.fuse_fields_for_sheet(db, sheet_id)


@router.post("/imports/{batch_id}/fuse-fields", response_model=BatchFusionResult)
def fuse_batch_fields(batch_id: int, db: Session = Depends(get_db)) -> BatchFusionResult:
    return fusion_service.fuse_fields_for_batch(db, batch_id)


@router.get("/sheets/{sheet_id}/field-values", response_model=list[FieldValueRead])
def list_sheet_field_values(sheet_id: int, db: Session = Depends(get_db)) -> list[FieldValueRead]:
    return [
        FieldValueRead.model_validate(value)
        for value in fusion_service.list_field_values(db, sheet_id)
    ]


@router.get("/sheets/{sheet_id}/evidence", response_model=list[FieldEvidenceRead])
def list_sheet_evidence(sheet_id: int, db: Session = Depends(get_db)) -> list[FieldEvidenceRead]:
    return fusion_service.list_field_evidence(db, sheet_id)
