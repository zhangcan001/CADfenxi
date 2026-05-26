"""跨图纸一致性校验 API。"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.core.database import get_db
from backend.services.consistency_check_service import (
    ConsistencyCheckSummary,
    run_consistency_check,
)

router = APIRouter(prefix="/api", tags=["consistency"])


@router.post(
    "/projects/{project_id}/consistency-check",
    response_model=ConsistencyCheckSummary,
)
def trigger_consistency_check(
    project_id: int,
    db: Session = Depends(get_db),
) -> ConsistencyCheckSummary:
    return run_consistency_check(db, project_id)
