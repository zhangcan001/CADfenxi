import json
from pathlib import Path

import pymupdf as fitz
from fastapi.testclient import TestClient

from backend.core.config import settings
from backend.main import app


def make_pdf_bytes() -> bytes:
    document = fitz.open()
    page = document.new_page(width=300, height=220)
    page.insert_text((72, 72), "图号：建施-08\n图名：屋面平面图\n日期：2026.05.20", fontsize=12)
    data = document.tobytes()
    document.close()
    return data


def prepare_sheet(client: TestClient, filename: str = "建施-03_二层平面图_A版_20260520.pdf"):
    project = client.post("/api/projects", json={"name": "候选值测试项目"})
    assert project.status_code == 201
    project_id = project.json()["id"]
    upload = client.post(
        f"/api/projects/{project_id}/imports",
        data={"batch_name": "候选值批次"},
        files=[("files", (filename, make_pdf_bytes(), "application/pdf"))],
    )
    assert upload.status_code == 201
    batch_id = upload.json()["id"]
    split = client.post(f"/api/imports/{batch_id}/split")
    assert split.status_code == 200
    sheet = client.get(f"/api/projects/{project_id}/sheets").json()["items"][0]
    return project_id, batch_id, sheet


def write_text_json(project_id: int, sheet_id: int, text: str):
    directory = settings.projects_dir / f"project_{project_id}" / "text"
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"sheet_{sheet_id}_pdf_text.json"
    path.write_text(
        json.dumps({"sheet_id": sheet_id, "page_no": 1, "source": "pdf_text", "text": text, "blocks": []}, ensure_ascii=False),
        encoding="utf-8",
    )


def write_ocr_json(project_id: int, sheet_id: int, text: str):
    directory = settings.projects_dir / f"project_{project_id}" / "ocr"
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"sheet_{sheet_id}_title_ocr.json"
    path.write_text(
        json.dumps({"sheet_id": sheet_id, "page_no": 1, "source": "title_ocr", "text": text, "items": []}, ensure_ascii=False),
        encoding="utf-8",
    )


def candidates_by_field(candidates: list[dict], field_name: str) -> list[dict]:
    return [candidate for candidate in candidates if candidate["field_name"] == field_name]


def test_generate_candidates_for_single_sheet_success():
    with TestClient(app) as client:
        project_id, _, sheet = prepare_sheet(client)
        write_text_json(project_id, sheet["id"], "图号：建施-08\n图名：屋面平面图")
        response = client.post(f"/api/sheets/{sheet['id']}/generate-candidates")

    assert response.status_code == 200
    assert response.json()["candidate_count"] > 0


def test_parse_drawing_no_from_filename():
    with TestClient(app) as client:
        _, _, sheet = prepare_sheet(client)
        response = client.post(f"/api/sheets/{sheet['id']}/generate-candidates")

    values = candidates_by_field(response.json()["candidates"], "drawing_no")
    assert any(candidate["normalized_value"] == "建施-03" for candidate in values)


def test_parse_drawing_name_from_filename():
    with TestClient(app) as client:
        _, _, sheet = prepare_sheet(client)
        response = client.post(f"/api/sheets/{sheet['id']}/generate-candidates")

    values = candidates_by_field(response.json()["candidates"], "drawing_name")
    assert any(candidate["candidate_value"] == "二层平面图" for candidate in values)


def test_parse_version_from_filename():
    with TestClient(app) as client:
        _, _, sheet = prepare_sheet(client)
        response = client.post(f"/api/sheets/{sheet['id']}/generate-candidates")

    values = candidates_by_field(response.json()["candidates"], "version")
    assert any(candidate["normalized_value"] == "A" for candidate in values)


def test_parse_issue_date_from_filename():
    with TestClient(app) as client:
        _, _, sheet = prepare_sheet(client)
        response = client.post(f"/api/sheets/{sheet['id']}/generate-candidates")

    values = candidates_by_field(response.json()["candidates"], "issue_date")
    assert any(candidate["normalized_value"] == "2026-05-20" for candidate in values)


def test_rule_generates_discipline_candidate():
    with TestClient(app) as client:
        _, _, sheet = prepare_sheet(client)
        response = client.post(f"/api/sheets/{sheet['id']}/generate-candidates")

    values = candidates_by_field(response.json()["candidates"], "discipline")
    assert any(candidate["source_type"] == "rule" and candidate["normalized_value"] == "建筑" for candidate in values)


