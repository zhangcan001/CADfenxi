import logging
import math
import os
import time
from collections import Counter
from functools import lru_cache
from pathlib import Path
from typing import Any

import ezdxf
import pymupdf as fitz
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.core.config import settings
from backend.models.drawing_file import DrawingFile
from backend.models.drawing_sheet import DrawingSheet
from backend.models.import_batch import ImportBatch
from backend.models.project import Project
from backend.schemas.cad import (
    BatchCadPreviewResult,
    CadPreviewBatchError,
    CadPreviewBatchRequest,
    CadPreviewBatchSummary,
    CadPreviewResult,
)
from backend.services import cad_sheet_service
from backend.services.project_service import project_dir

logger = logging.getLogger(__name__)

MAX_ENTITIES = 6000
MAX_FILE_SIZE = 30 * 1024 * 1024
MAX_DURATION_SECONDS = 20
MAX_CANVAS_WIDTH = 2000
MAX_CANVAS_HEIGHT = 1600
MIN_CANVAS_SIZE = 360
MARGIN = 56
MIN_EXTENT = 1e-6
MAX_EXTENT = 1e12
BATCH_SIZE_WARNING_THRESHOLD = 100
CJK_FONT_ALIAS = "cad_cjk"

SKIPPABLE_ENTITY_TYPES = {
    "HATCH",
    "SPLINE",
    "DIMENSION",
    "LEADER",
    "XREF",
    "IMAGE",
    "ACAD_PROXY_ENTITY",
}

CJK_FONT_CANDIDATES = (
    ("Microsoft YaHei", "msyh.ttc"),
    ("Microsoft YaHei Bold", "msyhbd.ttc"),
    ("SimHei", "simhei.ttf"),
    ("SimSun", "simsun.ttc"),
)


def generate_cad_preview_for_sheet(
    db: Session,
    sheet_id: int,
    *,
    force: bool = True,
    extra_warnings: list[str] | None = None,
) -> CadPreviewResult:
    started_at = time.monotonic()
    result_warnings = list(extra_warnings or [])
    sheet = db.get(DrawingSheet, sheet_id)
    if sheet is None:
        raise preview_http_error(status.HTTP_404_NOT_FOUND, "SHEET_NOT_FOUND", "图纸页不存在。")

    drawing_file = db.get(DrawingFile, sheet.file_id)
    if drawing_file is None:
        return fail_sheet(db, sheet, "CAD_PREVIEW_FILE_NOT_FOUND", "图纸文件不存在。", warnings=result_warnings)
    if not cad_sheet_service.is_dxf_file(drawing_file):
        return fail_sheet(
            db,
            sheet,
            "CAD_PREVIEW_UNSUPPORTED_FORMAT",
            "CAD 图形预览仅支持 DXF 或已转换为 DXF 的 DWG。",
            http_status=status.HTTP_400_BAD_REQUEST,
            warnings=result_warnings,
        )
    if force:
        reset_preview_state(sheet, delete_file=True)

    source_path = dxf_source_path(drawing_file)
    if source_path is None or not source_path.exists():
        return fail_sheet(
            db,
            sheet,
            "CAD_PREVIEW_FILE_NOT_FOUND",
            "CAD 预览源 DXF 文件不存在。",
            http_status=status.HTTP_404_NOT_FOUND,
            warnings=result_warnings,
        )
    if source_path.stat().st_size > MAX_FILE_SIZE:
        return fail_sheet(
            db,
            sheet,
            "CAD_PREVIEW_TIMEOUT",
            "CAD 文件较大，轻量预览暂不处理。",
            duration_seconds=elapsed(started_at),
            warnings=result_warnings,
        )

    sheet.cad_preview_status = "pending"
    sheet.cad_preview_error_code = None
    sheet.cad_preview_error_message = None
    db.flush()

    try:
        document = ezdxf.readfile(source_path)
    except (OSError, ezdxf.DXFError) as exc:
        logger.warning("CAD preview DXF open failed sheet_id=%s path=%s: %s", sheet.id, source_path, exc)
        return fail_sheet(
            db,
            sheet,
            "CAD_PREVIEW_DXF_OPEN_FAILED",
            "DXF 文件无法打开。",
            duration_seconds=elapsed(started_at),
            warnings=result_warnings,
        )

    try:
        primitives, warnings, skipped_entity_count = collect_primitives(document, started_at)
        warnings = merge_warnings(result_warnings, warnings)
        if not primitives:
            error_code = "CAD_PREVIEW_NO_RENDERABLE_ENTITY" if skipped_entity_count else "CAD_PREVIEW_EMPTY_DRAWING"
            return fail_sheet_with_warnings(
                db,
                sheet,
                error_code,
                "DXF 中未找到可预览图形。",
                warnings,
                duration_seconds=elapsed(started_at),
                skipped_entity_count=skipped_entity_count,
            )
        output_path = cad_preview_output_path(sheet.project_id, sheet.id)
        render_png(primitives, output_path, warnings, started_at)
        relative = relative_to_root(output_path)
        sheet.cad_preview_path = relative
        sheet.cad_preview_status = "success"
        sheet.cad_preview_error_code = None
        sheet.cad_preview_error_message = None
        db.commit()
        db.refresh(sheet)
        return CadPreviewResult(
            file_id=drawing_file.id,
            sheet_id=sheet.id,
            file_name=drawing_file.original_name,
            status="success",
            cad_preview_path=relative,
            preview_url=f"/api/sheets/{sheet.id}/cad-preview-image",
            warnings=warnings,
            duration_seconds=elapsed(started_at),
            skipped_entity_count=skipped_entity_count,
        )
    except PreviewFailure as exc:
        return fail_sheet_with_warnings(
            db,
            sheet,
            exc.error_code,
            exc.message,
            merge_warnings(result_warnings, exc.warnings),
            duration_seconds=elapsed(started_at),
            skipped_entity_count=exc.skipped_entity_count,
        )
    except (OSError, RuntimeError, ValueError, ezdxf.DXFError) as exc:
        logger.exception("CAD preview render failed sheet_id=%s", sheet.id)
        return fail_sheet(
            db,
            sheet,
            "CAD_PREVIEW_RENDER_FAILED",
            str(exc)[:500] or "CAD 图形预览生成失败。",
            duration_seconds=elapsed(started_at),
            warnings=result_warnings,
        )


