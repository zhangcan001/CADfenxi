import re


COMPONENT_NO_PATTERN = re.compile(
    r"^(?:KZ|L|KL|WKL|M|C|D|W|MQ|GZ|CT|YBZ|门|窗)-?\d+$",
    re.IGNORECASE,
)
AXIS_NO_PATTERN = re.compile(r"^(?:轴\d+|\d+轴|[A-Z]轴)$", re.IGNORECASE)


def normalize_drawing_no(value: str) -> str | None:
    text = value.strip().replace("—", "-").replace("－", "-").replace("–", "-").replace("_", "-")
    text = re.sub(r"\s+", "-", text)
    text = re.sub(r"-+", "-", text).strip("-")
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
    return text or None


def is_component_or_axis_no(value: str) -> bool:
    text = value.strip().replace(" ", "").replace("_", "-").replace("—", "-").replace("－", "-").replace("–", "-")
    return bool(COMPONENT_NO_PATTERN.match(text) or AXIS_NO_PATTERN.match(text))


def is_supported_drawing_no(value: str) -> bool:
    normalized = normalize_drawing_no(value) or ""
    if is_component_or_axis_no(normalized):
        return False
    patterns = [
        r"^(建施总|建施|建总|结施|水施|电施|暖施|弱电|消防|总施|设总|室外|建筑|结构|给排水|电气|暖通)(?:-[A-Z])?-\d{1,4}$",
        r"^(JS|JZ|JG|GS|SS|DS|NT|XS|RD|PL|LA)-\d{1,4}$",
        r"^[ASEMPT]-\d{2,4}$",
    ]
    return any(re.match(pattern, normalized, re.IGNORECASE) for pattern in patterns)
