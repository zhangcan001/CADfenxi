from pathlib import Path

import pymupdf as fitz
from fastapi.testclient import TestClient

from backend.core.config import settings
from backend.main import app


def make_pdf_bytes(page_count: int) -> bytes:
    document = fitz.open()
    for index in range(page_count):
        page = document.new_page(width=300, height=220)
        page.insert_text((72, 72), f"Test page {index + 1}", fontsize=14)
    data = document.tobytes()
    document.close()
    return data


def create_project(client: TestClient, name: str = "拆页测试项目") -> int:
    response = client.post("/api/projects", json={"name": name})
    assert response.status_code == 201
    return response.json()["id"]


def upload_pdf(client: TestClient, project_id: int, page_count: int, name: str) -> dict:
    response = client.post(
        f"/api/projects/{project_id}/imports",
        data={"batch_name": f"{name} 批次"},
        files=[("files", (name, make_pdf_bytes(page_count), "application/pdf"))],
    )
    assert response.status_code == 201
    return response.json()


def test_split_single_page_pdf_creates_one_sheet():
    with TestClient(app) as client:
        project_id = create_project(client)
        upload = upload_pdf(client, project_id, 1, "single.pdf")
        file_id = upload["files"][0]["id"]
        response = client.post(f"/api/files/{file_id}/split")

    assert response.status_code == 200
    data = response.json()
    assert data["page_count"] == 1
    assert data["created_count"] == 1
    assert len(data["sheets"]) == 1


def test_split_multi_page_pdf_creates_n_sheets():
    with TestClient(app) as client:
        project_id = create_project(client)
        upload = upload_pdf(client, project_id, 3, "multi.pdf")
        file_id = upload["files"][0]["id"]
        response = client.post(f"/api/files/{file_id}/split")

    assert response.status_code == 200
    assert response.json()["page_count"] == 3
    assert len(response.json()["sheets"]) == 3


def test_drawing_file_page_count_is_updated():
    with TestClient(app) as client:
        project_id = create_project(client)
        upload = upload_pdf(client, project_id, 2, "page-count.pdf")
        file_id = upload["files"][0]["id"]
        client.post(f"/api/files/{file_id}/split")
        files_response = client.get(f"/api/projects/{project_id}/files")

    file_record = next(item for item in files_response.json() if item["id"] == file_id)
    assert file_record["page_count"] == 2


def test_sheet_page_no_starts_from_one():
    with TestClient(app) as client:
        project_id = create_project(client)
        upload = upload_pdf(client, project_id, 2, "page-no.pdf")
        response = client.post(f"/api/files/{upload['files'][0]['id']}/split")

    assert [sheet["page_no"] for sheet in response.json()["sheets"]] == [1, 2]


def test_preview_and_thumbnail_files_exist():
    with TestClient(app) as client:
        project_id = create_project(client)
        upload = upload_pdf(client, project_id, 1, "images.pdf")
        response = client.post(f"/api/files/{upload['files'][0]['id']}/split")

    sheet = response.json()["sheets"][0]
    assert (settings.root_dir / sheet["preview_path"]).exists()
    assert (settings.root_dir / sheet["thumbnail_path"]).exists()


def test_get_project_sheets_returns_list():
    with TestClient(app) as client:
        project_id = create_project(client)
        upload = upload_pdf(client, project_id, 1, "list-sheets.pdf")
        client.post(f"/api/files/{upload['files'][0]['id']}/split")
        response = client.get(f"/api/projects/{project_id}/sheets")

    assert response.status_code == 200
    assert len(response.json()["items"]) >= 1
    assert response.json()["items"][0]["original_file_name"] == "list-sheets.pdf"


def test_get_sheet_detail_returns_detail():
    with TestClient(app) as client:
        project_id = create_project(client)
        upload = upload_pdf(client, project_id, 1, "detail-sheet.pdf")
        split = client.post(f"/api/files/{upload['files'][0]['id']}/split")
        sheet_id = split.json()["sheets"][0]["id"]
        response = client.get(f"/api/sheets/{sheet_id}")

    assert response.status_code == 200
    assert response.json()["id"] == sheet_id
    assert response.json()["original_file_name"] == "detail-sheet.pdf"


def test_get_sheet_preview_returns_image():
    with TestClient(app) as client:
        project_id = create_project(client)
        upload = upload_pdf(client, project_id, 1, "preview.pdf")
        split = client.post(f"/api/files/{upload['files'][0]['id']}/split")
        sheet_id = split.json()["sheets"][0]["id"]
        response = client.get(f"/api/sheets/{sheet_id}/preview")

    assert response.status_code == 200
    assert response.headers["content-type"] == "image/png"


def test_get_sheet_thumbnail_returns_image():
    with TestClient(app) as client:
        project_id = create_project(client)
        upload = upload_pdf(client, project_id, 1, "thumbnail.pdf")
        split = client.post(f"/api/files/{upload['files'][0]['id']}/split")
        sheet_id = split.json()["sheets"][0]["id"]
        response = client.get(f"/api/sheets/{sheet_id}/thumbnail")

    assert response.status_code == 200
    assert response.headers["content-type"] == "image/jpeg"


def test_repeated_split_does_not_duplicate_sheets():
    with TestClient(app) as client:
        project_id = create_project(client)
        upload = upload_pdf(client, project_id, 2, "repeat.pdf")
        file_id = upload["files"][0]["id"]
        first = client.post(f"/api/files/{file_id}/split")
        second = client.post(f"/api/files/{file_id}/split")
        sheets = client.get(f"/api/projects/{project_id}/sheets?file_id={file_id}")

    assert first.status_code == 200
    assert second.status_code == 200
    assert second.json()["created_count"] == 0
    assert len(sheets.json()["items"]) == 2


def test_missing_file_split_returns_404():
    with TestClient(app) as client:
        response = client.post("/api/files/999999/split")

    assert response.status_code == 404


def test_missing_batch_split_returns_404():
    with TestClient(app) as client:
        response = client.post("/api/imports/999999/split")

    assert response.status_code == 404


def test_split_batch_updates_sheet_count():
    with TestClient(app) as client:
        project_id = create_project(client)
        upload = upload_pdf(client, project_id, 2, "batch.pdf")
        batch_id = upload["id"]
        response = client.post(f"/api/imports/{batch_id}/split")
        detail = client.get(f"/api/imports/{batch_id}")

    assert response.status_code == 200
    assert response.json()["sheet_count"] == 2
    assert detail.json()["sheet_count"] == 2