def generate_cad_preview_for_batch(
    db: Session,
    batch_id: int,
    payload: CadPreviewBatchRequest | None = None,
) -> BatchCadPreviewResult:
    payload = payload or CadPreviewBatchRequest()
    batch = db.get(ImportBatch, batch_id)
    if batch is None:
        raise preview_http_error(status.HTTP_404_NOT_FOUND, "IMPORT_BATCH_NOT_FOUND", "导入批次不存在。")
    return generate_cad_previews_for_rows(
        db,
        cad_sheet_rows_for_batch(db, batch_id),
        payload,
        scope="batch",
        project_id=batch.project_id,
        batch_id=batch_id,
    )


def generate_cad_preview_for_project(
    db: Session,
    project_id: int,
    payload: CadPreviewBatchRequest | None = None,
) -> BatchCadPreviewResult:
    payload = payload or CadPreviewBatchRequest()
    project = db.get(Project, project_id)
    if project is None:
        raise preview_http_error(status.HTTP_404_NOT_FOUND, "PROJECT_NOT_FOUND", "项目不存在。")
    return generate_cad_previews_for_rows(
        db,
        cad_sheet_rows_for_project(db, project_id),
        payload,
        scope="project",
        project_id=project_id,
        batch_id=None,
    )


def generate_cad_previews_for_rows(
    db: Session,
    rows: list[tuple[DrawingSheet, DrawingFile]],
    payload: CadPreviewBatchRequest,
    *,
    scope: str,
    project_id: int | None,
    batch_id: int | None,
) -> BatchCadPreviewResult:
    started_at = time.monotonic()
    cad_sheets = [(sheet, drawing_file) for sheet, drawing_file in rows if cad_sheet_service.is_dxf_file(drawing_file)]

    items: list[CadPreviewResult] = []
    errors: list[CadPreviewBatchError] = []
    batch_warnings: list[str] = []
    success_count = 0
    failed_count = 0
    skipped_count = 0
    warning_count = 0

    if len(cad_sheets) > BATCH_SIZE_WARNING_THRESHOLD:
        batch_warnings.append(f"CAD_PREVIEW_BATCH_SIZE_WARNING:{len(cad_sheets)}")

    for sheet, drawing_file in cad_sheets:
        missing_preview_warning = preview_cache_warning(sheet)
        if payload.force:
            reset_preview_state(sheet, delete_file=True)

        if payload.skip_completed and not payload.force and is_preview_cache_complete(sheet):
            skipped_count += 1
            items.append(
                CadPreviewResult(
                    file_id=drawing_file.id,
                    sheet_id=sheet.id,
                    file_name=drawing_file.original_name,
                    status="skipped",
                    cad_preview_path=sheet.cad_preview_path,
                    preview_url=f"/api/sheets/{sheet.id}/cad-preview-image",
                )
            )
            continue

        result_warnings = [missing_preview_warning] if missing_preview_warning else []
        try:
            result = generate_cad_preview_for_sheet(
                db,
                sheet.id,
                force=payload.force,
                extra_warnings=result_warnings,
            )
        except HTTPException as exc:
            db.rollback()
            detail = exc.detail if isinstance(exc.detail, dict) else {}
            result = CadPreviewResult(
                file_id=drawing_file.id,
                sheet_id=sheet.id,
                file_name=drawing_file.original_name,
                status="failed",
                warnings=result_warnings,
                error_code=detail.get("error_code", "CAD_PREVIEW_RENDER_FAILED"),
                error_message=detail.get("message", "CAD 图形预览生成失败。"),
            )
        except Exception as exc:
            logger.exception("Batch CAD preview failed file_id=%s sheet_id=%s", drawing_file.id, sheet.id)
            db.rollback()
            result = CadPreviewResult(
                file_id=drawing_file.id,
                sheet_id=sheet.id,
                file_name=drawing_file.original_name,
                status="failed",
                warnings=result_warnings,
                error_code="CAD_PREVIEW_RENDER_FAILED",
                error_message=str(exc)[:500] or "CAD 图形预览生成失败。",
            )

        result.file_id = result.file_id or drawing_file.id
        result.file_name = result.file_name or drawing_file.original_name
        if result.status == "success":
            success_count += 1
        elif result.status == "skipped":
            skipped_count += 1
        else:
            failed_count += 1
            errors.append(
                CadPreviewBatchError(
                    sheet_id=sheet.id,
                    file_name=drawing_file.original_name,
                    error_code=result.error_code or "CAD_PREVIEW_RENDER_FAILED",
                    message=result.error_message or "CAD 图形预览生成失败。",
                )
            )
        warning_count += len(result.warnings)
        items.append(result)
        if result.status != "success" and not payload.continue_on_error:
            break

    duration_seconds = elapsed(started_at)
    status_value = batch_status(success_count, failed_count, skipped_count, len(cad_sheets), payload.continue_on_error)
    summary = CadPreviewBatchSummary(
        total_count=len(cad_sheets),
        success_count=success_count,
        failed_count=failed_count,
        skipped_count=skipped_count,
        warning_count=warning_count + len(batch_warnings),
        duration_seconds=duration_seconds,
    )
    return BatchCadPreviewResult(
        scope=scope,
        project_id=project_id,
        batch_id=batch_id,
        status=status_value,
        summary=summary,
        total_count=summary.total_count,
        success_count=success_count,
        failed_count=failed_count,
        skipped_count=skipped_count,
        warning_count=summary.warning_count,
        duration_seconds=duration_seconds,
        items=items,
        errors=errors,
        warnings=batch_warnings,
    )


