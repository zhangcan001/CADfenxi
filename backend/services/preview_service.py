from pathlib import Path

import pymupdf as fitz

from backend.core.config import settings


def preview_dir(project_id: int) -> Path:
    return settings.projects_dir / f"project_{project_id}" / "previews"


def thumbnail_dir(project_id: int) -> Path:
    return settings.projects_dir / f"project_{project_id}" / "thumbnails"


def ensure_preview_dirs(project_id: int) -> tuple[Path, Path]:
    previews = preview_dir(project_id)
    thumbnails = thumbnail_dir(project_id)
    previews.mkdir(parents=True, exist_ok=True)
    thumbnails.mkdir(parents=True, exist_ok=True)
    return previews, thumbnails


def render_page(
    page: fitz.Page,
    project_id: int,
    sheet_id: int,
) -> tuple[str, str]:
    previews, thumbnails = ensure_preview_dirs(project_id)
    preview_path = previews / f"sheet_{sheet_id}.png"
    thumbnail_path = thumbnails / f"sheet_{sheet_id}.jpg"

    preview_pixmap = page.get_pixmap(matrix=_matrix_for_width(page, settings.preview_max_width), alpha=False)
    preview_pixmap.save(preview_path)

    thumbnail_pixmap = page.get_pixmap(
        matrix=_matrix_for_width(page, settings.thumbnail_max_width), alpha=False
    )
    thumbnail_pixmap.save(thumbnail_path)

    return (
        str(preview_path.relative_to(settings.root_dir)),
        str(thumbnail_path.relative_to(settings.root_dir)),
    )


def _matrix_for_width(page: fitz.Page, max_width: int) -> fitz.Matrix:
    width = max(page.rect.width, 1)
    zoom = min(max_width / width, 2.0)
    zoom = max(zoom, 0.2)
    return fitz.Matrix(zoom, zoom)
