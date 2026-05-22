import logging

from recognizer.cad_engine.geometry import dxf_get, entity_handle, point_to_list
from recognizer.cad_engine.text_cleaning import clean_cad_text

logger = logging.getLogger(__name__)


def extract_mtext(entity) -> dict | None:
    try:
        raw_text = dxf_get(entity, "text", "")
        try:
            plain_text = entity.plain_text()
        except (AttributeError, ValueError):
            plain_text = raw_text
        clean_text = clean_cad_text(plain_text)
        if not clean_text:
            return None
        return {
            "type": "MTEXT",
            "raw_text": raw_text,
            "clean_text": clean_text,
            "layer": dxf_get(entity, "layer", ""),
            "insert": point_to_list(dxf_get(entity, "insert", (0, 0, 0))),
            "char_height": float(dxf_get(entity, "char_height", 0) or 0),
            "handle": entity_handle(entity),
        }
    except (AttributeError, TypeError, ValueError) as exc:
        logger.debug("extract_mtext skipped entity %r: %s", entity, exc)
        return None
