from recognizer.cad_engine.cad_text_rules import infer_candidates_from_text
from recognizer.cad_engine.tag_mapper import field_for_tag
from recognizer.cad_engine.title_area import point_in_bbox, resolve_title_area
from recognizer.filename_parser.parser import parse_filename
from recognizer.normalizer.discipline import infer_discipline

CAD_SOURCE_TYPES = ["cad_text", "cad_mtext", "cad_block_attr", "cad_layer", "cad_filename"]

TITLE_AREA_BONUS = 15
OUT_OF_TITLE_AREA_PENALTY = 10


def generate_candidates_from_cad_json(cad_json: dict, context: dict) -> list[dict]:
    title_bbox = resolve_title_area(cad_json)
    candidates: list[dict] = []
    candidates.extend(extract_candidates_from_attribs(cad_json, context, title_bbox))
    candidates.extend(extract_candidates_from_cad_texts(cad_json, context, title_bbox))
    candidates.extend(extract_candidates_from_layers(cad_json, context))
    candidates.extend(extract_candidates_from_cad_filename(context["original_name"], context))
    return candidates


def extract_candidates_from_attribs(cad_json: dict, context: dict, title_bbox=None) -> list[dict]:
    candidates = []
    for space in cad_json.get("spaces", []):
        for insert in space.get("inserts", []):
            insert_in_title = point_in_bbox(insert.get("insert"), title_bbox)
            for attrib in insert.get("attribs", []):
                field_name = field_for_tag(attrib.get("tag"))
                if not field_name:
                    continue
                parsed = infer_candidates_from_text(
                    attrib.get("clean_text") or attrib.get("raw_text") or "",
                    "cad_block_attr",
                    tagged_field=field_name,
                )
                if field_name == "drawing_name":
                    parsed = [
                        item
                        for item in parsed
                        if not is_note_like_title(item.get("candidate_value") or item.get("raw_text") or "")
                    ]
                for candidate in parsed:
                    candidate["raw_text"] = f"{attrib.get('tag', '')}={attrib.get('clean_text') or attrib.get('raw_text') or ''}"
                    point = attrib.get("insert") or insert.get("insert")
                    apply_position_signal(candidate, point, title_bbox, attrib_in_title=insert_in_title)
                candidates.extend(parsed)
    return candidates


def extract_candidates_from_cad_texts(cad_json: dict, context: dict, title_bbox=None) -> list[dict]:
    candidates = []
    for space in cad_json.get("spaces", []):
        for item in space.get("texts", []):
            parsed = filter_text_candidates(infer_candidates_from_text(item.get("clean_text") or "", "cad_text"))
            for candidate in parsed:
                apply_position_signal(candidate, item.get("insert"), title_bbox)
            candidates.extend(parsed)
        for item in space.get("mtexts", []):
            parsed = filter_text_candidates(infer_candidates_from_text(item.get("clean_text") or "", "cad_mtext"))
            for candidate in parsed:
                apply_position_signal(candidate, item.get("insert"), title_bbox)
            candidates.extend(parsed)
    return candidates


def apply_position_signal(
    candidate: dict,
    point: list[float] | None,
    title_bbox: tuple[float, float, float, float] | None,
    *,
    attrib_in_title: bool | None = None,
) -> None:
    """根据候选所在位置调整置信度。同时把 bbox 写回 candidate 供融合层使用。

    只对原本中高置信度（>= 60）的候选加位置分，避免低质量值（如 normalize
    失败的日期）被位置救活。
    """
    if point is not None:
        candidate["bbox"] = list(point)
    if title_bbox is None:
        return
    in_title = attrib_in_title if attrib_in_title is not None else point_in_bbox(point, title_bbox)
    base = int(candidate.get("confidence") or 0)
    if in_title:
        if base >= 60:
            candidate["confidence"] = min(100, base + TITLE_AREA_BONUS)
        candidate["in_title_area"] = True
    else:
        if candidate.get("source_type") in {"cad_text", "cad_mtext"}:
            candidate["confidence"] = max(0, base - OUT_OF_TITLE_AREA_PENALTY)
        candidate["in_title_area"] = False


def extract_candidates_from_layers(cad_json: dict, context: dict) -> list[dict]:
    candidates = []
    for layer in cad_json.get("layers", []):
        discipline = infer_discipline(layer)
        if discipline:
            candidates.append(
                {
                    "field_name": "discipline",
                    "candidate_value": discipline,
                    "normalized_value": discipline,
                    "source_type": "cad_layer",
                    "confidence": 60,
                    "raw_text": layer,
                    "bbox": None,
                    "parser_name": "dxf_candidate_parser",
                    "parser_version": "v0.2.1",
                }
            )
    return candidates


def extract_candidates_from_cad_filename(original_name: str, context: dict) -> list[dict]:
    candidates = []
    for item in parse_filename(original_name):
        cloned = dict(item)
        cloned["source_type"] = "cad_filename"
        cloned["parser_name"] = "dxf_candidate_parser"
        cloned["parser_version"] = "v0.2.1"
        candidates.append(cloned)
    return candidates


def filter_text_candidates(candidates: list[dict]) -> list[dict]:
    return [
        candidate
        for candidate in candidates
        if not (
            candidate.get("field_name") == "drawing_name"
            and is_note_like_title(candidate.get("candidate_value") or candidate.get("raw_text") or "")
        )
    ]


def is_note_like_title(text: str) -> bool:
    value = (text or "").strip()
    return len(value) > 80 or any(
        keyword in value
        for keyword in [
            "总说明",
            "设计说明",
            "主要材料表",
            "材料表",
            "设备表",
            "门窗表",
            "图例",
            "备注",
            "说明",
            "详见",
            "参见",
            "按规范执行",
        ]
    )


def cad_json_has_attribs(cad_json: dict) -> bool:
    return any(
        insert.get("attribs")
        for space in cad_json.get("spaces", [])
        for insert in space.get("inserts", [])
    )


def cad_json_has_text(cad_json: dict) -> bool:
    return any(space.get("texts") or space.get("mtexts") for space in cad_json.get("spaces", []))
