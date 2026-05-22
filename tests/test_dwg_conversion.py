from fastapi.testclient import TestClient

from backend.core.config import settings
from backend.main import app
from dwg_test_helpers import (
    clear_converter_tables,
    create_converter_setting,
    create_project,
    upload_dwg,
    write_mock_converter,
)


def test_dwg_upload_sets_source_format_and_pending_status():
    clear_converter_tables()
    with TestClient(app) as client:
        project_id = create_project(client)
        upload = upload_dwg(client, project_id)

    file = upload["files"][0]
    assert file["file_ext"] == ".dwg"
    assert file["source_format"] == "dwg"
    assert file["convert_status"] == "pending"


def test_convert_without_config_returns_structured_error():
    clear_converter_tables()
    with TestClient(app) as client:
        project_id = create_project(client)
        upload = upload_dwg(client, project_id)
        response = client.post(f"/api/files/{upload['files'][0]['id']}/convert-dwg-to-dxf")

    assert response.status_code == 400
    assert response.json()["detail"]["error_code"] == "CONVERTER_NOT_CONFIGURED"


def test_single_dwg_convert_success_writes_converted_path_and_run(tmp_path):
    clear_converter_tables()
    converter = write_mock_converter(tmp_path)
    with TestClient(app) as client:
        create_converter_setting(client, converter)
        project_id = create_project(client)
        upload = upload_dwg(client, project_id, "convert-me.dwg")
        file_id = upload["files"][0]["id"]
        response = client.post(f"/api/files/{file_id}/convert-dwg-to-dxf")
        files_response = client.get(f"/api/projects/{project_id}/files")
        runs_response = client.get(f"/api/files/{file_id}/cad-conversion-runs")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["converted_file_path"].startswith(f"app_data/projects/project_{project_id}/converted/")
    assert (settings.root_dir / data["converted_file_path"]).exists()
    file = next(item for item in files_response.json() if item["id"] == file_id)
    assert file["convert_status"] == "success"
    assert file["converted_file_path"] == data["converted_file_path"]
    assert runs_response.json()[0]["status"] == "success"


def test_converter_non_zero_records_failed_run(tmp_path):
    clear_converter_tables()
    converter = write_mock_converter(tmp_path, "failed")
    with TestClient(app) as client:
        create_converter_setting(client, converter)
        project_id = create_project(client)
        upload = upload_dwg(client, project_id, "fail-me.dwg")
        file_id = upload["files"][0]["id"]
        response = client.post(f"/api/files/{file_id}/convert-dwg-to-dxf")
        runs_response = client.get(f"/api/files/{file_id}/cad-conversion-runs")

    assert response.status_code == 200
    assert response.json()["status"] == "failed"
    assert response.json()["error_code"] == "DWG_CONVERT_FAILED"
    assert runs_response.json()[0]["error_code"] == "DWG_CONVERT_FAILED"


def test_converter_success_without_output_returns_missing_output(tmp_path):
    clear_converter_tables()
    converter = write_mock_converter(tmp_path, "missing_output")
    with TestClient(app) as client:
        create_converter_setting(client, converter)
        project_id = create_project(client)
        upload = upload_dwg(client, project_id, "missing-output.dwg")
        file_id = upload["files"][0]["id"]
        response = client.post(f"/api/files/{file_id}/convert-dwg-to-dxf")

    assert response.status_code == 200
    assert response.json()["status"] == "failed"
    assert response.json()["error_code"] == "DWG_CONVERT_OUTPUT_MISSING"


def test_batch_convert_continues_after_single_failure(tmp_path):
    clear_converter_tables()
    converter = tmp_path / "selective_converter.py"
    converter.write_text(
        """
import sys
from pathlib import Path

DXF = "0\\nSECTION\\n2\\nENTITIES\\n0\\nENDSEC\\n0\\nEOF\\n"
if len(sys.argv) == 1:
    raise SystemExit(0)
input_dir = Path(sys.argv[1])
output_dir = Path(sys.argv[2])
output_dir.mkdir(parents=True, exist_ok=True)
for source in input_dir.glob("*.dwg"):
    if "bad" in source.name:
        continue
    (output_dir / (source.stem + ".dxf")).write_text(DXF, encoding="utf-8")
raise SystemExit(0)
""".strip()
        + "\n",
        encoding="utf-8",
    )
    with TestClient(app) as client:
        create_converter_setting(client, converter)
        project_id = create_project(client)
        response = client.post(
            f"/api/projects/{project_id}/imports",
            files=[
                ("files", ("good.dwg", b"dwg", "application/acad")),
                ("files", ("bad.dwg", b"dwg", "application/acad")),
            ],
        )
        batch_id = response.json()["id"]
        result = client.post(f"/api/imports/{batch_id}/convert-dwg-to-dxf")

    assert result.status_code == 200
    data = result.json()
    assert data["total_count"] == 2
    assert data["success_count"] == 1
    assert data["failed_count"] == 1
