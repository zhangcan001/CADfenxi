"""DXF 表格抽取算法层（纯函数，无 DB 依赖）。

提供两条互补的抽取路径：
1. extract_acad_tables(document)         — 读 ACAD_TABLE 实体；ezdxf 直接给出 cells
2. extract_text_cluster_tables(cad_json) — 把 TEXT/MTEXT 按坐标聚类成伪表格

输出 dict 列表，每项含：
    extraction_method, header, rows, row_count, col_count, layer, bbox
"""
from __future__ import annotations

import logging
from statistics import median
from typing import Any, Iterable

logger = logging.getLogger(__name__)


MIN_ROWS = 3
MIN_COLS = 2
MIN_TOTAL_TEXTS = 6
MIN_NON_EMPTY_CELLS = 6
MIN_HEADER_NON_EMPTY_RATIO = 0.5

ROW_Y_THRESHOLD_FACTOR = 1.5    # 同行：y 差 < median_h * 该系数
ROW_GAP_MAX_FACTOR = 4.0        # 跨行：y 差 > median_h * 该系数 → 不在同表
COL_X_THRESHOLD_FACTOR = 0.6    # 同列聚类阈值（按文字平均宽度）

MAX_ROWS = 200
MAX_COLS = 30


def extract_acad_tables(document: Any) -> list[dict]:
    """读 modelspace 内全部 ACAD_TABLE 实体的 cell 内容。

    ezdxf 1.x 文档化 API：from ezdxf.entities.acad_table import read_acad_table_content
    """
    try:
        from ezdxf.entities.acad_table import read_acad_table_content
    except ImportError:
        logger.debug("ezdxf.entities.acad_table.read_acad_table_content 不可用，跳过 ACAD_TABLE 抽取")
        return []

    out: list[dict] = []
    try:
        modelspace = document.modelspace()
    except (AttributeError, RuntimeError) as exc:
        logger.warning("ACAD_TABLE 抽取无法访问 modelspace: %s", exc)
        return []

    try:
        candidates = list(modelspace.query("ACAD_TABLE"))
    except (AttributeError, TypeError) as exc:
        logger.warning("ACAD_TABLE 查询失败: %s", exc)
        return []

    for entity in candidates:
        try:
            content = read_acad_table_content(entity)
        except Exception as exc:  # noqa: BLE001 — 第三方 API 异常多样
            logger.warning("read_acad_table_content 失败: %s", exc)
            continue
        if not content or len(content) < 2:
            continue
        header = [_clean(cell) for cell in content[0]]
        rows = [[_clean(cell) for cell in row] for row in content[1:]]
        if not _looks_like_table(header, rows):
            continue
        rows, warnings = _enforce_size_limits(rows, header)
        confidence = _table_confidence(header, rows, "acad_table")
        if confidence < 70:
            warnings.append("LOW_CONFIDENCE_TABLE")
        out.append(
            {
                "extraction_method": "acad_table",
                "header": header,
                "rows": rows,
                "row_count": len(rows),
                "col_count": len(header),
                "confidence": confidence,
                "layer": _safe_layer(entity),
                "bbox": _safe_bbox(entity),
                "warnings": warnings,
            }
        )
    return out


