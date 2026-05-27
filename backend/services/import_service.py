import logging
from datetime import datetime
from pathlib import Path

from fastapi import HTTPException, UploadFile, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from backend.models.drawing_file import DrawingFile
from backend.models.import_batch import ImportBatch
from backend.models.project import Project
from backend.schemas.drawing_file import DrawingFileRead, ImportedFileRead
from backend.schemas.import_batch import ImportBatchRead, ImportItemRead
from backend.services import file_storage_service
from backend.services.project_service import get_project_or_404

logger = logging.getLogger(__name__)


def create_import_batch(
    db: Session,
    project_id: int,
    files: list[UploadFile],
    batch_name: str | None,
    remark: str | None,
) -> ImportBatchRead:
    if db.get(Project, project_id) is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error_code": "PROJECT_NOT_FOUND", "message": "项目不存在。"},
        )
    if not files:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error_code": "EMPTY_FILE", "message": "上传文件不能为空。"},
        )

    normalized_batch_name = normalize_batch_name(batch_name)
    normalized_remark = normalize_text(remark)
    saved_paths: list[Path] = []
    import_items: list[ImportItemRead] = []
    file_type_counts = empty_file_type_counts()
    imported_type_counts = empty_file_type_counts()

    try:
        batch = ImportBatch(
            project_id=project_id,
            batch_name=normalized_batch_name,
            remark=normalized_remark,
        )
        db.add(batch)
        db.flush()

        imported_files: list[tuple[DrawingFile, list[str]]] = []
        existing_hashes = set(
            db.scalars(
                select(DrawingFile.file_hash).where(DrawingFile.project_id == project_id)
            ).all()
        )

        for upload in files:
            file_name = upload.filename or "未命名文件"
            file_ext, source_format = classify_upload(file_name)
            if source_format is None:
                file_type_counts["unsupported"] += 1
                import_items.append(
                    ImportItemRead(
                        file_name=file_name,
                        file_type="unsupported",
                        status="unsupported",
                        error_code="UNSUPPORTED_FILE_TYPE",
                        message="当前文件格式不支持，请导入 PDF、DXF 或 DWG 文件。",
                    )
                )
                continue

            file_type_counts[source_format] += 1
            try:
                saved_path, file_size, file_hash = file_storage_service.save_drawing_file(
                    project_id, upload, file_ext
                )
            except HTTPException as exc:
                import_items.append(
                    ImportItemRead(
                        file_name=file_name,
                        file_type=source_format,
                        status="failed",
                        error_code=http_error_code(exc, "IMPORT_SAVE_FAILED"),
                        message=http_error_message(exc, "文件保存失败。"),
                    )
                )
                continue
            except Exception:
                logger.exception("Import save failed project_id=%s file=%s", project_id, file_name)
                import_items.append(
                    ImportItemRead(
                        file_name=file_name,
                        file_type=source_format,
                        status="failed",
                        error_code="IMPORT_SAVE_FAILED",
                        message="文件保存失败。",
                    )
                )
                continue

            if file_size <= 0:
                saved_path.unlink(missing_ok=True)
                import_items.append(
                    ImportItemRead(
                        file_name=file_name,
                        file_type=source_format,
                        status="failed",
                        error_code="EMPTY_FILE",
                        message="文件为空，请重新选择有效图纸文件。",
                    )
                )
                continue

            saved_paths.append(saved_path)
            warnings = []
            item_status = "imported"
            item_warning = None
            item_error_code = None
            item_message = None
            if file_hash in existing_hashes:
                warnings.append("duplicate_file")
                item_status = "duplicate"
                item_warning = "duplicate_file"
                item_error_code = "DUPLICATE_FILE"
                item_message = "该文件疑似已导入过，本次已标记为重复。"
            existing_hashes.add(file_hash)
            imported_type_counts[source_format] += 1

            drawing_file = DrawingFile(
                project_id=project_id,
                batch_id=batch.id,
                original_name=file_name,
                file_ext=file_ext,
                source_format=source_format,
                file_size=file_size,
                file_hash=file_hash,
                page_count=0,
                storage_path=str(saved_path.relative_to(file_storage_service.settings.root_dir)),
                status="imported",
                convert_status="pending" if source_format == "dwg" else "skipped",
            )
            db.add(drawing_file)
            imported_files.append((drawing_file, warnings))
            import_items.append(
                ImportItemRead(
                    file_name=file_name,
                    file_type=source_format,
                    status=item_status,
                    warning=item_warning,
                    error_code=item_error_code,
                    message=item_message,
                )
            )

        batch.file_count = len(imported_files)
        batch.failed_count = count_items(import_items, "failed")
        db.flush()
        db.refresh(batch)
        for drawing_file, _ in imported_files:
            db.refresh(drawing_file)
        db.commit()

        return batch_to_read(
            batch,
            imported_files,
            import_items=import_items,
            total_selected=len(files),
            file_type_counts=file_type_counts,
            next_actions=next_actions_for_counts(imported_type_counts),
        )
    except HTTPException:
        db.rollback()
        file_storage_service.remove_saved_files(saved_paths)
        raise
    except Exception:
        logger.exception("Import batch creation failed project_id=%s", project_id)
        db.rollback()
        file_storage_service.remove_saved_files(saved_paths)
        raise


