from pathlib import Path
import re

from recognizer.normalizer.date import normalize_issue_date
from recognizer.normalizer.discipline import infer_discipline
from recognizer.normalizer.drawing_no import is_supported_drawing_no, normalize_drawing_no
from recognizer.normalizer.version import normalize_version


PARSER_NAME = "filename_parser"
PARSER_VERSION = "0.1.0"


def parse_filename(filename: str) -> list[dict]:
    stem = Path(filename).stem
    parts = [part for part in re.split(r"[_\s]+", stem) if part]
    candidates: list[dict] = []
    raw_text = stem

    drawing_no = find_drawing_no(stem)
    if drawing_no and is_supported_drawing_no(drawing_no):
        candidates.append(candidate("drawing_no", drawing_no, normalize_drawing_no(drawing_no), 70, raw_text))

    name_part = find_name_part(parts, drawing_no)
    if name_part:
        candidates.append(candidate("drawing_name", name_part, name_part, 60, raw_text))

    version = find_version(stem)
    if version:
        candidates.append(candidate("version", version, normalize_version(version), 60, raw_text))

    issue_date = find_date(stem)
    if issue_date:
        candidates.append(candidate("issue_date", issue_date, normalize_issue_date(issue_date), 65, raw_text))

    discipline = infer_discipline(stem)
    if discipline:
        candidates.append(candidate("discipline", discipline, discipline, 60, raw_text))

    return candidates


def find_drawing_no(text: str) -> str | None:
    patterns = [
        r"(建施|建总|结施|水施|电施|暖施|弱电|消防|总施|设总|室外|建筑|结构|给排水|电气|暖通)\s*[-_—－– ]?\s*\d{1,4}",
        r"\b(JS|JZ|JG|GS|SS|DS|NT|XS|RD|PL|LA)\s*[-_—－– ]?\s*\d{1,4}\b",
        r"\b[ASEMPT]\s*[-_—－– ]?\s*\d{2,4}\b",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(0).strip()
    compact_text = re.sub(r"[\s_—－–-]+", "", text)
    compact_patterns = [
        r"(建施总|建总|建施|结施|水施|电施|暖施|弱电|消防|总施|设总|室外|建筑|结构|给排水|电气|暖通)\d{1,4}",
        r"(JS|JZ|JG|GS|SS|DS|NT|XS|RD|PL|LA)\d{1,4}",
        r"[ASEMPT]\d{2,4}",
    ]
    for pattern in compact_patterns:
        match = re.search(pattern, compact_text, re.IGNORECASE)
        if match:
            return match.group(0).strip()
    return None


def find_name_part(parts: list[str], drawing_no: str | None) -> str | None:
    for part in parts:
        if drawing_no and drawing_no.replace(" ", "") in part.replace(" ", ""):
            continue
        if find_version(part) or find_date(part):
            continue
        if any(keyword in part for keyword in ["图", "平面", "立面", "剖面", "详图"]):
            return part
    return None


def find_version(text: str) -> str | None:
    match = re.search(r"(?:版本)?[A-Z]版|Rev[.\s-]?\w+|V\d+(?:\.\d+)?|变更\d+", text, re.IGNORECASE)
    return match.group(0) if match else None


def find_date(text: str) -> str | None:
    match = re.search(r"\d{4}[年./-]?\d{1,2}[月./-]?\d{1,2}日?|\d{4}[年./-]?\d{1,2}月?|\d{8}|\d{6}|\d{2}[./-]\d{2}[./-]\d{2}", text)
    return match.group(0) if match else None


def candidate(field: str, value: str, normalized: str | None, confidence: int, raw_text: str) -> dict:
    return {
        "field_name": field,
        "candidate_value": value,
        "normalized_value": normalized,
        "source_type": "filename",
        "confidence": confidence,
        "raw_text": raw_text,
        "bbox": None,
        "parser_name": PARSER_NAME,
        "parser_version": PARSER_VERSION,
    }
