import hashlib
from pathlib import Path

from fastapi.testclient import TestClient

from backend.core.config import settings
from backend.main import app

PDF_BYTES = b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF\n"


def create_project(client: TestClient, name: str = "上传测试项目") -> int:
    response = client.post("/api/projects", json={"name": name})
    assert response.status_code == 201
    return response.json()["id"]


def pdf_file(name: str = "drawing.pdf", content: bytes = PDF_BYTES):
    return ("files", (name, content, "application/pdf"))


def dxf_file(name: str = "drawing.dxf", content: bytes = b"0\nSECTION\n2\nENTITIES\n0\nENDSEC\n0\nEOF\n"):
    return ("files", (name, content, "application/dxf"))


def test_upload_single_pdf_success():
    with TestClient(app) as client:
        project_id = create_project(client)
        response = client.post(
            f"/api/projects/{project_id}/imports",
            data={"batch_name": "第一次导入", "remark": "测试备注"},
            files=[pdf_file("建筑施工图.pdf")],
        )

    assert response.status_code == 201
    data = response.json()
    assert data["project_id"] == project_id
    assert data["batch_name"] == "第一次导入"
    assert data["file_count"] == 1
    assert data["sheet_count"] == 0
    assert data["files"][0]["original_name"] == "建筑施工图.pdf"
    assert data["files"][0]["file_ext"] == ".pdf"
    assert data["files"][0]["source_format"] == "pdf"
    assert data["files"][0]["status"] == "imported"


def test_upload_single_dxf_success_without_creating_sheets():
    with TestClient(app) as client:
        project_id = create_project(client)
        response = client.post(
            f"/api/projects/{project_id}/imports",
            files=[dxf_file("总平面.dxf")],
        )
        batch_id = response.json()["id"]
        split_response = client.post(f"/api/imports/{batch_id}/split")
        sheets_response = client.get(f"/api/projects/{project_id}/sheets")

    assert response.status_code == 201
    data = response.json()
    assert data["file_count"] == 1
    assert data["sheet_count"] == 0
    assert data["files"][0]["original_name"] == "总平面.dxf"
    assert data["files"][0]["file_ext"] == ".dxf"
    assert data["files"][0]["source_format"] == "dxf"
    assert data["files"][0]["page_count"] == 0
    assert split_response.status_code == 200
    assert split_response.json()["sheet_count"] == 0
    assert sheets_response.json()["total"] == 0


def test_upload_dwg_success_with_pending_conversion():
    with TestClient(app) as client:
        project_id = create_project(client)
        response = client.post(
            f"/api/projects/{project_id}/imports",
            files=[("files", ("drawing.dwg", b"dwg", "application/acad"))],
        )

    assert response.status_code == 201
    file = response.json()["files"][0]
    assert file["file_ext"] == ".dwg"
    assert file["source_format"] == "dwg"
    assert file["convert_status"] == "pending"


def test_upload_multiple_pdfs_success():
    with TestClient(app) as client:
        project_id = create_project(client)
        response = client.post(
            f"/api/projects/{project_id}/imports",
            files=[
                pdf_file("a.pdf", b"%PDF-1.4\na\n%%EOF\n"),
                pdf_file("b.pdf", b"%PDF-1.4\nb\n%%EOF\n"),
            ],
        )

    assert response.status_code == 201
    assert response.json()["file_count"] == 2
    assert len(response.json()["files"]) == 2


def test_upload_unsupported_file_returns_import_item():
    with TestClient(app) as client:
        project_id = create_project(client)
        response = client.post(
            f"/api/projects/{project_id}/imports",
            files=[("files", ("note.txt", b"hello", "text/plain"))],
        )

    assert response.status_code == 201
    data = response.json()
    assert data["total_selected"] == 1
    assert data["imported_count"] == 0
    assert data["unsupported_count"] == 1
    assert data["file_type_counts"]["unsupported"] == 1
    assert data["items"][0]["status"] == "unsupported"
    assert data["items"][0]["error_code"] == "UNSUPPORTED_FILE_TYPE"


