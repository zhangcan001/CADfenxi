import re


def normalize_version(value: str) -> str | None:
    text = value.strip()
    match = re.search(r"^(?:版本)?([A-Z])版?$", text, re.IGNORECASE)
    if match:
        return match.group(1).upper()
    match = re.search(r"^Rev[.\s-]?(\w+)$", text, re.IGNORECASE)
    if match:
        return f"Rev.{match.group(1)}"
    match = re.search(r"^V\d+(?:\.\d+)?$", text, re.IGNORECASE)
    if match:
        return text.upper()
    return text or None