def cad_sheet_rows_for_batch(db: Session, batch_id: int) -> list[tuple[DrawingSheet, DrawingFile]]:
    rows = db.execute(
        select(DrawingSheet, DrawingFile)
        .join(DrawingFile, DrawingFile.id == DrawingSheet.file_id)
        .where(DrawingSheet.batch_id == batch_id)
        .order_by(DrawingSheet.id.asc())
    ).all()
    return [(sheet, drawing_file) for sheet, drawing_file in rows]


def cad_sheet_rows_for_project(db: Session, project_id: int) -> list[tuple[DrawingSheet, DrawingFile]]:
    rows = db.execute(
        select(DrawingSheet, DrawingFile)
        .join(DrawingFile, DrawingFile.id == DrawingSheet.file_id)
        .where(DrawingSheet.project_id == project_id)
        .order_by(DrawingSheet.id.asc())
    ).all()
    return [(sheet, drawing_file) for sheet, drawing_file in rows]


def batch_status(
    success_count: int,
    failed_count: int,
    skipped_count: int,
    total_count: int,
    continue_on_error: bool,
) -> str:
    if total_count == 0 or skipped_count == total_count:
        return "skipped"
    if failed_count:
        if continue_on_error or success_count or skipped_count:
            return "completed_with_errors"
        return "failed"
    return "success"


