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
    return fallback_bottom_right_bbox(texts, mtexts, inserts)
