import logging
from pathlib import Path

import pymupdf as fitz
from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.core.config import settings
from backend.models.drawing_file import DrawingFile
from backend.models.drawing_issue import DrawingIssue
from backend.models.drawing_sheet import DrawingSheet
from backend.models.import_batch import ImportBatch
from backend.schemas.drawing_sheet import (
    BatchFileSplitResult,
    BatchSplitResult,
    DrawingSheetListItem,
    DrawingSheetRead,
    FileSplitResult,
    SplitSheetRead,
)
from backend.services import preview_service

logger = logging.getLogger(__name__)


def split_file(db: Session, file_id: int) -> FileSplitResult:
    drawing_file = db.get(DrawingFile, file_id)
    if drawing_file is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error_code": "FILE_NOT_FOUND", "message": "PDF 文件不存在"},
        )
    if drawing_file.file_ext.lower() != ".pdf":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error_code": "UNSUPPORTED_FORMAT", "message": "仅支持 PDF 文件拆页"},
        )

    existing = existing_sheets(db, file_id)
    if existing:
        return file_split_result(drawing_file, existing, created_count=0)

    source_path = settings.root_dir / drawing_file.storage_path
    try:
        document = fitz.open(source_path)
    except (OSError, RuntimeError, fitz.FileDataError) as exc:
        logger.warning("PDF open failed file_id=%s path=%s: %s", drawing_file.id, source_path, exc)
        drawing_file.status = "failed"
        drawing_file.error_code = "PDF_OPEN_FAILED"
        drawing_file.error_message = str(exc)[:500]
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error_code": "PDF_OPEN_FAILED", "message": "PDF 文件无法打开"},
        ) from exc

    created_sheets: list[DrawingSheet] = []
    try:
        drawing_file.page_count = document.page_count
        if document.page_count <= 0:
            drawing_file.status = "failed"
            drawing_file.error_code = "PDF_OPEN_FAILED"
            drawing_file.error_message = "PDF 页数为空"
            db.commit()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"error_code": "PDF_OPEN_FAILED", "message": "PDF 页数为空"},
            )

        for page_index in range(document.page_count):
            sheet = DrawingSheet(
                project_id=drawing_file.project_id,
                batch_id=drawing_file.batch_id,
                file_id=drawing_file.id,
                page_no=page_index + 1,
                sheet_type="unknown",
                status="imported",
                review_status="pending",
            )
            db.add(sheet)
            db.flush()

            try:
                page = document.load_page(page_index)
                preview_path, thumbnail_path = preview_service.render_page(
                    page, drawing_file.project_id, sheet.id
                )
                sheet.preview_path = preview_path
                sheet.thumbnail_path = thumbnail_path
                sheet.status = "preprocessed"
            except (OSError, RuntimeError, ValueError) as exc:
                logger.warning("PDF render failed sheet_id=%s page=%s: %s", sheet.id, page_index + 1, exc)
                sheet.status = "failed"
                sheet.error_code = "PDF_RENDER_FAILED"
                sheet.error_message = str(exc)[:500]
            created_sheets.append(sheet)

        drawing_file.status = "preprocessed"
        db.commit()
        for sheet in created_sheets:
            db.refresh(sheet)
        db.refresh(drawing_file)
    finally:
        document.close()

    update_batch_sheet_count(db, drawing_file.batch_id)
    return file_split_result(drawing_file, created_sheets, created_count=len(created_sheets))


def split_batch(db: Session, batch_id: int) -> BatchSplitResult:
    batch = db.get(ImportBatch, batch_id)
    if batch is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="导入批次不存在")

    files = db.scalars(
        select(DrawingFile)
        .where(DrawingFile.batch_id == batch_id)
        .order_by(DrawingFile.id.asc())
    ).all()

    results = []
    for drawing_file in files:
        if drawing_file.file_ext.lower() != ".pdf":
            results.append(
                BatchFileSplitResult(
                    file_id=drawing_file.id,
                    page_count=drawing_file.page_count,
                    sheet_count=0,
                    failed_count=0,
                )
            )
            continue
        result = split_file(db, drawing_file.id)
        results.append(
            BatchFileSplitResult(
                file_id=drawing_file.id,
                page_count=result.page_count,
                sheet_count=len(result.sheets),
                failed_count=result.failed_count,
            )
        )

    sheet_count = update_batch_sheet_count(db, batch_id)
    failed_count = sheet_count_by_status(db, batch_id, "failed")
    return BatchSplitResult(
        batch_id=batch_id,
        file_count=len(files),
        sheet_count=sheet_count,
        failed_count=failed_count,
        files=results,
    )


