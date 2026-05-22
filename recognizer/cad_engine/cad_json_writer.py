import json
from pathlib import Path


def cad_parse_output_path(root_dir: Path, project_id: int, sheet_id: int) -> Path:
    return (
        root_dir
        / "app_data"
        / "projects"
        / f"project_{project_id}"
        / "cad"
        / "parsed"
        / f"sheet_{sheet_id}_dxf_parse.json"
    )


def write_cad_json(data: dict, output_path: Path) -> str:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return output_path.as_posix()


def read_cad_json(output_path: Path) -> dict:
    return json.loads(output_path.read_text(encoding="utf-8"))
