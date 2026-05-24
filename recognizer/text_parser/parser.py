import re

from recognizer.filename_parser.parser import find_date, find_drawing_no, find_version
from recognizer.normalizer.date import normalize_issue_date
from recognizer.normalizer.discipline import infer_discipline
from recognizer.normalizer.drawing_no import (
    is_blacklisted_drawing_no,
    is_component_or_axis_no,
    is_plausible_drawing_no,
    is_supported_drawing_no,
    normalize_drawing_no,
)
from recognizer.normalizer.version import normalize_version

PARSER_NAME = "text_parser"
PARSER_VERSION = "0.1.0"


def parse_text(text: str, source_type: str) -> list[dict]:
    candidates: list[dict] = []
    raw = text[:1000]
    base = confidence_base(source_type)

    drawing_no = find_labeled_value(
        text,
        ["图号", "图纸编号", "图纸编码", "施工图编号", "专业图号", "Drawing No", "Sheet No"],
    ) or find_drawing_no(text)
    if drawing_no and not is_blacklisted_drawing_no(drawing_no):
        if is_supported_drawing_no(drawing_no):
            confidence = base["drawing_no"]
        elif is_plausible_drawing_no(drawing_no):
            confidence = max(base["drawing_no"] - 20, 50)
        else:
            confidence = min(base["drawing_no"], 45)
        if not is_component_or_axis_no(drawing_no):
            candidates.append(candidate("drawing_no", drawing_no, normalize_drawing_no(drawing_no), confidence, raw, source_type))

    drawing_name = find_labeled_value(text, ["图名", "图纸名称", "图纸名", "名称", "Drawing Title", "Sheet Title"])
    if drawing_name:
        candidates.append(candidate("drawing_name", drawing_name, drawing_name, base["drawing_name"], raw, source_type))

    version = find_labeled_value(text, ["版本", "版次", "Rev"]) or find_version(text)
    if version:
        candidates.append(candidate("version", version, normalize_version(version), base["version"], raw, source_type))

    issue_date = find_labeled_value(text, ["日期", "出图日期", "制图日期", "审核日期", "签发日期", "Date"]) or find_date(text)
    if issue_date:
        normalized = normalize_issue_date(issue_date)
        candidates.append(candidate("issue_date", issue_date, normalized, base["issue_date"] if normalized else min(base["issue_date"], 50), raw, source_type))

    discipline = infer_discipline(text)
    if discipline:
        candidates.append(candidate("discipline", discipline, discipline, base["discipline"], raw, source_type))

    # 签字栏字段（#9）
    for field_name, labels in SIGNATURE_LABELS.items():
        value = find_labeled_value(text, labels)
        if value and is_plausible_person_name(value):
            candidates.append(candidate(field_name, value, value, base.get(field_name, 65), raw, source_type))

    return candidates


SIGNATURE_LABELS = {
    "designer": ["设计", "设计人", "设计者", "Designer", "Design By"],
    "drafter": ["制图", "制图人", "绘图", "绘图人", "Drafter", "Drawn By"],
    "reviewer": ["审核", "审核人", "审图", "Reviewer", "Reviewed By"],
    "checker": ["校对", "校对人", "校核", "校核人", "Checker", "Checked By"],
    "approver": ["审定", "审定人", "批准", "批准人", "Approver", "Approved By"],
}


def is_plausible_person_name(value: str) -> bool:
    """姓名通常 2-6 字（中文）或 2-30 字（英文/拼音），不含明显非姓名字符。"""
    text = (value or "").strip()
    if not text or len(text) > 30:
        return False
    # 排除日期/版本/数字串误命中
    if any(char in text for char in ["年", "月", "日", "：", ":"]):
        return False
    if text.replace(".", "").replace("-", "").isdigit():
        return False
    return True


def find_labeled_value(text: str, labels: list[str]) -> str | None:
    for label in labels:
        pattern = rf"{re.escape(label)}\s*[:：]?\s*([A-Za-z0-9一-龥_.\-—－/年月日 ]{{1,40}})"
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            value = re.split(r"[\n\r]", match.group(1).strip())[0].strip()
            return value or None
    return None


def confidence_base(source_type: str) -> dict[str, int]:
    if source_type == "pdf_text":
        return {"drawing_no": 80, "drawing_name": 75, "version": 70, "issue_date": 70, "discipline": 65}
    return {"drawing_no": 75, "drawing_name": 70, "version": 65, "issue_date": 65, "discipline": 60}


def candidate(field: str, value: str, normalized: str | None, confidence: int, raw_text: str, source_type: str) -> dict:
    return {
        "field_name": field,
        "candidate_value": value.strip(),
        "normalized_value": normalized,
        "source_type": source_type,
        "confidence": confidence,
        "raw_text": raw_text,
        "bbox": None,
        "parser_name": PARSER_NAME,
        "parser_version": PARSER_VERSION,
    }
