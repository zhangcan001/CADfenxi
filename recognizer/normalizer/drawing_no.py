import re

COMPONENT_NO_PATTERN = re.compile(
    r"^(?:KZ|L|KL|WKL|M|C|D|W|MQ|GZ|CT|YBZ|门|窗)-?\d+$",
    re.IGNORECASE,
)
AXIS_NO_PATTERN = re.compile(r"^(?:轴\d+|\d+轴|[A-Z]轴)$", re.IGNORECASE)

# 黑名单：比例尺、纸张幅面、明显非图号的简短串
SCALE_PATTERN = re.compile(r"^\d+\s*:\s*\d+$")
PAPER_SIZE_PATTERN = re.compile(r"^A[0-4]$", re.IGNORECASE)

# 宽松匹配：1-6 个字母/汉字前缀 + 1-4 位数字，可选第二段数字（三段式 JS-01-01）
PLAUSIBLE_PATTERN = re.compile(
    r"^[A-Z一-鿿]{1,6}-\d{1,4}(?:-\d{1,4})?$",
    re.IGNORECASE,
)


def normalize_drawing_no(value: str) -> str | None:
    text = value.strip().replace("—", "-").replace("－", "-").replace("–", "-").replace("_", "-")
    text = re.sub(r"\s+", "-", text)
    text = re.sub(r"-+", "-", text).strip("-")
    # 段数判断：原文本 - 分割后的段数。手工输入的 "人工-001" 是两段，不应套三段式。
    segments = [s for s in text.split("-") if s]
    patterns = [
        (r"^(建施总|建施|建总|结施|水施|电施|暖施|弱电|消防|总施|设总|室外|建筑|结构|给排水|电气|暖通)[-]?([A-Z])[-]?(\d{1,4})$", r"\1-\2-\3"),
        (r"^(建施总|建施|建总|结施|水施|电施|暖施|弱电|消防|总施|设总|室外|建筑|结构|给排水|电气|暖通)[-]?(\d{1,4})$", r"\1-\2"),
        (r"^(JS|JZ|JG|GS|SS|DS|NT|XS|RD|PL|LA)[-]?(\d{1,4})$", r"\1-\2"),
        (r"^([ASEMPT])[-]?(\d{2,4})$", r"\1-\2"),
        (r"^(A|S|E|M|P|T)[-]?(\d{2,4})$", r"\1-\2"),
    ]
    for pattern, replacement in patterns:
        if re.match(pattern, text, re.IGNORECASE):
            return re.sub(pattern, replacement, text, flags=re.IGNORECASE).upper()
    # 三段式仅在原文本明确有三段时启用（避免 "人工-001" 被错误切成 "人工-00-1"）
    if len(segments) >= 3:
        three_segment = r"^([A-Z一-鿿]{1,6})[-]?(\d{1,4})[-]?(\d{1,4})$"
        if re.match(three_segment, text, re.IGNORECASE):
            return re.sub(three_segment, r"\1-\2-\3", text, flags=re.IGNORECASE).upper()
    return text or None


def is_component_or_axis_no(value: str) -> bool:
    text = value.strip().replace(" ", "").replace("_", "-").replace("—", "-").replace("－", "-").replace("–", "-")
    return bool(COMPONENT_NO_PATTERN.match(text) or AXIS_NO_PATTERN.match(text))


def is_blacklisted_drawing_no(value: str) -> bool:
    """非图号的明显候选：比例尺、纸张幅面、构件号、轴号。"""
    text = (value or "").strip().replace(" ", "")
    if not text:
        return True
    if SCALE_PATTERN.match(text):
        return True
    if PAPER_SIZE_PATTERN.match(text):
        return True
    if is_component_or_axis_no(text):
        return True
    return False


def is_supported_drawing_no(value: str) -> bool:
    """白名单：高置信度图号格式，列在已知规范内。"""
    normalized = normalize_drawing_no(value) or ""
    if is_component_or_axis_no(normalized):
        return False
    patterns = [
        r"^(建施总|建施|建总|结施|水施|电施|暖施|弱电|消防|总施|设总|室外|建筑|结构|给排水|电气|暖通)(?:-[A-Z])?-\d{1,4}$",
        r"^(JS|JZ|JG|GS|SS|DS|NT|XS|RD|PL|LA)-\d{1,4}$",
        r"^[ASEMPT]-\d{2,4}$",
    ]
    return any(re.match(pattern, normalized, re.IGNORECASE) for pattern in patterns)


def is_plausible_drawing_no(value: str) -> bool:
    """宽松匹配：可能是图号的格式，给中等置信度。

    覆盖三段式 (JS-01-01)、两段拼音首字母 (SJ-01, DQ-01, KT-05) 等真实工程
    常见但不在白名单里的图号。命中黑名单则一律拒绝。
    """
    if is_blacklisted_drawing_no(value):
        return False
    normalized = normalize_drawing_no(value) or ""
    if not normalized:
        return False
    # 至少包含一个字母/汉字 + 一个数字
    if not re.search(r"[A-Z一-鿿]", normalized, re.IGNORECASE):
        return False
    if not re.search(r"\d", normalized):
        return False
    if not PLAUSIBLE_PATTERN.match(normalized):
        return False
    return True