def is_preview_cache_complete(sheet: DrawingSheet) -> bool:
    return (
        sheet.cad_preview_status == "success"
        and bool(sheet.cad_preview_path)
        and stored_path_exists(sheet.cad_preview_path)
    )


def preview_cache_warning(sheet: DrawingSheet) -> str | None:
    if sheet.cad_preview_path and not stored_path_exists(sheet.cad_preview_path):
        return "CAD_PREVIEW_FILE_MISSING_REGENERATED"
    return None


def stored_path_exists(stored_path: str) -> bool:
    path = Path(stored_path)
    if not path.is_absolute():
        path = settings.root_dir / stored_path
    return path.exists() and path.is_file()


def reset_preview_state(sheet: DrawingSheet, *, delete_file: bool = False) -> None:
    if delete_file and sheet.cad_preview_path:
        preview_path = settings.root_dir / sheet.cad_preview_path
        try:
            preview_path.unlink(missing_ok=True)
        except OSError as exc:
            logger.warning("Failed deleting old CAD preview sheet_id=%s path=%s: %s", sheet.id, preview_path, exc)
        sheet.cad_preview_path = None
    sheet.cad_preview_status = "pending"
    sheet.cad_preview_error_code = None
    sheet.cad_preview_error_message = None


def cad_preview_image_path(db: Session, sheet_id: int) -> Path:
    sheet = db.get(DrawingSheet, sheet_id)
    if sheet is None:
        raise preview_http_error(status.HTTP_404_NOT_FOUND, "SHEET_NOT_FOUND", "图纸页不存在。")
    if not sheet.cad_preview_path:
        raise preview_http_error(status.HTTP_404_NOT_FOUND, "CAD_PREVIEW_FILE_NOT_FOUND", "CAD 预览图不存在。")
    path = settings.root_dir / sheet.cad_preview_path
    if not path.exists() or not path.is_file():
        sheet.cad_preview_status = "failed"
        sheet.cad_preview_error_code = "CAD_PREVIEW_FILE_MISSING"
        sheet.cad_preview_error_message = "CAD 预览图文件缺失，请重新生成。"
        db.commit()
        raise preview_http_error(status.HTTP_404_NOT_FOUND, "CAD_PREVIEW_FILE_MISSING", "CAD 预览图文件缺失，请重新生成。")
    return path


def dxf_source_path(drawing_file: DrawingFile) -> Path | None:
    if drawing_file.source_format == "dwg":
        return settings.root_dir / drawing_file.converted_file_path if drawing_file.converted_file_path else None
    return settings.root_dir / drawing_file.storage_path


def cad_preview_output_path(project_id: int, sheet_id: int) -> Path:
    directory = project_dir(project_id) / "cad" / "previews"
    directory.mkdir(parents=True, exist_ok=True)
    return directory / f"sheet_{sheet_id}_cad_preview.png"