def extract_text_cluster_tables(
    cad_json: dict, *, exclude_bbox: list[float] | None = None
) -> list[dict]:
    """从 cad_json modelspace 的 texts+mtexts 聚类伪表格。

    步骤：
    1. 收 (text, x, y, h)；排除 exclude_bbox 内（避开标题栏）
    2. 按 y 降序聚类成行，阈值 = median_h * ROW_Y_THRESHOLD_FACTOR
    3. 连续行扫描：列数差 ≤ 1 且 y 间距 < median_h * ROW_GAP_MAX_FACTOR 视为同一候选表
    4. 候选表 row ≥ MIN_ROWS、col ≥ MIN_COLS 才输出
    5. 跨行做 x 聚类生成列网格，cell 映射到最近列
    """
    items = _collect_text_items(cad_json, exclude_bbox)
    if len(items) < MIN_TOTAL_TEXTS:
        return []

    heights = [item["h"] for item in items if item["h"] > 0]
    if not heights:
        return []
    median_h = median(heights)
    if median_h <= 0:
        return []

    rows = _group_into_rows(items, median_h * ROW_Y_THRESHOLD_FACTOR)
    if len(rows) < MIN_ROWS:
        return []

    tables: list[dict] = []
    index = 0
    while index < len(rows):
        run = _find_table_run(rows, index, median_h * ROW_GAP_MAX_FACTOR)
        if run is None:
            index += 1
            continue
        table = _build_table_from_run(run, median_h)
        if table is not None:
            tables.append(table)
        index += len(run)
    return tables


# ---------- 私有工具函数 ----------


def _collect_text_items(cad_json: dict, exclude_bbox: list[float] | None) -> list[dict]:
    items: list[dict] = []
    modelspace = next(
        (space for space in cad_json.get("spaces", []) if space.get("space") == "modelspace"),
        None,
    )
    if not modelspace:
        return items

    for text in modelspace.get("texts", []):
        item = _text_to_item(text, text.get("height", 0))
        if item and not _in_bbox(item["x"], item["y"], exclude_bbox):
            items.append(item)

    for mtext in modelspace.get("mtexts", []):
        for split_record in _split_mtext_lines(mtext):
            item = _text_to_item(split_record, split_record.get("char_height", 0))
            if item and not _in_bbox(item["x"], item["y"], exclude_bbox):
                items.append(item)

    return items


def _split_mtext_lines(mtext: dict) -> list[dict]:
    """把多行 MTEXT 拆成多个单行记录，y 坐标按 char_height 递减。

    解决：表格聚类按 y 聚类时，单条 MTEXT 含多行会被当成 1 行，导致丢字。
    """
    clean = (mtext.get("clean_text") or "")
    if "\n" not in clean:
        return [mtext]
    insert = mtext.get("insert") or [0, 0, 0]
    try:
        x = float(insert[0])
        y0 = float(insert[1])
    except (TypeError, ValueError, IndexError):
        return [mtext]
    try:
        char_h = float(mtext.get("char_height") or 0) or 2.5
    except (TypeError, ValueError):
        char_h = 2.5
    lines = [line.strip() for line in clean.split("\n") if line.strip()]
    if len(lines) <= 1:
        return [mtext]
    records: list[dict] = []
    for index, line in enumerate(lines):
        records.append(
            {
                **mtext,
                "clean_text": line,
                "insert": [x, y0 - index * char_h, insert[2] if len(insert) > 2 else 0],
            }
        )
    return records


def _text_to_item(record: dict, raw_height: Any) -> dict | None:
    clean = (record.get("clean_text") or "").strip()
    if not clean:
        return None
    insert = record.get("insert") or [0, 0, 0]
    try:
        x = float(insert[0])
        y = float(insert[1])
    except (TypeError, ValueError, IndexError):
        return None
    try:
        h = float(raw_height or 0)
    except (TypeError, ValueError):
        h = 0.0
    if h <= 0:
        h = 2.5  # 合理默认高度，避免 median 计算时被 0 干扰
    return {
        "text": clean,
        "x": x,
        "y": y,
        "h": h,
        "layer": record.get("layer", ""),
    }


def _in_bbox(x: float, y: float, bbox: list[float] | None) -> bool:
    if not bbox or len(bbox) < 4:
        return False
    x_min, y_min, x_max, y_max = bbox[0], bbox[1], bbox[2], bbox[3]
    return x_min <= x <= x_max and y_min <= y <= y_max


