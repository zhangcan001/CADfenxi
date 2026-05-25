"""根据表头关键词把表格分类成 equipment / material / drawing_index / legend / other。

启发式：
- 命中 ≥2 个关键词的 kind 优先返回；
- 仅命中 1 个，但该词是强指示（如"设备表"/"图纸目录"），也直接返回；
- 多个 kind 同分时按 KIND_PRIORITY 选；
- 完全不命中 → 'other'。
"""
from __future__ import annotations


KIND_KEYWORDS: dict[str, list[str]] = {
    "equipment": ["设备", "型号", "规格", "功率", "电压", "数量", "品牌", "厂家", "设备表", "设备明细"],
    "material": ["材料", "品名", "单位", "用量", "材质", "材料表", "材料明细"],
    "drawing_index": ["图号", "图名", "页号", "页码", "图纸目录", "图纸名称", "图纸编号"],
    "legend": ["图例", "符号", "代号", "说明"],
}

STRONG_INDICATORS: dict[str, list[str]] = {
    "equipment": ["设备表", "设备明细", "设备清单"],
    "material": ["材料表", "材料明细", "材料清单"],
    "drawing_index": ["图纸目录", "图纸清单"],
    "legend": ["图例"],
}

KIND_PRIORITY = ["equipment", "material", "drawing_index", "legend"]


def classify_table_kind(header: list[str]) -> str:
    """返回表格类型。

    header: 表头单元格列表（已 strip）。
    """
    if not header:
        return "other"

    text_blob = " ".join(cell for cell in header if cell)
    if not text_blob:
        return "other"

    for kind in KIND_PRIORITY:
        for strong in STRONG_INDICATORS.get(kind, []):
            if strong in text_blob:
                return kind

    scores: dict[str, int] = {}
    for kind, keywords in KIND_KEYWORDS.items():
        hit = sum(1 for kw in keywords if kw in text_blob)
        if hit >= 2:
            scores[kind] = hit

    if not scores:
        return "other"

    best_score = max(scores.values())
    for kind in KIND_PRIORITY:
        if scores.get(kind) == best_score:
            return kind
    return "other"