def collect_primitives(
    document: Any,
    started_at: float,
) -> tuple[list[dict[str, Any]], list[str], int]:
    primitives: list[dict[str, Any]] = []
    warnings: list[str] = []
    skipped_types: Counter[str] = Counter()
    invalid_extent_count = 0
    modelspace = document.modelspace()
    for index, entity in enumerate(modelspace):
        check_timeout(started_at)
        if index >= MAX_ENTITIES:
            warnings.append("CAD_PREVIEW_ENTITY_LIMIT")
            break
        entity_type = entity.dxftype()
        try:
            if entity_type == "LINE":
                primitives.append({"type": "line", "points": [point2(entity.dxf.start), point2(entity.dxf.end)]})
            elif entity_type == "LWPOLYLINE":
                points = [(float(point[0]), float(point[1])) for point in entity.get_points()]
                add_polyline(primitives, points, bool(entity.closed))
            elif entity_type == "POLYLINE":
                points = [point2(vertex.dxf.location) for vertex in entity.vertices]
                add_polyline(primitives, points, bool(entity.is_closed))
            elif entity_type == "CIRCLE":
                center = point2(entity.dxf.center)
                primitives.append({"type": "circle", "center": center, "radius": abs(float(entity.dxf.radius))})
            elif entity_type == "ARC":
                primitives.extend(arc_segments(point2(entity.dxf.center), float(entity.dxf.radius), float(entity.dxf.start_angle), float(entity.dxf.end_angle)))
            elif entity_type in {"TEXT", "MTEXT"}:
                text = entity.plain_text() if hasattr(entity, "plain_text") else str(entity.dxf.text)
                insert = point2(entity.dxf.insert)
                if text.strip():
                    primitives.append({"type": "text", "point": insert, "text": text.strip()[:80]})
            elif entity_type == "INSERT":
                skipped_types[entity_type] += 1
            elif entity_type in SKIPPABLE_ENTITY_TYPES or entity_type.startswith("ACAD_PROXY"):
                skipped_types[entity_type] += 1
            else:
                skipped_types[entity_type] += 1
        except ValueError:
            invalid_extent_count += 1
        except (AttributeError, TypeError, ezdxf.DXFError):
            skipped_types[entity_type] += 1
    warnings.extend(skipped_warnings(skipped_types))
    if invalid_extent_count:
        warnings.append(f"CAD_PREVIEW_INVALID_EXTENTS_SKIPPED:{invalid_extent_count}")
    if not primitives and invalid_extent_count:
        raise PreviewFailure(
            "CAD_PREVIEW_INVALID_EXTENTS",
            "CAD 图形范围异常。",
            warnings=sorted(set(warnings)),
            skipped_entity_count=sum(skipped_types.values()),
        )
    if contains_non_ascii_text(primitives) and not resolve_cjk_font_file():
        warnings.append("CAD_PREVIEW_FONT_FALLBACK")
    return primitives, sorted(set(warnings)), sum(skipped_types.values())


def add_polyline(primitives: list[dict[str, Any]], points: list[tuple[float, float]], closed: bool) -> None:
    if len(points) < 2:
        return
    for start, end in zip(points, points[1:]):
        primitives.append({"type": "line", "points": [start, end]})
    if closed:
        primitives.append({"type": "line", "points": [points[-1], points[0]]})


def arc_segments(
    center: tuple[float, float],
    radius: float,
    start_angle: float,
    end_angle: float,
    segment_count: int = 48,
) -> list[dict[str, Any]]:
    if radius <= 0:
        return []
    if end_angle < start_angle:
        end_angle += 360
    steps = max(6, min(segment_count, int(abs(end_angle - start_angle) / 8) + 1))
    points = []
    for index in range(steps + 1):
        angle = math.radians(start_angle + (end_angle - start_angle) * index / steps)
        points.append((center[0] + math.cos(angle) * radius, center[1] + math.sin(angle) * radius))
    primitives: list[dict[str, Any]] = []
    add_polyline(primitives, points, False)
    return primitives


def render_png(
    primitives: list[dict[str, Any]],
    output_path: Path,
    warnings: list[str],
    started_at: float,
) -> None:
    bounds = primitive_bounds(primitives)
    if bounds is None:
        raise PreviewFailure("CAD_PREVIEW_EMPTY_DRAWING", "DXF 中未找到可预览图形。")
    min_x, min_y, max_x, max_y = normalized_bounds(bounds)
    width = max_x - min_x
    height = max_y - min_y
    target_width, target_height = target_canvas_size(width, height)
    scale = min((target_width - 2 * MARGIN) / width, (target_height - 2 * MARGIN) / height)

    def map_point(point: tuple[float, float]) -> fitz.Point:
        safe_point(point)
        x = (point[0] - min_x) * scale + MARGIN
        y = target_height - ((point[1] - min_y) * scale + MARGIN)
        return fitz.Point(x, y)

    document = fitz.open()
    page = document.new_page(width=target_width, height=target_height)
    shape = page.new_shape()
    stroke = (0.0, 0.0, 0.0)
    line_width = max(0.8, min(1.8, scale * 0.02))
    for item in primitives:
        check_timeout(started_at)
        if item["type"] == "line":
            start, end = item["points"]
            shape.draw_line(map_point(start), map_point(end))
        elif item["type"] == "circle":
            center = map_point(item["center"])
            radius = max(item["radius"] * scale, 0.5)
            shape.draw_circle(center, radius)
    shape.finish(color=stroke, width=line_width)
    shape.commit()
    fontname, fontfile = preview_font(warnings)
    for item in primitives:
        check_timeout(started_at)
        if item["type"] == "text":
            insert_preview_text(
                page,
                map_point(item["point"]),
                item["text"],
                max(7, min(16, scale * 1.4)),
                fontname,
                fontfile,
                warnings,
            )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    pixmap = page.get_pixmap(matrix=fitz.Matrix(1, 1), alpha=False)
    pixmap.save(output_path)
    document.close()


