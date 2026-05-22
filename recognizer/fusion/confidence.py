FIELD_WEIGHTS = {
    "drawing_no": 0.35,
    "drawing_name": 0.30,
    "discipline": 0.20,
    "issue_date": 0.10,
    "version": 0.05,
}


def calculate_confidence_score(field_confidences: dict[str, float]) -> int:
    score = 0.0
    for field_name, weight in FIELD_WEIGHTS.items():
        score += float(field_confidences.get(field_name, 0)) * weight
    return round(max(0, min(100, score)))


def calculate_trust_level(
    confidence_score: int,
    values: dict[str, str | None],
    issue_severities: list[str],
) -> str:
    has_error = "error" in issue_severities
    has_warning = "warning" in issue_severities
    has_core = all(values.get(field) for field in ["drawing_no", "drawing_name", "discipline"])

    if confidence_score < 50 or not values.get("drawing_no"):
        return "D"
    if confidence_score >= 90 and has_core and not has_error:
        return "A"
    if confidence_score >= 75 and values.get("drawing_no") and values.get("drawing_name") and not has_error:
        return "C" if has_warning else "B"
    return "C"
