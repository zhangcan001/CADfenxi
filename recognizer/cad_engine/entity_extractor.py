from datetime import datetime, timezone

import ezdxf

from recognizer.cad_engine.block_extractor import extract_insert
from recognizer.cad_engine.layer_extractor import extract_layers
from recognizer.cad_engine.mtext_extractor import extract_mtext
from recognizer.cad_engine.text_extractor import extract_text


def extract_cad_entities(
    document,
    *,
    project_id: int,
    file_id: int,
    sheet_id: int,
    source_file: str,
    warnings: list[str] | None = None,
) -> dict:
    modelspace = document.modelspace()
    texts = []
    mtexts = []
    inserts = []

    for entity in modelspace:
        try:
            entity_type = entity.dxftype()
        except Exception:
            continue
        if entity_type == "TEXT":
            parsed_text = extract_text(entity)
            if parsed_text is not None:
                texts.append(parsed_text)
        elif entity_type == "MTEXT":
            parsed_mtext = extract_mtext(entity)
            if parsed_mtext is not None:
                mtexts.append(parsed_mtext)
        elif entity_type == "INSERT":
            parsed_insert = extract_insert(entity)
            if parsed_insert is not None:
                inserts.append(parsed_insert)

    layers = extract_layers(document)
    attrib_count = sum(len(insert.get("attribs", [])) for insert in inserts)
    return {
        "project_id": project_id,
        "file_id": file_id,
        "sheet_id": sheet_id,
        "engine": "ezdxf",
        "engine_version": ezdxf.__version__,
        "source_file": source_file,
        "spaces": [
            {
                "space": "modelspace",
                "layout_name": None,
                "texts": texts,
                "mtexts": mtexts,
                "inserts": inserts,
            }
        ],
        "layers": layers,
        "counts": {
            "text_count": len(texts),
            "mtext_count": len(mtexts),
            "insert_count": len(inserts),
            "attrib_count": attrib_count,
            "layer_count": len(layers),
        },
        "warnings": warnings or [],
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
