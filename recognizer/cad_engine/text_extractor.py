import logging

from recognizer.cad_engine.geometry import dxf_get, entity_handle, point_to_list
from recognizer.cad_engine.text_cleaning import clean_cad_text

logger = logging.getLogger(__name__)


def extract_text(entity) -> dict | None:
    try:
        raw_text = dxf_get(entity, "text", "")
        clean_text = clean_cad_text(raw_text)
        if not clean_text:
            return None
        return {
            "type": "TEXT",
            "raw_text": raw_text,
            "clean_text": clean_text,
            "layer": dxf_get(entity, "layer", ""),
            "insert": point_to_list(dxf_get(entity, "insert", (0, 0, 0))),
            "height": float(dxf_get(entity, "height", 0) or 0),
            "rotation": float(dxf_get(entity, "rotation", 0) or 0),
            "handle": entity_handle(entity),
        }
    except (AttributeError, TypeError, ValueError) as exc:
        logger.debug("extract_text skipped entity %r: %s", entity, exc)
        return None