def primitive_bounds(primitives: list[dict[str, Any]]) -> tuple[float, float, float, float] | None:
    xs: list[float] = []
    ys: list[float] = []
    for item in primitives:
        if item["type"] == "line":
            for point in item["points"]:
                append_finite(xs, ys, point)
        elif item["type"] == "circle":
            x, y = item["center"]
            radius = item["radius"]
            for point in [(x - radius, y - radius), (x + radius, y + radius)]:
                append_finite(xs, ys, point)
        elif item["type"] == "text":
            append_finite(xs, ys, item["point"])
    if not xs or not ys:
        return None
    return min(xs), min(ys), max(xs), max(ys)


def point2(value: Any) -> tuple[float, float]:
    point = (float(value[0]), float(value[1]))
    if not math.isfinite(point[0]) or not math.isfinite(point[1]):
        raise ValueError("invalid point")
    return point


def append_finite(xs: list[float], ys: list[float], point: tuple[float, float]) -> None:
    if math.isfinite(point[0]) and math.isfinite(point[1]):
        xs.append(point[0])
        ys.append(point[1])


def normalized_bounds(bounds: tuple[float, float, float, float]) -> tuple[float, float, float, float]:
    min_x, min_y, max_x, max_y = bounds
    values = [min_x, min_y, max_x, max_y]
    if not all(math.isfinite(value) for value in values):
        raise PreviewFailure("CAD_PREVIEW_INVALID_EXTENTS", "CAD 图形范围无效。")
    width = max_x - min_x
    height = max_y - min_y
    if width < 0 or height < 0 or max(abs(value) for value in values) > MAX_EXTENT:
        raise PreviewFailure("CAD_PREVIEW_INVALID_EXTENTS", "CAD 图形范围异常。")
    if width < 1:
        center = (min_x + max_x) / 2
        min_x = center - 0.5
        max_x = center + 0.5
    if height < 1:
        center = (min_y + max_y) / 2
        min_y = center - 0.5
        max_y = center + 0.5
    pad_x = max((max_x - min_x) * 0.03, 0.5)
    pad_y = max((max_y - min_y) * 0.03, 0.5)
    return min_x - pad_x, min_y - pad_y, max_x + pad_x, max_y + pad_y


def target_canvas_size(width: float, height: float) -> tuple[int, int]:
    aspect = max(width / max(height, MIN_EXTENT), MIN_EXTENT)
    if aspect >= 1:
        canvas_width = MAX_CANVAS_WIDTH
        canvas_height = int(MAX_CANVAS_WIDTH / aspect)
    else:
        canvas_height = MAX_CANVAS_HEIGHT
        canvas_width = int(MAX_CANVAS_HEIGHT * aspect)
    return (
        max(MIN_CANVAS_SIZE, min(MAX_CANVAS_WIDTH, canvas_width)),
        max(MIN_CANVAS_SIZE, min(MAX_CANVAS_HEIGHT, canvas_height)),
    )


def safe_point(point: tuple[float, float]) -> None:
    if not math.isfinite(point[0]) or not math.isfinite(point[1]):
        raise ValueError("invalid point")
    if abs(point[0]) > MAX_EXTENT or abs(point[1]) > MAX_EXTENT:
        raise ValueError("point out of supported range")


def skipped_warnings(skipped_types: Counter[str]) -> list[str]:
    return [
        f"CAD_PREVIEW_ENTITY_SKIPPED:{entity_type}:{count}"
        for entity_type, count in sorted(skipped_types.items())
    ]


