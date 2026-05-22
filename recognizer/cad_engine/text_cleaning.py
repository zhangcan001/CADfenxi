import re

CONTROL_CHARS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
WHITESPACE = re.compile(r"\s+")
MTEXT_FORMAT_GROUP = re.compile(r"\{\\[^;{}]*;([^{}]*)\}")


def clean_cad_text(text: str | None) -> str:
    if text is None:
        return ""
    value = str(text)
    value = value.replace("\\P", " ").replace("\\p", " ")
    value = value.replace("\\~", " ")
    value = value.replace("\\{", "{").replace("\\}", "}")
    value = MTEXT_FORMAT_GROUP.sub(r"\1", value)
    value = re.sub(r"\\[A-Za-z][^;]*;", "", value)
    value = re.sub(r"\\[A-Za-z]", "", value)
    value = value.replace("{", "").replace("}", "")
    value = CONTROL_CHARS.sub("", value)
    value = WHITESPACE.sub(" ", value)
    return value.strip()
