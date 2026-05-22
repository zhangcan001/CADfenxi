import logging
from pathlib import Path

import pymupdf as fitz
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.core.config import settings
from backend.models.drawing_sheet import DrawingSheet
from backend.models.import_batch import ImportBatch
from backend.schemas.drawing_sheet import (
    BatchTitleCropResult,
    TitleCropBBox,
    TitleCropResult,
)

logger = logging.getLogger(__name__)


def calculate_bottom_right_bbox(width: int, height: int, ratio: float = 0.30) -> TitleCropBBox:
    crop_width = max(int(width * ratio), 1)
    crop_height = max(int(height * ratio), 1)
    return TitleCropBBox(
        x=max(width - crop_width, 0),
        y=max(height - crop_height, 0),
        width=crop_width,
        height=crop_height,
    )


def crop_title_block_for_sheet(db: Session, sheet_id: int) -> TitleCropResult:
    sheet = db.get(DrawingSheet, sheet_id)
    if sheet is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="图纸页不存在")

    if not sheet.preview_path:
        mark_failed(db, sheet, "PREVIEW_NOT_FOUND", "图纸页尚未生成预览图")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error_code": "PREVIEW_NOT_FOUND", "message": "图纸页尚未生成预览图"},
        )

    preview_path = settings.root_dir / sheet.preview_path
    if not preview_path.exists():
        mark_failed(db, sheet, "PREVIEW_FILE_MISSING", "预览图文件不存在")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error_code": "PREVIEW_FILE_MISSING", "message": "预览图文件不存在"},
        )

    try:
        crop_path, bbox = save_title_crop_image(sheet, preview_path)
        sheet.title_crop_path = crop_path
        sheet.title_crop_bbox = bbox.model_dump_json()
        sheet.title_crop_status = "success"
        sheet.title_crop_error_code = None
        sheet.title_crop_error_message = None
        db.commit()
        return TitleCropResult(
            sheet_id=sheet.id,
            status="success",
            title_crop_path=crop_path,
            title_crop_bbox=bbox,
        )
    except (OSError, RuntimeError, ValueError) as exc:
        logger.warning("Title crop failed sheet_id=%s: %s", sheet.id, exc)
        mark_failed(db, sheet, "CROP_FAILED", str(exc)[:500])
        return TitleCropResult(
            sheet_id=sheet.id,
            status="failed",
            error_code="CROP_FAILED",
            error_message=str(exc)[:500],
        )


def crop_title_blocks_for_batch(db: Session, batch_id: int) -> BatchTitleCropResult:
    batch = db.get(ImportBatch, batch_id)
    if batch is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="导入批次不存在")

    sheets = db.scalars(
        select(DrawingSheet)
        .where(DrawingSheet.batch_id == batch_id, DrawingSheet.status == "preprocessed")
        .order_by(DrawingSheet.id.asc())
    ).all()

    items: list[TitleCropResult] = []
    for sheet in sheets:
        try:
            items.append(crop_title_block_for_sheet(db, sheet.id))
        except HTTPException as exc:
            detail = exc.detail if isinstance(exc.detail, dict) else {}
            items.append(
                TitleCropResult(
                    sheet_id=sheet.id,
                    status="failed",
                    error_code=detail.get("error_code", "CROP_FAILED"),
                    error_message=detail.get("message", str(exc.detail)),
                )
            )

    success_count = sum(1 for item in items if item.status == "success")
    failed_count = len(items) - success_count
    return BatchTitleCropResult(
        batch_id=batch_id,
        total_count=len(items),
        success_count=success_count,
        failed_count=failed_count,
        items=items,
    )


def save_title_crop_image(sheet: DrawingSheet, preview_path: Path) -> tuple[str, TitleCropBBox]:
    crops_dir = settings.projects_dir / f"project_{sheet.project_id}" / "crops"
    crops_dir.mkdir(parents=True, exist_ok=True)
    target_path = crops_dir / f"sheet_{sheet.id}_title.png"

    document = fitz.open(str(preview_path))
    try:
        page = document.load_page(0)
        bbox = calculate_bottom_right_bbox(int(page.rect.width), int(page.rect.height))
        clip = fitz.Rect(bbox.x, bbox.y, bbox.x + bbox.width, bbox.y + bbox.height)
        crop = page.get_pixmap(clip=clip, alpha=False)
        crop.save(target_path)
    finally:
        document.close()
    return str(target_path.relative_to(settings.root_dir)), bbox


def title_crop_path(db: Session, sheet_id: int) -> Path:
    sheet = db.get(DrawingSheet, sheet_id)
    if sheet is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="图纸页不存在")
    if not sheet.title_crop_path:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="标题栏裁剪图不存在")
    path = settings.root_dir / sheet.title_crop_path
    if not path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="标题栏裁剪图文件不存在")
    return path


def mark_failed(db: Session, sheet: DrawingSheet, code: str, message: str) -> None:
    sheet.title_crop_status = "failed"
    sheet.title_crop_error_code = code
    sheet.title_crop_error_message = message
    db.commit()
