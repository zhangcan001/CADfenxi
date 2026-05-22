from recognizer.cad_engine.geometry import dxf_get, entity_handle, point_to_list
from recognizer.cad_engine.text_cleaning import clean_cad_text


def extract_insert(entity) -> dict | None:
    try:
        attribs = []
        try:
            attrib_entities = list(entity.attribs)
        except Exception:
            attrib_entities = []
        for attrib in attrib_entities:
            parsed_attrib = extract_attrib(attrib)
            if parsed_attrib is not None:
                attribs.append(parsed_attrib)
        return {
            "block_name": dxf_get(entity, "name", ""),
            "layer": dxf_get(entity, "layer", ""),
            "insert": point_to_list(dxf_get(entity, "insert", (0, 0, 0))),
            "rotation": float(dxf_get(entity, "rotation", 0) or 0),
            "xscale": float(dxf_get(entity, "xscale", 1) or 1),
            "yscale": float(dxf_get(entity, "yscale", 1) or 1),
            "handle": entity_handle(entity),
            "attribs": attribs,
        }
    except Exception:
        return None


def extract_attrib(entity) -> dict | None:
    try:
        raw_text = dxf_get(entity, "text", "")
        clean_text = clean_cad_text(raw_text)
        if not clean_text:
            return None
        return {
            "tag": dxf_get(entity, "tag", ""),
            "raw_text": raw_text,
            "clean_text": clean_text,
            "layer": dxf_get(entity, "layer", ""),
            "insert": point_to_list(dxf_get(entity, "insert", (0, 0, 0))),
            "height": float(dxf_get(entity, "height", 0) or 0),
            "handle": entity_handle(entity),
        }
    except Exception:
        return None
