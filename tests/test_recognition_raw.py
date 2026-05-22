from pathlib import Path

import pymupdf as fitz
from fastapi.testclient import TestClient

from backend.core.config import settings
from backend.core.database import SessionLocal
from backend.models.drawing_sheet import DrawingSheet
from backend.main import app


def make_pdf_bytes(text: str = "PDF raw text", page_count: int = 1) -> bytes:
    document = fitz.open()
    for index in range(page_count):
        page = document.new_page(width=300, height=220)
        if text:
            page.insert_text((72, 72), f"{text} {index + 1}", fontsize=14)
    data = document.tobytes()
    document.close()
    return data


def create_project(client: TestClient) -> int:
    response = client.post("/api/projects", json={"name": "原始识别测试项目"})
    assert response.status_code == 201
    return response.json()["id"]


def prepare_sheet(client: TestClient, text: str = "PDF raw text", page_count: int = 1):
    project_id = create_project(client)
    upload = client.post(
        f"/api/projects/{project_id}/imports",
        data={"batch_name": "原始识别批次"},
        files=[
            (
                "files",
                ("recognition.pdf", make_pdf_bytes(text, page_count), "application/pdf"),
            )
        ],
    )
    assert upload.status_code == 201
    batch_id = upload.json()["id"]
    split = client.post(f"/api/imports/{batch_id}/split")
    assert split.status_code == 200
    sheets = client.get(f"/api/projects/{project_id}/sheets").json()["items"]
    return project_id, batch_id, sheets[0]


def prepare_sheet_with_title_crop(client: TestClient, text: str = "PDF raw text"):
    project_id, batch_id, sheet = prepare_sheet(client, text=text)
    crop = client.post(f"/api/sheets/{sheet['id']}/title-crop")
    assert crop.status_code == 200
    return project_id, batch_id, sheet


def test_extract_pdf_text_for_single_sheet_success():
    with TestClient(app) as client:
        _, _, sheet = prepare_sheet(client)
        response = client.post(f"/api/sheets/{sheet['id']}/extract-text")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["run_type"] == "pdf_text"
    assert data["text_length"] > 0


def test_pdf_text_result_file_exists():
    with TestClient(app) as client:
        _, _, sheet = prepare_sheet(client)
        response = client.post(f"/api/sheets/{sheet['id']}/extract-text")

    output_path = settings.root_dir / response.json()["output_path"]
    assert output_path.exists()
    assert output_path.parent.name == "text"


def test_pdf_text_recognition_run_is_written():
    with TestClient(app) as client:
        _, _, sheet = prepare_sheet(client)
        client.post(f"/api/sheets/{sheet['id']}/extract-text")
        response = client.get(f"/api/sheets/{sheet['id']}/recognition-runs")

    assert response.status_code == 200
    assert any(run["run_type"] == "pdf_text" for run in response.json())


def test_ocr_title_for_single_sheet_success():
    with TestClient(app) as client:
        _, _, sheet = prepare_sheet_with_title_crop(client)
        response = client.post(f"/api/sheets/{sheet['id']}/ocr-title")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["run_type"] == "title_ocr"
    assert data["error_code"] == "OCR_TEXT_EMPTY"


def test_ocr_result_file_exists():
    with TestClient(app) as client:
        _, _, sheet = prepare_sheet_with_title_crop(client)
        response = client.post(f"/api/sheets/{sheet['id']}/ocr-title")

    output_path = settings.root_dir / response.json()["output_path"]
    assert output_path.exists()
    assert output_path.parent.name == "ocr"


def test_title_ocr_recognition_run_is_written():
    with TestClient(app) as client:
        _, _, sheet = prepare_sheet_with_title_crop(client)
        client.post(f"/api/sheets/{sheet['id']}/ocr-title")
        response = client.get(f"/api/sheets/{sheet['id']}/recognition-runs")

    assert response.status_code == 200
    assert any(run["run_type"] == "title_ocr" for run in response.json())


def test_get_recognition_runs_returns_records():
    with TestClient(app) as client:
        _, _, sheet = prepare_sheet_with_title_crop(client)
        client.post(f"/api/sheets/{sheet['id']}/extract-text")
        client.post(f"/api/sheets/{sheet['id']}/ocr-title")
        response = client.get(f"/api/sheets/{sheet['id']}/recognition-runs")

    assert response.status_code == 200
    assert len(response.json()) >= 2


def test_batch_extract_text_success():
    with TestClient(app) as client:
        _, batch_id, _ = prepare_sheet(client, page_count=2)
        response = client.post(f"/api/imports/{batch_id}/extract-text")

    assert response.status_code == 200
    assert response.json()["total_count"] == 2
    assert response.json()["success_count"] == 2


def test_batch_ocr_titles_success():
    with TestClient(app) as client:
        _, batch_id, _ = prepare_sheet(client, page_count=2)
        crop = client.post(f"/api/imports/{batch_id}/title-crops")
        assert crop.status_code == 200
        response = client.post(f"/api/imports/{batch_id}/ocr-titles")

    assert response.status_code == 200
    assert response.json()["total_count"] == 2
    assert response.json()["success_count"] == 2


def test_missing_sheet_returns_404():
    with TestClient(app) as client:
        response = client.post("/api/sheets/999999/extract-text")

    assert response.status_code == 404


def test_ocr_without_title_crop_returns_title_crop_not_found():
    with TestClient(app) as client:
        _, _, sheet = prepare_sheet(client)
        response = client.post(f"/api/sheets/{sheet['id']}/ocr-title")

    assert response.status_code == 400
    assert response.json()["detail"]["error_code"] == "TITLE_CROP_NOT_FOUND"


def test_ocr_missing_title_crop_file_returns_file_missing():
    with TestClient(app) as client:
        _, _, sheet = prepare_sheet_with_title_crop(client)

    with SessionLocal() as db:
        stored = db.get(DrawingSheet, sheet["id"])
        assert stored is not None
        (settings.root_dir / stored.title_crop_path).unlink(missing_ok=True)
        db.commit()

    with TestClient(app) as client:
        response = client.post(f"/api/sheets/{sheet['id']}/ocr-title")

    assert response.status_code == 400
    assert response.json()["detail"]["error_code"] == "TITLE_CROP_FILE_MISSING"


def test_pdf_without_text_is_success_with_warning():
    with TestClient(app) as client:
        _, _, sheet = prepare_sheet(client, text="")
        response = client.post(f"/api/sheets/{sheet['id']}/extract-text")

    assert response.status_code == 200
    assert response.json()["status"] == "success"
    assert response.json()["error_code"] == "PDF_TEXT_EMPTY"


def test_ocr_empty_text_is_success_with_warning():
    with TestClient(app) as client:
        _, _, sheet = prepare_sheet_with_title_crop(client)
        response = client.post(f"/api/sheets/{sheet['id']}/ocr-title")

    assert response.status_code == 200
    assert response.json()["status"] == "success"
    assert response.json()["error_code"] == "OCR_TEXT_EMPTY"
