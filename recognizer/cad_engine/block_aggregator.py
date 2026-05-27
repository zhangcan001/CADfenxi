"""INSERT 块聚合：按 (block_name, layer) 分组统计图纸内符号/设备块。

输入：cad_json（含 spaces[].inserts）
输出：聚合行列表，每行附 discipline_guess（由 layer 推断）和 attribs 摘要。

排除规则：
- block_name 命中 title-block hints（图签）
- 匿名块（*Model_Space / *Paper_Space / *U... / *X... 等系统块）
- block_name 为空
"""
from __future__ import annotations

from recognizer.cad_engine.title_area import is_title_block_name
from recognizer.normalizer.discipline import infer_discipline


ANONYMOUS_BLOCK_PREFIXES = ("*MODEL_SPACE", "*PAPER_SPACE")
ANONYMOUS_BLOCK_CHARS = ("*U", "*X", "*T", "*D", "*A")
MAX_ATTRIB_VALUES_PER_TAG = 10
MAX_DISTINCT_BLOCKS = 500
FRAME_BLOCK_KEYWORDS = (
    "FRAME",
    "BORDER",
    "SHEET",
    "PAPER",
    "图框",
    "外框",
    "内框",
    "边框",
    "图纸框",
)


def _is_anonymous_block(name: str) -> bool:
    if not name:
        return True
    upper = name.upper()
    if any(upper.startswith(prefix) for prefix in ANONYMOUS_BLOCK_PREFIXES):
        return True
    if upper.startswith("*") and len(upper) >= 2 and upper[1] in ("U", "X", "T", "D", "A"):
        return True
    return False


def _normalize_block_name(name: str) -> str:
    return " ".join((name or "").strip().split())


def _is_frame_block_name(name: str) -> bool:
    if not name:
        return False
    upper = name.upper()
    if any(keyword in upper or keyword in name for keyword in FRAME_BLOCK_KEYWORDS):
        return True
    normalized = upper.replace("-", "_").replace(" ", "_")
    return any(
        token in normalized
        for token in (
            "A0_FRAME",
            "A1_FRAME",
            "A2_FRAME",
            "A3_FRAME",
            "A4_FRAME",
            "FRAME_A0",
            "FRAME_A1",
            "FRAME_A2",
            "FRAME_A3",
            "FRAME_A4",
        )
    )


def aggregate_inserts(
    cad_json: dict,
    *,
    exclude_block_names: set[str] | None = None,
) -> list[dict]:
    """按 (block_name, layer) 聚合 INSERT 实体。

    返回:
      [
        {
          "block_name": str,
          "layer_name": str,
          "discipline_guess": str | None,   # 由 layer_name 推断
          "count": int,
          "sample_insert": [x, y, z] | None,
          "sample_bbox": [xmin, ymin, xmax, ymax] | None,  # 单点 ±10 半径示意
          "attribs_summary": {tag: [value1, value2, ...], ...},  # 去重、截断
        },
        ...
      ]
    """
    excluded: set[str] = set(exclude_block_names or set())

    groups: dict[tuple[str, str], dict] = {}
    for space in cad_json.get("spaces", []) or []:
        for insert in space.get("inserts", []) or []:
            block_name = _normalize_block_name(insert.get("block_name") or "")
            if not block_name:
                continue
            if _is_anonymous_block(block_name):
                continue
            if is_title_block_name(block_name):
                continue
            if _is_frame_block_name(block_name):
                continue
            if block_name in excluded:
                continue

            layer_name = (insert.get("layer") or "").strip() or "0"
            key = (block_name, layer_name)
            point = insert.get("insert") or [0.0, 0.0, 0.0]
            try:
                sample_point = [float(point[0]), float(point[1]), float(point[2] if len(point) > 2 else 0.0)]
            except (TypeError, ValueError, IndexError):
                sample_point = [0.0, 0.0, 0.0]

            bucket = groups.get(key)
            if bucket is None:
                bucket = {
                    "block_name": block_name,
                    "layer_name": layer_name,
                    "count": 0,
                    "sample_insert": sample_point,
                    "attribs": {},
                }
                groups[key] = bucket
            bucket["count"] += 1

            for attrib in insert.get("attribs", []) or []:
                tag = (attrib.get("tag") or "").strip()
                value = (attrib.get("clean_text") or "").strip()
                if not tag or not value:
                    continue
                values = bucket["attribs"].setdefault(tag, [])
                if value not in values and len(values) < MAX_ATTRIB_VALUES_PER_TAG:
                    values.append(value)

    rows: list[dict] = []
    for (block_name, layer_name), bucket in groups.items():
        discipline_guess = infer_discipline(layer_name) or infer_discipline(block_name)
        sample_insert = bucket["sample_insert"]
        sample_bbox: list[float] | None = None
        if sample_insert is not None:
            x, y = sample_insert[0], sample_insert[1]
            sample_bbox = [x - 10.0, y - 10.0, x + 10.0, y + 10.0]
        rows.append(
            {
                "block_name": block_name,
                "layer_name": layer_name,
                "discipline_guess": discipline_guess,
                "count": bucket["count"],
                "sample_insert": sample_insert,
                "sample_bbox": sample_bbox,
                "attribs_summary": dict(bucket["attribs"]),
            }
        )

    rows.sort(key=lambda r: (-r["count"], r["block_name"], r["layer_name"]))
    if len(rows) > MAX_DISTINCT_BLOCKS:
        rows = rows[:MAX_DISTINCT_BLOCKS]
    return rows
