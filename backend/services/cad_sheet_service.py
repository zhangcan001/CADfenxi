from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.models.drawing_file import DrawingFile
from backend.models.drawing_sheet import DrawingSheet
from backend.models.import_batch import ImportBatch
from backend.schemas.cad import (
    BatchDxfSheetPrepareItem,
    BatchDxfSheetPrepareResult,
    DxfSheetPrepareResult,
)


def prepare_dxf_sheet(db: Session, file_id: int) -> DxfSheetPrepareResult:
    drawing_file = db.get(DrawingFile, file_id)
    if drawing_file is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error_code": "FILE_NOT_FOUND", "message": "图纸文件不存在。"},
        )
    if not is_dxf_file(drawing_file):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error_code": "UNSUPPORTED_CAD_FORMAT",
                "message": "该接口仅支持 DXF 文件。",
            },
        )

    existing_sheet = get_existing_dxf_sheet(db, drawing_file.id)
    if existing_sheet is not None:
        ensure_dxf_file_status(db, drawing_file)
        return prepare_result(drawing_file, existing_sheet, created=False)

    sheet = DrawingSheet(
        project_id=drawing_file.project_id,
        batch_id=drawing_file.batch_id,
        file_id=drawing_file.id,
        page_no=1,
        sheet_type="drawing",
        status="cad_pending",
        review_status="unreviewed",
    )
    drawing_file.status = "cad_pending"
    drawing_file.page_count = max(drawing_file.page_count, 1)
    db.add(sheet)
    db.flush()
    update_batch_sheet_count(db, drawing_file.batch_id)
    db.commit()
    db.refresh(sheet)
    db.refresh(drawing_file)
    return prepare_result(drawing_file, sheet, created=True)


def prepare_dxf_sheets_for_batch(db: Session, batch_id: int) -> BatchDxfSheetPrepareResult:
    batch = db.get(ImportBatch, batch_id)
    if batch is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error_code": "IMPORT_BATCH_NOT_FOUND", "message": "导入批次不存在。"},
        )

    dxf_files = db.scalars(
        select(DrawingFile)
        .where(
            DrawingFile.batch_id == batch_id,
            (
                (DrawingFile.source_format == "dxf")
                | (DrawingFile.file_ext == ".dxf")
                | (
                    (DrawingFile.source_format == "dwg")
                    & (DrawingFile.convert_status == "success")
                    & (DrawingFile.converted_file_path.is_not(None))
                )
            ),
        )
        .order_by(DrawingFile.id.asc())
    ).all()

    items: list[BatchDxfSheetPrepareItem] = []
    created_count = 0
    existing_count = 0
    failed_count = 0

    for drawing_file in dxf_files:
        try:
            result = prepare_dxf_sheet(db, drawing_file.id)
            if result.created:
                created_count += 1
            else:
                existing_count += 1
            items.append(
                BatchDxfSheetPrepareItem(
                    file_id=result.file_id,
                    sheet_id=result.sheet_id,
                    status=result.status,
                    created=result.created,
                )
            )
        except HTTPException as exc:
            db.rollback()
            failed_count += 1
            detail = exc.detail if isinstance(exc.detail, dict) else {}
            items.append(
                BatchDxfSheetPrepareItem(
                    file_id=drawing_file.id,
                    status="failed",
                    error_code=detail.get("error_code", "DXF_SHEET_PREPARE_FAILED"),
                    message=detail.get("message", "DXF 图纸页准备失败。"),
                )
            )

    return BatchDxfSheetPrepareResult(
        batch_id=batch_id,
        total_dxf_count=len(dxf_files),
        created_count=created_count,
        existing_count=existing_count,
        failed_count=failed_count,
        items=items,
    )


def is_dxf_file(drawing_file: DrawingFile) -> bool:
    return (
        drawing_file.source_format == "dxf"
        or drawing_file.file_ext.lower() == ".dxf"
        or (
            drawing_file.source_format == "dwg"
            and drawing_file.convert_status == "success"
            and bool(drawing_file.converted_file_path)
        )
    )


def get_existing_dxf_sheet(db: Session, file_id: int) -> DrawingSheet | None:
    return db.scalar(
        select(DrawingSheet)
        .where(DrawingSheet.file_id == file_id, DrawingSheet.page_no == 1)
        .order_by(DrawingSheet.id.asc())
    )


def ensure_dxf_file_status(db: Session, drawing_file: DrawingFile) -> None:
    changed = False
    if drawing_file.status != "cad_pending":
        drawing_file.status = "cad_pending"
        changed = True
    if drawing_file.page_count < 1:
        drawing_file.page_count = 1
        changed = True
    if changed:
        update_batch_sheet_count(db, drawing_file.batch_id)
        db.commit()
        db.refresh(drawing_file)


def update_batch_sheet_count(db: Session, batch_id: int) -> None:
    sheet_count = db.scalar(
        select(func.count()).select_from(DrawingSheet).where(DrawingSheet.batch_id == batch_id)
    ) or 0
    batch = db.get(ImportBatch, batch_id)
    if batch is not None:
        batch.sheet_count = sheet_count


def prepare_result(
    drawing_file: DrawingFile,
    sheet: DrawingSheet,
    created: bool,
) -> DxfSheetPrepareResult:
    return DxfSheetPrepareResult(
        file_id=drawing_file.id,
        sheet_id=sheet.id,
        project_id=sheet.project_id,
        batch_id=sheet.batch_id,
        page_no=sheet.page_no,
        sheet_type=sheet.sheet_type,
        status=sheet.status,
        review_status=sheet.review_status,
        created=created,
    )