def _group_into_rows(items: list[dict], y_threshold: float) -> list[list[dict]]:
    sorted_items = sorted(items, key=lambda it: -it["y"])
    rows: list[list[dict]] = []
    current: list[dict] = []
    anchor_y: float | None = None
    for item in sorted_items:
        if anchor_y is None or abs(anchor_y - item["y"]) < y_threshold:
            current.append(item)
            if anchor_y is None:
                anchor_y = item["y"]
        else:
            rows.append(sorted(current, key=lambda it: it["x"]))
            current = [item]
            anchor_y = item["y"]
    if current:
        rows.append(sorted(current, key=lambda it: it["x"]))
    return rows


def _find_table_run(
    rows: list[list[dict]], start_index: int, y_gap_max: float
) -> list[list[dict]] | None:
    """从 start_index 起寻找连续行：列数相近 + y 间距合理。"""
    base = rows[start_index]
    base_cols = _estimate_col_count(base)
    if base_cols < MIN_COLS:
        return None
    run = [base]
    for j in range(start_index + 1, len(rows)):
        candidate = rows[j]
        cols = _estimate_col_count(candidate)
        if cols < MIN_COLS:
            break
        if abs(cols - base_cols) > 1:
            break
        prev_y = run[-1][0]["y"]
        curr_y = candidate[0]["y"]
        if abs(prev_y - curr_y) > y_gap_max:
            break
        run.append(candidate)
    if len(run) < MIN_ROWS:
        return None
    return run


def _estimate_col_count(row: list[dict]) -> int:
    if not row:
        return 0
    if len(row) == 1:
        return 1
    avg_h = sum(it["h"] for it in row) / len(row)
    gap_threshold = avg_h * 1.5  # x 间距大于 1.5 倍字高才算新列
    count = 1
    for prev, curr in zip(row, row[1:]):
        if abs(curr["x"] - prev["x"]) > gap_threshold:
            count += 1
    return count


def _build_table_from_run(run: list[list[dict]], median_h: float) -> dict | None:
    columns = _derive_columns(run, median_h)
    if len(columns) < MIN_COLS:
        return None

    grid: list[list[str]] = []
    for row in run:
        cells = [""] * len(columns)
        for item in row:
            col_idx = min(range(len(columns)), key=lambda i: abs(columns[i] - item["x"]))
            if cells[col_idx]:
                cells[col_idx] = f"{cells[col_idx]} {item['text']}"
            else:
                cells[col_idx] = item["text"]
        grid.append(cells)

    header = grid[0]
    data_rows = grid[1:]
    if not _looks_like_table(header, data_rows):
        return None

    data_rows, warnings = _enforce_size_limits(data_rows, header)
    confidence = _table_confidence(header, data_rows, "text_cluster")
    if confidence < 70:
        warnings.append("LOW_CONFIDENCE_TABLE")

    all_x = [item["x"] for row in run for item in row]
    all_y = [item["y"] for row in run for item in row]
    bbox = [min(all_x), min(all_y), max(all_x), max(all_y)] if all_x and all_y else None

    layer = _most_common_layer(run)

    return {
        "extraction_method": "text_cluster",
        "header": header,
        "rows": data_rows,
        "row_count": len(data_rows),
        "col_count": len(columns),
        "confidence": confidence,
        "layer": layer,
        "bbox": bbox,
        "warnings": warnings,
    }


def _derive_columns(run: list[list[dict]], median_h: float) -> list[float]:
    xs = sorted(item["x"] for row in run for item in row)
    if not xs:
        return []
    threshold = max(median_h * COL_X_THRESHOLD_FACTOR * 4, 1.0)

    clusters: list[float] = []
    bucket = [xs[0]]
    for x in xs[1:]:
        if x - bucket[-1] < threshold:
            bucket.append(x)
        else:
            clusters.append(sum(bucket) / len(bucket))
            bucket = [x]
    clusters.append(sum(bucket) / len(bucket))
    return clusters


