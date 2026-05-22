from recognizer.normalizer.discipline import infer_discipline

PARSER_NAME = "discipline_rules"
PARSER_VERSION = "0.1.0"


def generate_discipline_candidates(texts: list[str]) -> list[dict]:
    joined = " ".join(text for text in texts if text)
    discipline = infer_discipline(joined)
    if not discipline:
        return []
    return [
        {
            "field_name": "discipline",
            "candidate_value": discipline,
            "normalized_value": discipline,
            "source_type": "rule",
            "confidence": 70,
            "raw_text": joined[:1000],
            "bbox": None,
            "parser_name": PARSER_NAME,
            "parser_version": PARSER_VERSION,
        }
    ]
