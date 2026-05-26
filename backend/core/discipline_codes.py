"""图号前缀 → 专业映射（用于跨图一致性校验）。

与 `recognizer/normalizer/discipline.py` 的关键词列表保持一致，但这里只做
"前缀 → 专业" 单向映射，用最长前缀匹配。
"""
from __future__ import annotations

import re


DRAWING_NO_PREFIX_TO_DISCIPLINE: dict[str, str] = {
    # 中文施工图常用前缀
    "建施": "建筑",
    "建": "建筑",
    "结施": "结构",
    "结": "结构",
    "水施": "给排水",
    "电施": "电气",
    "暖施": "暖通",
    "通施": "暖通",
    "弱施": "弱电",
    "弱电": "弱电",
    "消施": "消防",
    "消": "消防",
    "总": "室外",
    "总图": "室外",
    "园": "景观",
    "景": "景观",
    # 英文缩写
    "ARCH": "建筑",
    "AR": "建筑",
    "JZ": "建筑",
    "JS": "建筑",
    "STR": "结构",
    "STRUCT": "结构",
    "ST": "结构",
    "JG": "结构",
    "GS": "结构",
    "PD": "给排水",
    "PL": "给排水",
    "SS": "给排水",
    "EE": "电气",
    "EL": "电气",
    "ELEC": "电气",
    "DS": "电气",
    "ME": "暖通",
    "HV": "暖通",
    "HVAC": "暖通",
    "NT": "暖通",
    "FA": "消防",
    "RD": "弱电",
    "LAND": "景观",
    "LA": "景观",
}


_PREFIX_PATTERN = re.compile(r"^\s*([A-Za-z]+|[一-鿿]+)")


def infer_discipline_from_drawing_no(drawing_no: str | None) -> str | None:
    """从图号字符串前缀推断专业。最长前缀匹配；无命中返回 None。"""
    if not drawing_no:
        return None
    match = _PREFIX_PATTERN.match(drawing_no)
    if not match:
        return None
    token = match.group(1).upper()
    # 中文匹配
    cn_match = re.match(r"^[一-鿿]+", drawing_no)
    if cn_match:
        cn_token = cn_match.group(0)
        for length in range(len(cn_token), 0, -1):
            prefix = cn_token[:length]
            if prefix in DRAWING_NO_PREFIX_TO_DISCIPLINE:
                return DRAWING_NO_PREFIX_TO_DISCIPLINE[prefix]
    # 英文匹配
    upper_map = {k.upper(): v for k, v in DRAWING_NO_PREFIX_TO_DISCIPLINE.items() if k.isascii()}
    for length in range(len(token), 0, -1):
        prefix = token[:length]
        if prefix in upper_map:
            return upper_map[prefix]
    return None
