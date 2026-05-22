from fastapi.testclient import TestClient

from backend.main import app

PDF_BYTES = b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF\n"
DXF_BYTES = b"0\nSECTION\n2\nENTITIES\n0\nENDSEC\n0\nEOF\n"


def create_project(client: TestClient, name: str = "DXF 图纸页准备测试") -> int:
    response = client.post("/api/projects", json={"name": name})
    assert response.status_code == 201
    return response.json()["id"]


def upload_files(client: TestClient, project_id: int, files: list[tuple]) -> dict:
    response = client.post(f"/api/projects/{project_id}/imports", files=files)
    assert response.status_code == 201
    return response.json()


def dxf_file(name: str = "drawing.dxf", content: bytes = DXF_BYTES):
    return ("files", (name, content, "application/dxf"))


def pdf_file(name: str = "drawing.pdf", content: bytes = PDF_BYTES):
    return ("files", (name, content, "application/pdf"))


def test_prepare_dxf_sheet_creates_sheet_with_cad_pending_fields():
    with TestClient(app) as client:
        project_id = create_project(client)
        upload = upload_files(client, project_id, [dxf_file("cad-a.dxf")])
        file_id = upload["files"][0]["id"]

        response = client.post(f"/api/files/{file_id}/prepare-dxf-sheet")
        sheets_response = client.get(f"/api/projects/{project_id}/sheets")
        file_response = client.get(f"/api/projects/{project_id}/files")

    assert response.status_code == 200
    data = response.json()
    assert data["file_id"] == file_id
    assert data["project_id"] == project_id
    assert data["batch_id"] == upload["id"]
    assert data["page_no"] == 1
    assert data["sheet_type"] == "drawing"
    assert data["status"] == "cad_pending"
    assert data["review_status"] == "unreviewed"
    assert data["created"] is True

    sheets = sheets_response.json()["items"]
    assert len(sheets) == 1
    sheet = sheets[0]
    assert sheet["id"] == data["sheet_id"]
    assert sheet["file_id"] == file_id
    assert sheet["page_no"] == 1
    assert sheet["sheet_type"] == "drawing"
    assert sheet["status"] == "cad_pending"
    assert sheet["review_status"] == "unreviewed"
    assert sheet["source_format"] == "dxf"
    assert sheet["preview_path"] is None
    assert sheet["thumbnail_path"] is None
    assert sheet["title_crop_path"] is None
    assert file_response.json()[0]["status"] == "cad_pending"


def test_prepare_dxf_sheet_is_idempotent():
    with TestClient(app) as client:
        project_id = create_project(client)
        upload = upload_files(client, project_id, [dxf_file("cad-repeat.dxf")])
        file_id = upload["files"][0]["id"]

        first = client.post(f"/api/files/{file_id}/prepare-dxf-sheet")
        second = client.post(f"/api/files/{file_id}/prepare-dxf-sheet")
        sheets_response = client.get(f"/api/projects/{project_id}/sheets")

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["sheet_id"] == second.json()["sheet_id"]
    assert first.json()["created"] is True
    assert second.json()["created"] is False
    assert sheets_response.json()["total"] == 1


def test_prepare_dxf_sheet_rejects_pdf_with_structured_error():
    with TestClient(app) as client:
        project_id = create_project(client)
        upload = upload_files(client, project_id, [pdf_file("not-cad.pdf")])
        file_id = upload["files"][0]["id"]

        response = client.post(f"/api/files/{file_id}/prepare-dxf-sheet")

    assert response.status_code == 400
    assert response.json()["detail"]["error_code"] == "UNSUPPORTED_CAD_FORMAT"


def test_prepare_dxf_sheet_missing_file_returns_404():
    with TestClient(app) as client:
        response = client.post("/api/files/999999999/prepare-dxf-sheet")

    assert response.status_code == 404


def test_prepare_dxf_sheets_for_batch_creates_only_dxf_sheets():
    with TestClient(app) as client:
        project_id = create_project(client)
        upload = upload_files(
            client,
            project_id,
            [dxf_file("cad-1.dxf"), pdf_file("skip.pdf"), dxf_file("cad-2.dxf")],
        )

        first = client.post(f"/api/imports/{upload['id']}/prepare-dxf-sheets")
        second = client.post(f"/api/imports/{upload['id']}/prepare-dxf-sheets")
        sheets_response = client.get(f"/api/projects/{project_id}/sheets")

    assert first.status_code == 200
    assert first.json()["batch_id"] == upload["id"]
    assert first.json()["total_dxf_count"] == 2
    assert first.json()["created_count"] == 2
    assert first.json()["existing_count"] == 0
    assert first.json()["failed_count"] == 0
    assert len(first.json()["items"]) == 2

    assert second.status_code == 200
    assert second.json()["created_count"] == 0
    assert second.json()["existing_count"] == 2
    assert sheets_response.json()["total"] == 2
    assert {item["source_format"] for item in sheets_response.json()["items"]} == {"dxf"}


def test_prepare_dxf_sheets_missing_batch_returns_404():
    with TestClient(app) as client:
        response = client.post("/api/imports/999999999/prepare-dxf-sheets")

    assert response.status_code == 404
