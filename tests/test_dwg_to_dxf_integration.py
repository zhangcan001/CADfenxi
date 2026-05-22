from fastapi.testclient import TestClient

from backend.main import app
from dwg_test_helpers import (
    clear_converter_tables,
    create_converter_setting,
    create_project,
    upload_dwg,
    upload_dxf,
    write_mock_converter,
)


def test_unconverted_dwg_parse_dxf_returns_dwg_not_converted():
    clear_converter_tables()
    with TestClient(app) as client:
        project_id = create_project(client)
        upload = upload_dwg(client, project_id)
        response = client.post(f"/api/files/{upload['files'][0]['id']}/parse-dxf")

    assert response.status_code == 400
    assert response.json()["detail"]["error_code"] == "DWG_NOT_CONVERTED"


def test_converted_dwg_can_enter_parse_dxf_flow(tmp_path):
    clear_converter_tables()
    converter = write_mock_converter(tmp_path)
    with TestClient(app) as client:
        create_converter_setting(client, converter)
        project_id = create_project(client)
        upload = upload_dwg(client, project_id, "parse-after-convert.dwg")
        file_id = upload["files"][0]["id"]
        convert_response = client.post(f"/api/files/{file_id}/convert-dwg-to-dxf")
        parse_response = client.post(f"/api/files/{file_id}/parse-dxf")

    assert convert_response.status_code == 200
    assert parse_response.status_code == 200
    assert parse_response.json()["status"] == "success"
    assert parse_response.json()["counts"]["text_count"] == 1


def test_pdf_dxf_old_flow_still_accepts_dxf_parse():
    clear_converter_tables()
    with TestClient(app) as client:
        project_id = create_project(client)
        upload = upload_dxf(client, project_id, "old-flow.dxf")
        response = client.post(f"/api/files/{upload['files'][0]['id']}/parse-dxf")

    assert response.status_code == 200
    assert response.json()["status"] == "success"
