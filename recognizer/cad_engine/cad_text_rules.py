
from recognizer.filename_parser.parser import find_date, find_drawing_no, find_version
from recognizer.normalizer.date import is_full_date_text, normalize_issue_date
from recognizer.normalizer.discipline import infer_discipline
from recognizer.normalizer.drawing_no import (
    is_blacklisted_drawing_no,
    is_component_or_axis_no,
    is_plausible_drawing_no,
    is_supported_drawing_no,
    normalize_drawing_no,
)
from recognizer.normalizer.version import normalize_version

DRAWING_NAME_KEYWORDS = [
    "总平面图",
    "建筑总平面图",
    "一层平面图",
    "二层平面图",
    "三层平面图",
    "地下室平面图",
    "屋面平面图",
    "立面图",
    "剖面图",
    "楼梯详图",
    "节点详图",
    "墙身详图",
    "门窗详图",
    "基础平面图",
    "基础详图",
    "梁配筋图",
    "板配筋图",
    "柱平法施工图",
    "墙柱平法施工图",
    "结构平面图",
    "照明平面图",
    "插座平面图",
    "配电系统图",
    "弱电平面图",
    "火灾报警平面图",
    "给排水平面图",
    "给水平面图",
    "排水平面图",
    "消防平面图",
    "喷淋平面图",
    "暖通平面图",
    "通风平面图",
    "空调平面图",
    "平面布置图",
    "设备布置图",
    "管线综合图",
    "综合管线图",
    "电气系统图",
    "防雷接地平面图",
    "弱电系统图",
    "消防系统图",
    "喷淋系统图",
    "给水系统图",
    "排水系统图",
    "雨水系统图",
    "空调水系统图",
    "通风系统图",
    "排烟系统图",
    "基础梁配筋图",
    "屋面结构平面图",
    "墙柱定位图",
    "梁平法施工图",
    "板平法施工图",
    "节点大样图",
    "门窗表图纸",
    "系统图",
    "原理图",
    "详图",
    "大样图",
]

NOTE_TEXT_KEYWORDS = [
    "本图尺寸以毫米为单位",
    "施工时应按规范执行",
    "详见设计说明",
    "未经许可不得施工",
    "所有尺寸现场复核",
    "本图未尽事宜",
    "本图尺寸",
    "施工前应",
    "施工单位应",
    "现场复核",
    "图中尺寸",
    "标高以米计",
    "本工程",
    "设计说明",
    "主要材料表",
    "图例",
    "备注",
    "说明",
    "材料表",
    "设备表",
    "门窗表",
    "主要材料",
    "技术要求",
    "施工要求",
    "详见",
    "参见",
    "按规范执行",
]


def infer_candidates_from_text(text: str, source_type: str, *, tagged_field: str | None = None) -> list[dict]:
    value = (text or "").strip()
    if not value:
        return []
    candidates: list[dict] = []
    base = confidence_base(source_type)

    if tagged_field:
        tagged = tagged_candidate(tagged_field, value, source_type, base.get(tagged_field, 70))
        return [tagged] if tagged else []

    drawing_no = find_drawing_no(value)
    if drawing_no and not is_blacklisted_drawing_no(drawing_no):
        if is_supported_drawing_no(drawing_no):
            confidence = adjusted_confidence(base["drawing_no"], value)
        elif is_plausible_drawing_no(drawing_no):
            confidence = adjusted_confidence(max(base["drawing_no"] - 20, 50), value)
        else:
            confidence = 0
        if confidence > 0:
            candidates.append(candidate("drawing_no", drawing_no, normalize_drawing_no(drawing_no), confidence, value, source_type))

    drawing_name = find_drawing_name(value)
    if drawing_name:
        # 关键词命中 = 强候选；启发式命中 = 弱候选（-15）
        is_heuristic = drawing_name == value and drawing_name not in DRAWING_NAME_KEYWORDS
        name_confidence = adjusted_confidence(base["drawing_name"], value)
        if is_heuristic:
            name_confidence = max(name_confidence - 15, 0)
        candidates.append(candidate("drawing_name", drawing_name, drawing_name, name_confidence, value, source_type))

    version = find_version(value)
    if version:
        candidates.append(candidate("version", version, normalize_version(version), base["version"], value, source_type))

    issue_date = find_date(value)
    if issue_date:
        normalized = normalize_issue_date(issue_date)
        confidence = base["issue_date"] if normalized else min(base["issue_date"], 50)
        # 自由 cad_text/cad_mtext 路径下，非完整日期 (如 "2024年5月") 容易误吃
        # 图中规范引用，给低置信度
        if source_type in {"cad_text", "cad_mtext"} and not is_full_date_text(issue_date):
            confidence = min(confidence, 45)
        candidates.append(candidate("issue_date", issue_date, normalized, confidence, value, source_type))

    discipline = infer_discipline(value)
    if discipline:
        confidence = discipline_confidence(source_type, value, base["discipline"])
        candidates.append(candidate("discipline", discipline, discipline, confidence, value, source_type))

    return candidates