def _looks_like_table(header: list[str], rows: list[list[str]]) -> bool:
    """Conservative filter for pseudo tables from notes or title blocks."""
    if len(header) < MIN_COLS or len(rows) < MIN_ROWS - 1:
        return False
    if _non_empty_count([header] + rows) < MIN_NON_EMPTY_CELLS:
        return False
    header_non_empty = sum(1 for cell in header if cell.strip())
    if header_non_empty / max(len(header), 1) < MIN_HEADER_NON_EMPTY_RATIO:
        return False
    row_widths = [sum(1 for cell in row if cell.strip()) for row in rows]
    if not row_widths or max(row_widths) < MIN_COLS:
        return False
    useful_rows = sum(1 for width in row_widths if width >= MIN_COLS)
    if useful_rows < MIN_ROWS - 1:
        return False
    if _looks_like_plain_notes(header, rows):
        return False
    return True


def _non_empty_count(grid: list[list[str]]) -> int:
    return sum(1 for row in grid for cell in row if cell.strip())


def _looks_like_plain_notes(header: list[str], rows: list[list[str]]) -> bool:
    grid = [header] + rows
    text_cells = [cell.strip() for row in grid for cell in row if cell.strip()]
    if not text_cells:
        return True
    long_cells = [cell for cell in text_cells if len(cell) >= 18]
    note_keywords = (
        "说明",
        "备注",
        "详见",
        "参见",
        "按规范",
        "施工",
        "复核",
        "本图",
        "不得",
    )
    note_hits = sum(1 for cell in text_cells if any(keyword in cell for keyword in note_keywords))
    sparse_rows = sum(1 for row in grid if sum(1 for cell in row if cell.strip()) <= 1)
    return (
        len(long_cells) >= max(2, len(text_cells) // 2)
        or note_hits >= max(2, len(text_cells) // 2)
        or sparse_rows >= max(3, len(grid) - 1)
    )


def _table_confidence(header: list[str], rows: list[list[str]], method: str) -> int:
    score = 86 if method == "acad_table" else 74
    widths = [sum(1 for cell in row if cell.strip()) for row in [header] + rows]
    if len(set(widths)) > 2:
        score -= 10
    if min(widths or [0]) < MIN_COLS:
        score -= 8
    if _looks_like_plain_notes(header, rows):
        score -= 25
    if len(rows) < 3:
        score -= 8
    return max(30, min(100, score))


def _most_common_layer(run: list[list[dict]]) -> str:
    layers = [item.get("layer", "") for row in run for item in row if item.get("layer")]
    if not layers:
        return ""
    counts: dict[str, int] = {}
    for layer in layers:
        counts[layer] = counts.get(layer, 0) + 1
    return max(counts.items(), key=lambda kv: kv[1])[0]


def _enforce_size_limits(rows: list[list[str]], header: list[str]) -> tuple[list[list[str]], list[str]]:
    warnings: list[str] = []
    if len(rows) > MAX_ROWS:
        rows = rows[:MAX_ROWS]
        warnings.append(f"TABLE_ROW_TRUNCATED_TO_{MAX_ROWS}")
    if header and len(header) > MAX_COLS:
        rows = [row[:MAX_COLS] for row in rows]
        warnings.append(f"TABLE_COL_TRUNCATED_TO_{MAX_COLS}")
    return rows, warnings


def _clean(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _safe_layer(entity: Any) -> str:
    try:
        return str(entity.dxf.layer)
    except AttributeError:
        return ""


def _safe_bbox(entity: Any) -> list[float] | None:
    try:
        insert = entity.dxf.insert
        return [float(insert[0]), float(insert[1]), float(insert[0]), float(insert[1])]
    except (AttributeError, TypeError, IndexError, ValueError):
        return None


def iter_extraction_methods(*tables: Iterable[dict]) -> Iterable[dict]:
    """便于上层串联两种抽取结果。"""
    for table_list in tables:
        yield from table_list
