import re
from datetime import date


def normalize_issue_date(value: str) -> str | None:
    text = value.strip()
    match = None
    if re.fullmatch(r"\d{8}", text):
        match = re.match(r"(\d{4})(\d{2})(\d{2})", text)
    elif not re.fullmatch(r"\d{6}", text):
        match = re.search(r"(\d{4})[年./-](\d{1,2})[月./-](\d{1,2})日?", text)
    if match:
        year, month, day = map(int, match.groups())
        try:
            return date(year, month, day).isoformat()
        except ValueError:
            return None
    month_match = re.search(r"(\d{4})[年./-]?(\d{1,2})月?", text)
    if not month_match and re.fullmatch(r"\d{6}", text):
        month_match = re.match(r"(\d{4})(\d{2})", text)
    if not month_match:
        short_match = re.fullmatch(r"(\d{2})[./-](\d{2})[./-](\d{2})", text)
        if not short_match:
            return None
        year = 2000 + int(short_match.group(1))
        month = int(short_match.group(2))
        day = int(short_match.group(3))
        try:
            return date(year, month, day).isoformat()
        except ValueError:
            return None
    year, month = map(int, month_match.groups())
    try:
        return date(year, month, 1).isoformat()
    except ValueError:
        return None


def is_full_date_text(value: str) -> bool:
    """文本是否为完整日期格式（YYYY-MM-DD / YYYY年MM月DD日 / YYYYMMDD）。

    用于区分 ATTRIB / 标签命中的高置信日期 vs 文中扫到的"2024年5月某规范"
    这类带月份的引用文本。
    """
    text = (value or "").strip()
    if re.fullmatch(r"\d{8}", text):
        return True
    if re.search(r"\d{4}[年./-]\d{1,2}[月./-]\d{1,2}日?", text):
        return True
    if re.fullmatch(r"\d{2}[./-]\d{2}[./-]\d{2}", text):
        return True
    return False