def test_upload_empty_file_list_fails():
    with TestClient(app) as client:
        project_id = create_project(client)
        response = client.post(f"/api/projects/{project_id}/imports")

    assert response.status_code == 400


def test_upload_missing_project_returns_404():
    with TestClient(app) as client:
        response = client.post(
            "/api/projects/999999/imports",
            files=[pdf_file("missing.pdf")],
        )

    assert response.status_code == 404


def test_import_batch_record_is_correct():
    with TestClient(app) as client:
        project_id = create_project(client)
        upload_response = client.post(
            f"/api/projects/{project_id}/imports",
            data={"batch_name": "批次记录测试"},
            files=[pdf_file()],
        )
        batch_id = upload_response.json()["id"]
        response = client.get(f"/api/imports/{batch_id}")

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == batch_id
    assert data["project_id"] == project_id
    assert data["file_count"] == 1
    assert data["recognized_count"] == 0


def test_drawing_file_record_is_correct():
    with TestClient(app) as client:
        project_id = create_project(client)
        client.post(
            f"/api/projects/{project_id}/imports",
            files=[pdf_file("record.pdf")],
        )
        response = client.get(f"/api/projects/{project_id}/files")

    assert response.status_code == 200
    files = response.json()
    assert files[0]["project_id"] == project_id
    assert files[0]["original_name"] == "record.pdf"
    assert files[0]["source_format"] == "pdf"
    assert files[0]["page_count"] == 0
    assert files[0]["batch_id"] is not None


def test_original_file_saved_to_project_original_dir():
    with TestClient(app) as client:
        project_id = create_project(client)
        response = client.post(
            f"/api/projects/{project_id}/imports",
            files=[pdf_file("save-path.pdf")],
        )

    storage_path = response.json()["files"][0]["storage_path"]
    saved_path = settings.root_dir / storage_path
    assert saved_path.exists()
    assert saved_path.parent == settings.projects_dir / f"project_{project_id}" / "original"


def test_file_hash_is_generated_correctly():
    content = b"%PDF-1.4\nhash test\n%%EOF\n"
    with TestClient(app) as client:
        project_id = create_project(client)
        response = client.post(
            f"/api/projects/{project_id}/imports",
            files=[pdf_file("hash.pdf", content)],
        )

    assert response.json()["files"][0]["file_hash"] == hashlib.sha256(content).hexdigest()


def test_duplicate_upload_returns_warning():
    with TestClient(app) as client:
        project_id = create_project(client)
        client.post(
            f"/api/projects/{project_id}/imports",
            files=[pdf_file("first.pdf", PDF_BYTES)],
        )
        response = client.post(
            f"/api/projects/{project_id}/imports",
            files=[pdf_file("second.pdf", PDF_BYTES)],
        )

    assert response.status_code == 201
    data = response.json()
    assert data["duplicate_count"] == 1
    assert data["items"][0]["status"] == "duplicate"
    assert data["items"][0]["warning"] == "duplicate_file"


def test_get_import_batch_returns_files():
    with TestClient(app) as client:
        project_id = create_project(client)
        upload_response = client.post(
            f"/api/projects/{project_id}/imports",
            files=[pdf_file("detail.pdf")],
        )
        batch_id = upload_response.json()["id"]
        response = client.get(f"/api/imports/{batch_id}")

    assert response.status_code == 200
    assert len(response.json()["files"]) == 1


def test_get_project_files_returns_list():
    with TestClient(app) as client:
        project_id = create_project(client)
        client.post(
            f"/api/projects/{project_id}/imports",
            files=[pdf_file("list.pdf")],
        )
        response = client.get(f"/api/projects/{project_id}/files")

    assert response.status_code == 200
    assert len(response.json()) >= 1
