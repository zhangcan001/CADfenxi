from pathlib import Path

from fastapi.testclient import TestClient

from backend.core.database import SessionLocal, init_database
from backend.models.cad_conversion_run import CadConversionRun
from backend.models.converter_setting import ConverterSetting


DWG_BYTES = b"mock dwg bytes"
DXF_TEXT = "0\nSECTION\n2\nENTITIES\n0\nTEXT\n8\n0\n10\n0\n20\n0\n30\n0\n40\n2.5\n1\nA-001\n0\nENDSEC\n0\nEOF\n"


def create_project(client: TestClient, name: str = "DWG 转换测试") -> int:
    response = client.post("/api/projects", json={"name": name})
    assert response.status_code == 201
    return response.json()["id"]


def upload_dwg(client: TestClient, project_id: int, name: str = "sample.dwg") -> dict:
    response = client.post(
        f"/api/projects/{project_id}/imports",
        files=[("files", (name, DWG_BYTES, "application/acad"))],
    )
    assert response.status_code == 201
    return response.json()


def upload_dxf(client: TestClient, project_id: int, name: str = "sample.dxf") -> dict:
    response = client.post(
        f"/api/projects/{project_id}/imports",
        files=[("files", (name, DXF_TEXT.encode("utf-8"), "application/dxf"))],
    )
    assert response.status_code == 201
    return response.json()


def clear_converter_tables() -> None:
    init_database()
    with SessionLocal() as db:
        db.query(CadConversionRun).delete()
        db.query(ConverterSetting).delete()
        db.commit()


def write_mock_converter(tmp_path: Path, mode: str = "success") -> Path:
    script = tmp_path / f"mock_converter_{mode}.py"
    if mode == "success":
        body = f"""
import sys
from pathlib import Path

if len(sys.argv) == 1:
    raise SystemExit(0)
input_dir = Path(sys.argv[1])
output_dir = Path(sys.argv[2])
output_dir.mkdir(parents=True, exist_ok=True)
for source in input_dir.glob("*.dwg"):
    (output_dir / (source.stem + ".dxf")).write_text({DXF_TEXT!r}, encoding="utf-8")
raise SystemExit(0)
"""
    elif mode == "failed":
        body = """
import sys

if len(sys.argv) == 1:
    raise SystemExit(0)
print("mock converter failed", file=sys.stderr)
raise SystemExit(2)
"""
    else:
        body = """
import sys

if len(sys.argv) == 1:
    raise SystemExit(0)
raise SystemExit(0)
"""
    script.write_text(body.strip() + "\n", encoding="utf-8")
    return script


def create_converter_setting(client: TestClient, converter_path: Path) -> dict:
    response = client.post(
        "/api/cad/converter-settings",
        json={
            "converter_name": "Mock Converter",
            "converter_exe_path": str(converter_path),
            "output_version": "ACAD2018",
            "output_type": "DXF",
            "is_enabled": True,
        },
    )
    assert response.status_code == 200
    return response.json()