def list_project_sheets(
    db: Session,
    project_id: int,
    file_id: int | None = None,
    batch_id: int | None = None,
    sheet_status: str | None = None,
) -> list[DrawingSheetListItem]:
    query = (
        select(DrawingSheet, DrawingFile.original_name, DrawingFile.source_format)
        .join(DrawingFile, DrawingFile.id == DrawingSheet.file_id)
        .where(DrawingSheet.project_id == project_id)
        .order_by(DrawingSheet.created_at.desc(), DrawingSheet.id.desc())
    )
    if file_id is not None:
        query = query.where(DrawingSheet.file_id == file_id)
    if batch_id is not None:
        query = query.where(DrawingSheet.batch_id == batch_id)
    if sheet_status is not None:
        query = query.where(DrawingSheet.status == sheet_status)

    return [
        DrawingSheetListItem.model_validate(
            {
                **sheet.__dict__,
                "issue_date": sheet.issue_date.isoformat() if sheet.issue_date else None,
                "issue_count": open_issue_count(db, sheet.id),
                "original_file_name": original_name,
                "source_format": source_format,
            }
        )
        for sheet, original_name, source_format in db.execute(query).all()
    ]


def get_sheet_detail(db: Session, sheet_id: int) -> DrawingSheetRead:
    sheet, original_name, source_format = get_sheet_with_file_name(db, sheet_id)
    return DrawingSheetRead.model_validate(
        {
            **sheet.__dict__,
            "issue_date": sheet.issue_date.isoformat() if sheet.issue_date else None,
            "original_file_name": original_name,
            "source_format": source_format,
            "cad_preview_url": f"/api/sheets/{sheet.id}/cad-preview-image" if sheet.cad_preview_path else None,
        }
    )


def sheet_preview_path(db: Session, sheet_id: int, kind: str) -> Path:
    sheet = db.get(DrawingSheet, sheet_id)
    if sheet is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="图纸页不存在")
    relative = sheet.preview_path if kind == "preview" else sheet.thumbnail_path
    if not relative:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="图片不存在")
    path = settings.root_dir / relative
    if not path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="图片文件不存在")
    return path


def project_sheet_count(db: Session, project_id: int) -> int:
    return db.scalar(
        select(func.count()).select_from(DrawingSheet).where(DrawingSheet.project_id == project_id)
    ) or 0


def project_sheet_count_by_status(db: Session, project_id: int, sheet_status: str) -> int:
    return db.scalar(
        select(func.count())
        .select_from(DrawingSheet)
        .where(DrawingSheet.project_id == project_id, DrawingSheet.status == sheet_status)
    ) or 0


def open_issue_count(db: Session, sheet_id: int) -> int:
    return db.scalar(
        select(func.count())
        .select_from(DrawingIssue)
        .where(DrawingIssue.sheet_id == sheet_id, DrawingIssue.status == "open")
    ) or 0


def existing_sheets(db: Session, file_id: int) -> list[DrawingSheet]:
    return db.scalars(
        select(DrawingSheet)
        .where(DrawingSheet.file_id == file_id)
        .order_by(DrawingSheet.page_no.asc())
    ).all()


def file_split_result(
    drawing_file: DrawingFile,
    sheets: list[DrawingSheet],
    created_count: int,
) -> FileSplitResult:
    return FileSplitResult(
        file_id=drawing_file.id,
        project_id=drawing_file.project_id,
        batch_id=drawing_file.batch_id,
        page_count=drawing_file.page_count,
        created_count=created_count,
        failed_count=sum(1 for sheet in sheets if sheet.status == "failed"),
        sheets=[
            SplitSheetRead(
                id=sheet.id,
                page_no=sheet.page_no,
                status=sheet.status,
                preview_path=sheet.preview_path,
                thumbnail_path=sheet.thumbnail_path,
            )
            for sheet in sheets
        ],
    )


def update_batch_sheet_count(db: Session, batch_id: int) -> int:
    sheet_count = db.scalar(
        select(func.count()).select_from(DrawingSheet).where(DrawingSheet.batch_id == batch_id)
    ) or 0
    batch = db.get(ImportBatch, batch_id)
    if batch is not None:
        batch.sheet_count = sheet_count
        db.commit()
    return sheet_count


def sheet_count_by_status(db: Session, batch_id: int, sheet_status: str) -> int:
    return db.scalar(
        select(func.count())
        .select_from(DrawingSheet)
        .where(DrawingSheet.batch_id == batch_id, DrawingSheet.status == sheet_status)
    ) or 0


def get_sheet_with_file_name(db: Session, sheet_id: int) -> tuple[DrawingSheet, str, str]:
    result = db.execute(
        select(DrawingSheet, DrawingFile.original_name, DrawingFile.source_format)
        .join(DrawingFile, DrawingFile.id == DrawingSheet.file_id)
        .where(DrawingSheet.id == sheet_id)
    ).first()
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="图纸页不存在")
    return result
