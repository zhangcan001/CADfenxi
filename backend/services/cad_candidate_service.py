from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from backend.core.config import settings
from backend.models.drawing_file import DrawingFile
from backend.models.drawing_sheet import DrawingSheet
from recognizer.cad_engine.cad_candidate_adapter import generate_candidates_from_cad_json
from recognizer.cad_engine.cad_json_writer import cad_parse_output_path, read_cad_json


def load_cad_candidates(db: Session, sheet: DrawingSheet, drawing_file: DrawingFile) -> list[dict]:
    output_path = cad_parse_output_path(settings.root_dir, sheet.project_id, sheet.id)
    if not output_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error_code": "CAD_PARSE_NOT_FOUND",
                "message": "未找到 CAD 解析结果，请先执行 DXF 解析。",
            },
        )
    cad_json = read_cad_json(output_path)
    return generate_candidates_from_cad_json(
        cad_json,
        {
            "project_id": sheet.project_id,
            "batch_id": sheet.batch_id,
            "file_id": sheet.file_id,
            "sheet_id": sheet.id,
            "original_name": drawing_file.original_name,
        },
    )
