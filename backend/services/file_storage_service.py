import hashlib
import re
import shutil
from pathlib import Path
from uuid import uuid4

from fastapi import HTTPException, UploadFile, status

from backend.core.config import settings

SAFE_NAME_PATTERN = re.compile(r"[^A-Za-z0-9._-]+")
SUPPORTED_UPLOAD_EXTENSIONS = {".pdf": "pdf", ".dxf": "dxf", ".dwg": "dwg"}


def project_original_dir(project_id: int) -> Path:
    return settings.projects_dir / f"project_{project_id}" / "original"


def project_converted_dir(project_id: int) -> Path:
    return settings.projects_dir / f"project_{project_id}" / "converted"


def project_cad_log_dir(project_id: int) -> Path:
    return settings.projects_dir / f"project_{project_id}" / "cad" / "logs"


def safe_filename(filename: str, file_ext: str = ".pdf") -> str:
    stem = Path(filename).stem
    safe_stem = SAFE_NAME_PATTERN.sub("_", stem).strip("._-")
    if not safe_stem:
        safe_stem = "drawing"
    return f"{safe_stem[:80]}{file_ext}"


def get_upload_source_format(file: UploadFile) -> tuple[str, str]:
    original_name = file.filename or ""
    file_ext = Path(original_name).suffix.lower()
    source_format = SUPPORTED_UPLOAD_EXTENSIONS.get(file_ext)
    if source_format is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error_code": "UNSUPPORTED_FORMAT",
                "message": f"仅支持 PDF、DXF 或 DWG 文件：{original_name or '未命名文件'}",
            },
        )
    return file_ext, source_format


def validate_pdf_upload(file: UploadFile) -> None:
    file_ext, _ = get_upload_source_format(file)
    if file_ext != ".pdf":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error_code": "UNSUPPORTED_FORMAT",
                "message": f"仅支持 PDF 文件：{file.filename or '未命名文件'}",
            },
        )


def validate_drawing_upload(file: UploadFile) -> tuple[str, str]:
    return get_upload_source_format(file)


def save_drawing_file(project_id: int, file: UploadFile, file_ext: str) -> tuple[Path, int, str]:
    directory = project_original_dir(project_id)
    directory.mkdir(parents=True, exist_ok=True)

    target = directory / f"{uuid4().hex}_{safe_filename(file.filename or f'drawing{file_ext}', file_ext)}"
    digest = hashlib.sha256()
    size = 0

    try:
        with target.open("wb") as output:
            while chunk := file.file.read(1024 * 1024):
                size += len(chunk)
                digest.update(chunk)
                output.write(chunk)
    except OSError as exc:
        target.unlink(missing_ok=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error_code": "FILE_NOT_FOUND", "message": "文件保存失败"},
        ) from exc
    finally:
        file.file.seek(0)

    return target, size, digest.hexdigest()


def save_pdf_file(project_id: int, file: UploadFile) -> tuple[Path, int, str]:
    return save_drawing_file(project_id, file, ".pdf")


def remove_saved_files(paths: list[Path]) -> None:
    for path in paths:
        path.unlink(missing_ok=True)


def remove_original_dir_if_empty(project_id: int) -> None:
    directory = project_original_dir(project_id)
    if directory.exists():
        try:
            directory.rmdir()
        except OSError:
            pass