def get_import_batch(db: Session, batch_id: int) -> ImportBatchRead:
    batch = db.scalar(
        select(ImportBatch)
        .options(selectinload(ImportBatch.files))
        .where(ImportBatch.id == batch_id)
    )
    if batch is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="导入批次不存在",
        )
    return batch_to_read(batch, [(file, []) for file in batch.files])


def list_project_files(db: Session, project_id: int) -> list[DrawingFileRead]:
    get_project_or_404(db, project_id)
    files = db.scalars(
        select(DrawingFile)
        .where(DrawingFile.project_id == project_id)
        .order_by(DrawingFile.created_at.desc(), DrawingFile.id.desc())
    ).all()
    return [DrawingFileRead.model_validate(file) for file in files]


def project_file_count(db: Session, project_id: int) -> int:
    return db.scalar(
        select(func.count()).select_from(DrawingFile).where(DrawingFile.project_id == project_id)
    ) or 0


def normalize_batch_name(value: str | None) -> str:
    stripped = normalize_text(value)
    if stripped:
        return stripped[:200]
    return f"图纸导入批次 {datetime.now().strftime('%Y%m%d%H%M%S')}"


def normalize_text(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None


def empty_file_type_counts() -> dict[str, int]:
    return {"pdf": 0, "dxf": 0, "dwg": 0, "unsupported": 0}


def classify_upload(file_name: str) -> tuple[str, str | None]:
    file_ext = Path(file_name).suffix.lower()
    source_format = file_storage_service.SUPPORTED_UPLOAD_EXTENSIONS.get(file_ext)
    return file_ext, source_format


def count_items(items: list[ImportItemRead], status_value: str) -> int:
    return sum(1 for item in items if item.status == status_value)


def http_error_code(exc: HTTPException, fallback: str) -> str:
    detail = exc.detail
    if isinstance(detail, dict):
        code = detail.get("error_code")
        if isinstance(code, str) and code:
            return "UNSUPPORTED_FILE_TYPE" if code == "UNSUPPORTED_FORMAT" else code
    return fallback


def http_error_message(exc: HTTPException, fallback: str) -> str:
    detail = exc.detail
    if isinstance(detail, dict):
        message = detail.get("message")
        if isinstance(message, str) and message:
            return message
    if isinstance(detail, str) and detail:
        return detail
    return fallback


def next_actions_for_counts(file_type_counts: dict[str, int]) -> list[str]:
    actions: list[str] = []
    if file_type_counts.get("pdf", 0) > 0:
        actions.append("split_pdf")
    if file_type_counts.get("dwg", 0) > 0:
        actions.append("convert_dwg")
    if file_type_counts.get("dxf", 0) > 0 or file_type_counts.get("dwg", 0) > 0:
        actions.append("run_cad_pipeline")
    if file_type_counts.get("dxf", 0) > 0:
        actions.append("generate_cad_preview")
    return actions


def batch_to_read(
    batch: ImportBatch,
    imported_files: list[tuple[DrawingFile, list[str]]],
    import_items: list[ImportItemRead] | None = None,
    total_selected: int | None = None,
    file_type_counts: dict[str, int] | None = None,
    next_actions: list[str] | None = None,
) -> ImportBatchRead:
    counts = file_type_counts or counts_from_files([file for file, _ in imported_files])
    items = import_items or items_from_files([file for file, _ in imported_files])
    return ImportBatchRead.model_validate(
        {
            "id": batch.id,
            "project_id": batch.project_id,
            "batch_name": batch.batch_name,
            "file_count": batch.file_count,
            "sheet_count": batch.sheet_count,
            "recognized_count": batch.recognized_count,
            "failed_count": batch.failed_count,
            "confirmed_count": batch.confirmed_count,
            "remark": batch.remark,
            "created_at": batch.created_at,
            "updated_at": batch.updated_at,
            "files": [
                ImportedFileRead(
                    id=file.id,
                    original_name=file.original_name,
                    file_ext=file.file_ext,
                    source_format=file.source_format,
                    file_size=file.file_size,
                    file_hash=file.file_hash,
                    page_count=file.page_count,
                    status=file.status,
                    storage_path=file.storage_path,
                    converted_format=file.converted_format,
                    converted_file_path=file.converted_file_path,
                    convert_status=file.convert_status,
                    convert_error_code=file.convert_error_code,
                    convert_error_message=file.convert_error_message,
                    warnings=warnings,
                )
                for file, warnings in imported_files
            ],
            "total_selected": total_selected if total_selected is not None else len(imported_files),
            "imported_count": count_items(items, "imported"),
            "duplicate_count": count_items(items, "duplicate"),
            "unsupported_count": count_items(items, "unsupported"),
            "file_type_counts": counts,
            "items": items,
            "next_actions": next_actions if next_actions is not None else next_actions_for_counts(counts),
        }
    )


def counts_from_files(files: list[DrawingFile]) -> dict[str, int]:
    counts = empty_file_type_counts()
    for file in files:
        if file.source_format in counts:
            counts[file.source_format] += 1
    return counts


def items_from_files(files: list[DrawingFile]) -> list[ImportItemRead]:
    return [
        ImportItemRead(
            file_name=file.original_name,
            file_type=file.source_format,
            status=file.status,
            error_code=file.error_code,
            message=file.error_message,
        )
        for file in files
    ]
