"""标题栏区域定位与候选位置加权。

策略：
1. 扫描 INSERT 实体的 block_name，命中 TITLE_BLOCK_HINTS 视为图签 → 记录其插入点。
2. 没找到图签 INSERT 时，退化为"modelspace 包围盒右下 1/4 区域"。
3. 给 cad_text / cad_mtext 候选附加 in_title_area 标记，融合时可加分。
"""
from __future__ import annotations

TITLE_BLOCK_HINTS = (
    "TITLE",
    "TITLEBLOCK",
    "TBLOCK",
    "TBLK",
    "图签",
    "图框",
    "标题栏",
    "会签栏",
    "签字栏",
    "图纸标题",
)


def is_title_block_name(name: str | None) -> bool:
    if not name:
        return False
    upper = name.upper()
    return any(hint in upper or hint in name for hint in TITLE_BLOCK_HINTS)


def find_title_block_bbox(inserts: list[dict]) -> tuple[float, float, float, float] | None:
    """从 INSERT 列表里找最可能的图签块。

    返回 (xmin, ymin, xmax, ymax) 或 None。当前实现：取第一个匹配 hint 的
    INSERT 的插入点，以经验值 ±400 单位为半径生成 bbox（典型图签宽 200-400mm）。
    """
    for insert in inserts:
        if is_title_block_name(insert.get("block_name")):
            point = insert.get("insert") or [0, 0, 0]
            try:
                x, y = float(point[0]), float(point[1])
            except (TypeError, ValueError, IndexError):
                continue
            return (x - 400.0, y - 250.0, x + 400.0, y + 250.0)
    return None


def fallback_bottom_right_bbox(
    texts: list[dict], mtexts: list[dict], inserts: list[dict]
) -> tuple[float, float, float, float] | None:
    """退化策略：所有实体的包围盒右下 1/4。"""
    xs: list[float] = []
    ys: list[float] = []
    for collection in (texts, mtexts, inserts):
        for item in collection:
            point = item.get("insert") or [0, 0, 0]
            try:
                xs.append(float(point[0]))
                ys.append(float(point[1]))
            except (TypeError, ValueError, IndexError):
                continue
    if not xs or not ys:
        return None
    xmin, xmax = min(xs), max(xs)
    ymin, ymax = min(ys), max(ys)
    width = xmax - xmin
    height = ymax - ymin
    if width <= 0 or height <= 0:
        return None
    return (xmin + width * 0.5, ymin, xmax, ymin + height * 0.5)


def point_in_bbox(point: list[float] | None, bbox: tuple[float, float, float, float] | None) -> bool:
    if not point or not bbox:
        return False
    try:
        x, y = float(point[0]), float(point[1])
    except (TypeError, ValueError, IndexError):
        return False
    xmin, ymin, xmax, ymax = bbox
    return xmin <= x <= xmax and ymin <= y <= ymax


def find_title_block_bbox_adaptive(
    inserts: list[dict],
    texts: list[dict],
    *,
    drawing_extent: tuple[float, float, float, float] | None = None,
) -> tuple[float, float, float, float] | None:
    """优先 INSERT 名称匹配；失败时按文字密度启发式判右下角。

    启发式：把所有 texts 落到 10x10 网格，找文字密度最高的右下象限格子簇。
    若该簇 bbox 比例符合（宽/高 在 1.2~5.0）且文字数 >= 8 → 视为标题栏。
    否则返回 None（不再 fallback 到固定右下 1/4，避免误判）。
    """
    bbox = find_title_block_bbox(inserts)
    if bbox is not None:
        return bbox

    xs: list[float] = []
    ys: list[float] = []
    for text in texts:
        point = text.get("insert") or [0, 0, 0]
        try:
            xs.append(float(point[0]))
            ys.append(float(point[1]))
        except (TypeError, ValueError, IndexError):
            continue
    if len(xs) < 8:
        return None
    if drawing_extent is not None:
        xmin_all, ymin_all, xmax_all, ymax_all = drawing_extent
    else:
        xmin_all, xmax_all = min(xs), max(xs)
        ymin_all, ymax_all = min(ys), max(ys)
    width = xmax_all - xmin_all
    height = ymax_all - ymin_all
    if width <= 0 or height <= 0:
        return None

    grid_size = 10
    cell_w = width / grid_size
    cell_h = height / grid_size
    cells: dict[tuple[int, int], list[tuple[float, float]]] = {}
    for x, y in zip(xs, ys):
        col = min(int((x - xmin_all) / cell_w), grid_size - 1)
        row = min(int((y - ymin_all) / cell_h), grid_size - 1)
        if col < grid_size // 2 or row >= grid_size // 2:
            continue
        cells.setdefault((col, row), []).append((x, y))

    if not cells:
        return None
    densest = max(cells.values(), key=len)
    if len(densest) < 8:
        return None

    cx_min = min(p[0] for p in densest)
    cx_max = max(p[0] for p in densest)
    cy_min = min(p[1] for p in densest)
    cy_max = max(p[1] for p in densest)
    cluster_w = cx_max - cx_min
    cluster_h = cy_max - cy_min
    if cluster_w <= 0 or cluster_h <= 0:
        return None
    ratio = cluster_w / cluster_h
    if ratio < 1.2 or ratio > 5.0:
        return None

    pad_x = max(cluster_w * 0.15, 20.0)
    pad_y = max(cluster_h * 0.25, 20.0)
    return (cx_min - pad_x, cy_min - pad_y, cx_max + pad_x, cy_max + pad_y)


def resolve_title_area(cad_json: dict) -> tuple[float, float, float, float] | None:
    """从已抽取的 cad_json 里解析出标题栏区域 bbox。"""
    inserts: list[dict] = []
    texts: list[dict] = []
    mtexts: list[dict] = []
    for space in cad_json.get("spaces", []):
        inserts.extend(space.get("inserts", []))
        texts.extend(space.get("texts", []))
        mtexts.extend(space.get("mtexts", []))
    bbox = find_title_block_bbox(inserts)
    if bbox is not None:
        return bbox
    bbox = find_title_block_bbox_adaptive(inserts, texts)
    if bbox is not None:
        return bbox
    return fallback_bottom_right_bbox(texts, mtexts, inserts)
