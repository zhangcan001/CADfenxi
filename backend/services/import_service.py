from datetime import datetime
import logging
from pathlib import Path

from fastapi import HTTPException, UploadFile, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from backend.models.drawing_file import DrawingFile
from backend.models.import_batch import ImportBatch
from backend.schemas.drawing_file import DrawingFileRead, ImportedFileRead
from backend.schemas.import_batch import ImportBatchRead
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
    get_project_or_404(db, project_id)
    if not files:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="上传文件不能为空",
        )

    upload_formats = [file_storage_service.validate_drawing_upload(file) for file in files]

    normalized_batch_name = normalize_batch_name(batch_name)
    normalized_remark = normalize_text(remark)
    saved_paths: list[Path] = []

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

        for upload, (file_ext, source_format) in zip(files, upload_formats, strict=True):
            saved_path, file_size, file_hash = file_storage_service.save_drawing_file(
                project_id, upload, file_ext
            )
            saved_paths.append(saved_path)

            warnings = []
            if file_hash in existing_hashes:
                warnings.append("duplicate_file")
            existing_hashes.add(file_hash)

            drawing_file = DrawingFile(
                project_id=project_id,
                batch_id=batch.id,
                original_name=upload.filename or f"未命名{file_ext}",
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

        batch.file_count = len(imported_files)
        db.flush()
        db.refresh(batch)
        for drawing_file, _ in imported_files:
            db.refresh(drawing_file)
        db.commit()

        return batch_to_read(batch, imported_files)
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


def batch_to_read(
    batch: ImportBatch,
    imported_files: list[tuple[DrawingFile, list[str]]],
) -> ImportBatchRead:
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
        }
    )