def contains_non_ascii_text(primitives: list[dict[str, Any]]) -> bool:
    return any(
        item.get("type") == "text" and any(ord(char) > 127 for char in item.get("text", ""))
        for item in primitives
    )


def preview_font(warnings: list[str]) -> tuple[str, str | None]:
    # Prefer common Windows CJK fonts for real local drawings, but never fail preview
    # rendering just because the portable runtime cannot find a Chinese font.
    if "CAD_PREVIEW_FONT_FALLBACK" not in warnings:
        font_file = resolve_cjk_font_file()
        if font_file is not None:
            return CJK_FONT_ALIAS, str(font_file)
    return "helv", None


def insert_preview_text(
    page: fitz.Page,
    point: fitz.Point,
    text: str,
    fontsize: float,
    fontname: str,
    fontfile: str | None,
    warnings: list[str],
) -> None:
    try:
        page.insert_text(
            point,
            text,
            fontsize=fontsize,
            fontname=fontname,
            fontfile=fontfile,
            color=(0.05, 0.05, 0.05),
        )
    except RuntimeError:
        if fontfile is None:
            raise
        if "CAD_PREVIEW_FONT_FALLBACK" not in warnings:
            warnings.append("CAD_PREVIEW_FONT_FALLBACK")
        page.insert_text(
            point,
            text,
            fontsize=fontsize,
            fontname="helv",
            color=(0.05, 0.05, 0.05),
        )


@lru_cache(maxsize=1)
def resolve_cjk_font_file() -> Path | None:
    search_dirs = []
    windir = os.environ.get("WINDIR")
    if windir:
        search_dirs.append(Path(windir) / "Fonts")
    search_dirs.append(Path("C:/Windows/Fonts"))
    for _font_name, file_name in CJK_FONT_CANDIDATES:
        for directory in search_dirs:
            candidate = directory / file_name
            if candidate.exists() and candidate.is_file():
                return candidate
    return None


def fail_sheet(
    db: Session,
    sheet: DrawingSheet,
    error_code: str,
    message: str,
    http_status: int | None = None,
    duration_seconds: float = 0,
    skipped_entity_count: int = 0,
    warnings: list[str] | None = None,
) -> CadPreviewResult:
    sheet.cad_preview_status = "failed"
    sheet.cad_preview_error_code = error_code
    sheet.cad_preview_error_message = message
    db.commit()
    if http_status is not None:
        raise preview_http_error(http_status, error_code, message)
    return CadPreviewResult(
        file_id=sheet.file_id,
        sheet_id=sheet.id,
        status="failed",
        warnings=warnings or [],
        duration_seconds=duration_seconds,
        skipped_entity_count=skipped_entity_count,
        error_code=error_code,
        error_message=message,
    )


def fail_sheet_with_warnings(
    db: Session,
    sheet: DrawingSheet,
    error_code: str,
    message: str,
    warnings: list[str],
    duration_seconds: float = 0,
    skipped_entity_count: int = 0,
) -> CadPreviewResult:
    return fail_sheet(
        db,
        sheet,
        error_code,
        message,
        duration_seconds=duration_seconds,
        skipped_entity_count=skipped_entity_count,
        warnings=warnings,
    )


def relative_to_root(path: Path) -> str:
    return path.relative_to(settings.root_dir).as_posix()


def merge_warnings(left: list[str], right: list[str]) -> list[str]:
    return sorted(set(left + right))


def preview_http_error(status_code: int, error_code: str, message: str) -> HTTPException:
    return HTTPException(status_code=status_code, detail={"error_code": error_code, "message": message})


def check_timeout(started_at: float) -> None:
    if elapsed(started_at) > MAX_DURATION_SECONDS:
        raise PreviewFailure("CAD_PREVIEW_TIMEOUT", "CAD 图形预览生成超时。")


def elapsed(started_at: float) -> float:
    return round(max(time.monotonic() - started_at, 0), 3)


class PreviewFailure(Exception):
    def __init__(
        self,
        error_code: str,
        message: str,
        warnings: list[str] | None = None,
        skipped_entity_count: int = 0,
    ):
        super().__init__(message)
        self.error_code = error_code
        self.message = message
        self.warnings = warnings or []
        self.skipped_entity_count = skipped_entity_count