def tagged_candidate(field_name: str, value: str, source_type: str, confidence: int) -> dict | None:
    normalized = normalize_by_field(field_name, value)
    if field_name == "issue_date" and normalized is None:
        confidence = min(confidence, 50)
    if source_type != "cad_block_attr" and field_name == "drawing_no" and is_component_or_axis_no(value):
        confidence = min(confidence, 45)
    if source_type != "cad_block_attr" and field_name == "drawing_name" and is_note_text(value):
        confidence = min(confidence, 45)
    return candidate(field_name, value, normalized, confidence, value, source_type)


def normalize_by_field(field_name: str, value: str) -> str | None:
    if field_name == "drawing_no":
        return normalize_drawing_no(value)
    if field_name == "version":
        return normalize_version(value)
    if field_name == "issue_date":
        return normalize_issue_date(value)
    if field_name == "discipline":
        return infer_discipline(value) or value
    return value


NAME_HINT_KEYWORDS = (
    "图",
    "表",
    "详图",
    "大样",
    "平面",
    "立面",
    "剖面",
    "系统",
    "原理",
    "节点",
    "示意",
    "布置",
)


def find_drawing_name(text: str) -> str | None:
    if is_note_text(text):
        return None
    for keyword in DRAWING_NAME_KEYWORDS:
        if keyword in text:
            return keyword
    # 启发式：长度 2-30 字、含图名提示词、非全数字符号
    stripped = (text or "").strip()
    if 2 <= len(stripped) <= 30 and any(hint in stripped for hint in NAME_HINT_KEYWORDS):
        if not stripped.replace("-", "").replace(" ", "").isdigit():
            return stripped
    return None


def is_note_text(text: str) -> bool:
    stripped = (text or "").strip()
    if len(stripped) > 80:
        return True
    return any(keyword in stripped for keyword in NOTE_TEXT_KEYWORDS)


def adjusted_confidence(confidence: int, text: str) -> int:
    value = (text or "").strip()
    if is_component_or_axis_no(value):
        confidence -= 20
    if len(text) > 80:
        confidence -= 15
    if len(text) > 30:
        confidence -= 10
    return max(confidence, 0)


def discipline_confidence(source_type: str, text: str, confidence: int) -> int:
    if source_type in {"cad_text", "cad_mtext"} and len((text or "").strip()) > 30:
        return max(confidence - 10, 0)
    return confidence


def confidence_base(source_type: str) -> dict[str, int]:
    if source_type == "cad_block_attr":
        return {
            "drawing_no": 93, "drawing_name": 90, "version": 88, "issue_date": 88, "discipline": 84,
            "designer": 92, "drafter": 92, "reviewer": 92, "checker": 92, "approver": 92,
        }
    if source_type == "cad_filename":
        return {
            "drawing_no": 70, "drawing_name": 60, "version": 60, "issue_date": 65, "discipline": 60,
            "designer": 55, "drafter": 55, "reviewer": 55, "checker": 55, "approver": 55,
        }
    return {
        "drawing_no": 78, "drawing_name": 72, "version": 66, "issue_date": 66, "discipline": 64,
        "designer": 70, "drafter": 70, "reviewer": 70, "checker": 70, "approver": 70,
    }


def is_suspect_drawing_no_candidate(value: str, source_type: str) -> bool:
    if source_type not in {"cad_text", "cad_mtext"}:
        return False
    return is_component_or_axis_no(value) or not is_supported_drawing_no(value)


def is_suspect_drawing_name_candidate(value: str, source_type: str) -> bool:
    if source_type not in {"cad_text", "cad_mtext"}:
        return False
    text = (value or "").strip()
    return is_note_text(text) or len(text) > 80


def candidate(
    field: str,
    value: str,
    normalized: str | None,
    confidence: int,
    raw_text: str,
    source_type: str,
) -> dict:
    return {
        "field_name": field,
        "candidate_value": value.strip(),
        "normalized_value": normalized,
        "source_type": source_type,
        "confidence": confidence,
        "raw_text": raw_text,
        "bbox": None,
        "parser_name": "dxf_candidate_parser",
        "parser_version": "v0.2.1",
    }
