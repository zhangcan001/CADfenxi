from recognizer.fusion.confidence import calculate_confidence_score, calculate_trust_level


def score_sheet(field_confidences: dict[str, float]) -> int:
    return calculate_confidence_score(field_confidences)


def trust_level(score: int, values: dict[str, str | None], severities: list[str]) -> str:
    return calculate_trust_level(score, values, severities)