def test_pdf_text_generates_drawing_no_candidate():
    with TestClient(app) as client:
        project_id, _, sheet = prepare_sheet(client)
        write_text_json(project_id, sheet["id"], "图号：结施-09\n图名：梁配筋图")
        response = client.post(f"/api/sheets/{sheet['id']}/generate-candidates")

    values = candidates_by_field(response.json()["candidates"], "drawing_no")
    assert any(candidate["source_type"] == "pdf_text" and candidate["normalized_value"] == "结施-09" for candidate in values)


def test_ocr_text_generates_drawing_no_candidate():
    with TestClient(app) as client:
        project_id, _, sheet = prepare_sheet(client)
        write_ocr_json(project_id, sheet["id"], "图号：电施-04\n图名：照明平面图")
        response = client.post(f"/api/sheets/{sheet['id']}/generate-candidates")

    values = candidates_by_field(response.json()["candidates"], "drawing_no")
    assert any(candidate["source_type"] == "title_ocr" and candidate["normalized_value"] == "电施-04" for candidate in values)


def test_normalized_value_is_generated():
    with TestClient(app) as client:
        _, _, sheet = prepare_sheet(client, filename="建施03_一层平面图_B版_2026.5.2.pdf")
        response = client.post(f"/api/sheets/{sheet['id']}/generate-candidates")

    candidates = response.json()["candidates"]
    assert any(candidate["normalized_value"] == "建施-03" for candidate in candidates)
    assert any(candidate["normalized_value"] == "2026-05-02" for candidate in candidates)


def test_get_candidates_returns_list():
    with TestClient(app) as client:
        _, _, sheet = prepare_sheet(client)
        client.post(f"/api/sheets/{sheet['id']}/generate-candidates")
        response = client.get(f"/api/sheets/{sheet['id']}/candidates")

    assert response.status_code == 200
    assert len(response.json()) > 0


def test_field_name_filter_works():
    with TestClient(app) as client:
        _, _, sheet = prepare_sheet(client)
        client.post(f"/api/sheets/{sheet['id']}/generate-candidates")
        response = client.get(f"/api/sheets/{sheet['id']}/candidates?field_name=drawing_no")

    assert response.status_code == 200
    assert all(candidate["field_name"] == "drawing_no" for candidate in response.json())


def test_delete_candidates_clears_machine_candidates():
    with TestClient(app) as client:
        _, _, sheet = prepare_sheet(client)
        client.post(f"/api/sheets/{sheet['id']}/generate-candidates")
        delete_response = client.delete(f"/api/sheets/{sheet['id']}/candidates")
        list_response = client.get(f"/api/sheets/{sheet['id']}/candidates")

    assert delete_response.status_code == 200
    assert delete_response.json()["deleted_count"] > 0
    assert list_response.json() == []


def test_batch_generate_candidates_success():
    with TestClient(app) as client:
        _, batch_id, _ = prepare_sheet(client)
        response = client.post(f"/api/imports/{batch_id}/generate-candidates")

    assert response.status_code == 200
    assert response.json()["total_count"] == 1
    assert response.json()["candidate_count"] > 0


def test_missing_ocr_result_does_not_fail():
    with TestClient(app) as client:
        _, _, sheet = prepare_sheet(client)
        response = client.post(f"/api/sheets/{sheet['id']}/generate-candidates")

    assert response.status_code == 200
    assert response.json()["candidate_count"] > 0


def test_missing_pdf_text_result_does_not_fail():
    with TestClient(app) as client:
        project_id, _, sheet = prepare_sheet(client)
        write_ocr_json(project_id, sheet["id"], "图号：水施-03")
        response = client.post(f"/api/sheets/{sheet['id']}/generate-candidates")

    assert response.status_code == 200
    assert response.json()["candidate_count"] > 0


def test_missing_sheet_returns_404():
    with TestClient(app) as client:
        response = client.post("/api/sheets/999999/generate-candidates")

    assert response.status_code == 404


def test_repeated_generate_does_not_duplicate_machine_candidates():
    with TestClient(app) as client:
        _, _, sheet = prepare_sheet(client)
        first = client.post(f"/api/sheets/{sheet['id']}/generate-candidates")
        second = client.post(f"/api/sheets/{sheet['id']}/generate-candidates")
        listed = client.get(f"/api/sheets/{sheet['id']}/candidates")

    assert first.status_code == 200
    assert second.status_code == 200
    assert len(listed.json()) == second.json()["candidate_count"]
