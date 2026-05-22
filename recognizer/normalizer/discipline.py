import re

PREFIX_RULES = [
    ("建筑", ["建施", "建筑", "JZ", "JS", "ARCH", "A"]),
    ("结构", ["结施", "结构", "JG", "GS", "STR", "STRUCT", "S"]),
    ("给排水", ["水施", "给排水", "给水", "排水", "雨水", "污水", "喷淋", "SS", "PL", "P"]),
    ("电气", ["电施", "电气", "强电", "照明", "动力", "配电", "防雷", "接地", "DS", "ELEC", "E"]),
    ("暖通", ["暖施", "暖通", "空调", "通风", "防排烟", "排烟", "HVAC", "NT", "M"]),
    ("弱电", ["弱电", "智能化", "通信", "安防", "RD"]),
    ("消防", ["消防", "火灾报警", "消火栓", "喷淋"]),
    ("景观", ["景观", "园林", "LAND", "LA"]),
    ("室外", ["室外", "总图", "道路", "管网", "综合管线"]),
]

DISCIPLINE_RULES = [
    ("消防", ["消防电", "消防水", "消防", "火灾报警", "消火栓"]),
    ("建筑", ["建施", "建筑施工图", "建筑平面", "建筑", "立面", "剖面", "ARCH", "JZ", "JS"]),
    ("结构", ["结施", "结构施工图", "结构", "梁", "板", "柱", "基础", "STRUCT", "STR", "JG", "GS"]),
    ("给排水", ["水施", "给排水", "给水", "排水", "雨水", "污水", "喷淋", "PLUMBING", "SS", "PL"]),
    ("电气", ["电施", "电气", "强电", "照明", "动力", "配电", "防雷", "接地", "ELEC", "DS"]),
    ("暖通", ["暖施", "暖通", "空调", "通风", "防排烟", "排烟", "HVAC", "NT"]),
    ("弱电", ["弱电", "智能化", "通信", "综合布线", "安防", "监控", "RD"]),
    ("消防", ["喷淋"]),
    ("景观", ["景观", "园林", "LAND", "LA"]),
    ("室外", ["室外", "总图", "道路", "管网", "综合管线"]),
]


def infer_discipline(text: str) -> str | None:
    upper = (text or "").upper()
    prefix = re.match(r"^\s*([A-Z]+|[\u4e00-\u9fff]+)\s*[-_—－–]?\s*\d+", upper)
    if prefix:
        token = prefix.group(1)
        for discipline, keywords in PREFIX_RULES:
            if token in {keyword.upper() for keyword in keywords}:
                return discipline
    for discipline, keywords in DISCIPLINE_RULES:
        for keyword in keywords:
            if keyword.upper() in upper:
                return discipline
    return None
