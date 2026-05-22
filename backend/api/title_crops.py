from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from backend.core.database import get_db
from backend.schemas.drawing_sheet import BatchTitleCropResult, TitleCropResult
from backend.services import title_crop_service

router = APIRouter(prefix="/api", tags=["title-crops"])


@router.post("/sheets/{sheet_id}/title-crop", response_model=TitleCropResult)
def crop_sheet_title(sheet_id: int, db: Session = Depends(get_db)) -> TitleCropResult:
    return title_crop_service.crop_title_block_for_sheet(db, sheet_id)


@router.post("/imports/{batch_id}/title-crops", response_model=BatchTitleCropResult)
def crop_batch_titles(batch_id: int, db: Session = Depends(get_db)) -> BatchTitleCropResult:
    return title_crop_service.crop_title_blocks_for_batch(db, batch_id)


@router.get("/sheets/{sheet_id}/title-crop")
def get_sheet_title_crop(sheet_id: int, db: Session = Depends(get_db)) -> FileResponse:
    path = title_crop_service.title_crop_path(db, sheet_id)
    return FileResponse(path, media_type="image/png")
