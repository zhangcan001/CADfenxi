from fastapi.testclient import TestClient

from backend.main import app
from dwg_test_helpers import clear_converter_tables, write_mock_converter


def test_save_converter_setting_success(tmp_path):
    clear_converter_tables()
    converter = write_mock_converter(tmp_path)
    with TestClient(app) as client:
        response = client.post(
            "/api/cad/converter-settings",
            json={
                "converter_name": "ODA File Converter",
                "converter_exe_path": str(converter),
                "output_version": "ACAD2018",
                "output_type": "DXF",
                "is_enabled": True,
            },
        )
        settings_response = client.get("/api/cad/converter-settings")

    assert response.status_code == 200
    assert response.json()["converter_exe_path"] == str(converter)
    assert settings_response.status_code == 200
    assert settings_response.json()[0]["output_type"] == "DXF"


def test_converter_check_not_found_returns_structured_error(tmp_path):
    clear_converter_tables()
    missing = tmp_path / "missing_converter.exe"
    with TestClient(app) as client:
        setting = client.post(
            "/api/cad/converter-settings",
            json={
                "converter_name": "Missing Converter",
                "converter_exe_path": str(missing),
                "output_version": "ACAD2018",
                "output_type": "DXF",
                "is_enabled": True,
            },
        ).json()
        response = client.post(f"/api/cad/converter-settings/{setting['id']}/check")

    assert response.status_code == 404
    assert response.json()["detail"]["error_code"] == "CONVERTER_NOT_FOUND"


def test_mock_converter_check_success(tmp_path):
    clear_converter_tables()
    converter = write_mock_converter(tmp_path)
    with TestClient(app) as client:
        setting = client.post(
            "/api/cad/converter-settings",
            json={
                "converter_name": "Mock Converter",
                "converter_exe_path": str(converter),
                "output_version": "ACAD2018",
                "output_type": "DXF",
                "is_enabled": True,
            },
        ).json()
        response = client.post(f"/api/cad/converter-settings/{setting['id']}/check")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
