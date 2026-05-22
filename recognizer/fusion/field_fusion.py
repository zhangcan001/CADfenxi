from dataclasses import dataclass

SOURCE_PRIORITY = {
    "manual": 0,
    "cad_block_attr": 1,
    "pdf_text": 2,
    "title_ocr": 3,
    "cad_text": 4,
    "cad_mtext": 4,
    "filename": 5,
    "cad_filename": 6,
    "rule": 7,
    "cad_layer": 8,
}

CAD_SOURCE_TYPES = {"cad_block_attr", "cad_text", "cad_mtext", "cad_layer", "cad_filename"}
MACHINE_SOURCE_TYPES = set(SOURCE_PRIORITY) - {"manual"}


@dataclass
class FusionChoice:
    raw_value: str
    normalized_value: str | None
    display_value: str
    final_source: str
    confidence: float
    evidence_ids: list[int]
    conflict: bool
    conflict_sources: list[str]


def value_key(candidate) -> str:
    return (candidate.normalized_value or candidate.candidate_value or "").strip()


def choose_field_value(candidates: list) -> FusionChoice | None:
    usable = [candidate for candidate in candidates if value_key(candidate)]
    if not usable:
        return None

    groups: dict[str, list] = {}
    for candidate in usable:
        groups.setdefault(value_key(candidate), []).append(candidate)

    _best_key, best_group = min(
        groups.items(),
        key=lambda item: (
            min(SOURCE_PRIORITY.get(candidate.source_type, 99) for candidate in item[1]),
            -len(item[1]),
            -max(candidate.confidence for candidate in item[1]),
        ),
    )

    conflict = len(groups) > 1
    chosen = sorted(
        best_group,
        key=lambda candidate: (
            SOURCE_PRIORITY.get(candidate.source_type, 99),
            -candidate.confidence,
            candidate.id,
        ),
    )[0]
    confidence = max(candidate.confidence for candidate in best_group)
    final_source = chosen.source_type
    if len(best_group) > 1:
        confidence = min(100, confidence + min(15, 5 * (len(best_group) - 1)))
        final_source = "mixed"

    return FusionChoice(
        raw_value=chosen.candidate_value,
        normalized_value=chosen.normalized_value,
        display_value=chosen.normalized_value or chosen.candidate_value,
        final_source=final_source,
        confidence=confidence,
        evidence_ids=[candidate.id for candidate in best_group],
        conflict=conflict,
        conflict_sources=sorted({candidate.source_type for candidate in usable}),
    )
