from pathlib import Path

import pymupdf as fitz
from fastapi.testclient import TestClient

from backend.core.config import settings
from backend.core.database import SessionLocal
from backend.models.drawing_sheet import DrawingSheet
from backend.main import app


def make_pdf_bytes(page_count: int) -> bytes:
    document = fitz.open()
    for index in range(page_count):
        page = document.new_page(width=300, height=220)
        page.insert_text((72, 72), f"Title crop page {index + 1}", fontsize=14)
    data = document.tobytes()
    document.close()
    return data


def create_project(client: TestClient) -> int:
    response = client.post("/api/projects", json={"name": "标题栏裁剪测试项目"})
    assert response.status_code == 201
    return response.json()["id"]


def upload_and_split(client: TestClient, page_count: int = 1) -> tuple[int, int, list[dict]]:
    project_id = create_project(client)
    upload = client.post(
        f"/api/projects/{project_id}/imports",
        data={"batch_name": "标题栏裁剪批次"},
        files=[
            (
                "files",
                ("title-crop.pdf", make_pdf_bytes(page_count), "application/pdf"),
            )
        ],
    )
    assert upload.status_code == 201
    batch_id = upload.json()["id"]
    split = client.post(f"/api/imports/{batch_id}/split")
    assert split.status_code == 200
    return project_id, batch_id, split.json()["files"]


def first_sheet(client: TestClient, project_id: int) -> dict:
    response = client.get(f"/api/projects/{project_id}/sheets")
    assert response.status_code == 200
    assert response.json()["items"]
    return response.json()["items"][0]


def test_title_crop_single_sheet_success():
    with TestClient(app) as client:
        project_id, _, _ = upload_and_split(client)
        sheet = first_sheet(client, project_id)
        response = client.post(f"/api/sheets/{sheet['id']}/title-crop")

    assert response.status_code == 200
    data = response.json()
    assert data["sheet_id"] == sheet["id"]
    assert data["status"] == "success"
    assert data["title_crop_path"].endswith("_title.png")
    assert data["title_crop_bbox"]["width"] > 0


def test_title_crop_path_and_bbox_are_written_to_sheet():
    with TestClient(app) as client:
        project_id, _, _ = upload_and_split(client)
        sheet = first_sheet(client, project_id)
        client.post(f"/api/sheets/{sheet['id']}/title-crop")

    with SessionLocal() as db:
        stored = db.get(DrawingSheet, sheet["id"])
        assert stored is not None
        assert stored.title_crop_path
        assert stored.title_crop_bbox
        assert stored.title_crop_status == "success"


def test_title_crop_image_file_exists():
    with TestClient(app) as client:
        project_id, _, _ = upload_and_split(client)
        sheet = first_sheet(client, project_id)
        response = client.post(f"/api/sheets/{sheet['id']}/title-crop")

    crop_path = settings.root_dir / response.json()["title_crop_path"]
    assert crop_path.exists()
    assert crop_path.parent == settings.projects_dir / f"project_{project_id}" / "crops"


def test_get_title_crop_returns_png():
    with TestClient(app) as client:
        project_id, _, _ = upload_and_split(client)
        sheet = first_sheet(client, project_id)
        client.post(f"/api/sheets/{sheet['id']}/title-crop")
        response = client.get(f"/api/sheets/{sheet['id']}/title-crop")

    assert response.status_code == 200
    assert response.headers["content-type"] == "image/png"


def test_batch_title_crops_success():
    with TestClient(app) as client:
        _, batch_id, _ = upload_and_split(client, page_count=2)
        response = client.post(f"/api/imports/{batch_id}/title-crops")

    assert response.status_code == 200
    data = response.json()
    assert data["total_count"] == 2
    assert data["success_count"] == 2
    assert data["failed_count"] == 0


def test_repeated_title_crop_overwrites_same_record():
    with TestClient(app) as client:
        project_id, _, _ = upload_and_split(client)
        sheet = first_sheet(client, project_id)
        first = client.post(f"/api/sheets/{sheet['id']}/title-crop")
        second = client.post(f"/api/sheets/{sheet['id']}/title-crop")
        detail = client.get(f"/api/sheets/{sheet['id']}")

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["title_crop_path"] == second.json()["title_crop_path"]
    assert detail.json()["title_crop_path"] == first.json()["title_crop_path"]


def test_missing_sheet_returns_404():
    with TestClient(app) as client:
        response = client.post("/api/sheets/999999/title-crop")

    assert response.status_code == 404


def test_preview_not_found_returns_400():
    with TestClient(app) as client:
        project_id, _, _ = upload_and_split(client)
        sheet = first_sheet(client, project_id)

    with SessionLocal() as db:
        stored = db.get(DrawingSheet, sheet["id"])
        assert stored is not None
        stored.preview_path = None
        db.commit()

    with TestClient(app) as client:
        response = client.post(f"/api/sheets/{sheet['id']}/title-crop")

    assert response.status_code == 400
    assert response.json()["detail"]["error_code"] == "PREVIEW_NOT_FOUND"


def test_preview_file_missing_returns_400():
    with TestClient(app) as client:
        project_id, _, _ = upload_and_split(client)
        sheet = first_sheet(client, project_id)

    with SessionLocal() as db:
        stored = db.get(DrawingSheet, sheet["id"])
        assert stored is not None
        preview_path = settings.root_dir / stored.preview_path
        preview_path.unlink(missing_ok=True)
        db.commit()

    with TestClient(app) as client:
        response = client.post(f"/api/sheets/{sheet['id']}/title-crop")

    assert response.status_code == 400
    assert response.json()["detail"]["error_code"] == "PREVIEW_FILE_MISSING"


def test_batch_title_crop_single_failure_does_not_stop_other_pages():
    with TestClient(app) as client:
        project_id, batch_id, _ = upload_and_split(client, page_count=2)
        sheets = client.get(f"/api/projects/{project_id}/sheets").json()["items"]

    missing_sheet = sheets[0]
    with SessionLocal() as db:
        stored = db.get(DrawingSheet, missing_sheet["id"])
        assert stored is not None
        Path(settings.root_dir / stored.preview_path).unlink(missing_ok=True)
        db.commit()

    with TestClient(app) as client:
        response = client.post(f"/api/imports/{batch_id}/title-crops")

    assert response.status_code == 200
    data = response.json()
    assert data["total_count"] == 2
    assert data["success_count"] == 1
    assert data["failed_count"] == 1
    assert any(item["error_code"] == "PREVIEW_FILE_MISSING" for item in data["items"])
