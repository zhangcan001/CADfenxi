import io

import ezdxf
import pymupdf as fitz
import pytest
from fastapi.testclient import TestClient

from backend.main import app

def make_pdf_bytes(text: str = "PDF drawing") -> bytes:
    document = fitz.open()
    page = document.new_page()
    page.insert_text((72, 72), text)
    payload = document.tobytes()
    document.close()
    return payload


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as test_client:
        yield test_client


def create_project(client: TestClient, name: str = "DXF 候选测试") -> int:
    response = client.post("/api/projects", json={"name": name})
    assert response.status_code == 201
    return response.json()["id"]


def dxf_bytes(builder=None) -> bytes:
    doc = ezdxf.new("R2010")
    if builder is not None:
        builder(doc)
    stream = io.StringIO()
    doc.write(stream)
    return stream.getvalue().encode("utf-8")


def upload_dxf(client: TestClient, project_id: int, content: bytes, name: str) -> dict:
    response = client.post(
        f"/api/projects/{project_id}/imports",
        files=[("files", (name, content, "application/dxf"))],
    )
    assert response.status_code == 201
    return response.json()


def parse_and_generate(client: TestClient, project_id: int, content: bytes, name: str) -> tuple[dict, list[dict]]:
    upload = upload_dxf(client, project_id, content, name)
    file_id = upload["files"][0]["id"]
    parse = client.post(f"/api/files/{file_id}/parse-dxf")
    assert parse.status_code == 200
    generate = client.post(f"/api/sheets/{parse.json()['sheet_id']}/generate-candidates")
    assert generate.status_code == 200
    candidates = client.get(f"/api/sheets/{parse.json()['sheet_id']}/candidates").json()
    return parse.json(), candidates


def by_source(candidates: list[dict], source_type: str, field_name: str | None = None) -> list[dict]:
    return [
        item
        for item in candidates
        if item["source_type"] == source_type and (field_name is None or item["field_name"] == field_name)
    ]


def test_dxf_candidates_from_attrib_text_mtext_layer_and_filename(client: TestClient):
    def build(doc):
        doc.layers.add("ARCH")
        doc.layers.add("TITLE")
        msp = doc.modelspace()
        msp.add_text("建施-04", dxfattribs={"layer": "TITLE", "insert": (1, 1, 0)})
        msp.add_text("KZ-1", dxfattribs={"layer": "TITLE", "insert": (2, 2, 0)})
        msp.add_text("本图尺寸以毫米为单位", dxfattribs={"layer": "TITLE", "insert": (3, 3, 0)})
        msp.add_mtext("二层平面图", dxfattribs={"layer": "TITLE", "insert": (4, 4, 0)})
        block = doc.blocks.new(name="TITLE_BLOCK")
        for tag in ["DRAWING_NO", "DRAWING_TITLE", "REVISION", "DATE"]:
            block.add_attdef(tag, insert=(0, 0, 0), dxfattribs={"layer": "TITLE", "height": 3.5})
        insert = msp.add_blockref("TITLE_BLOCK", (0, 0, 0))
        insert.add_auto_attribs(
            {
                "DRAWING_NO": "建施-03",
                "DRAWING_TITLE": "一层平面图",
                "REVISION": "A版",
                "DATE": "2026.05.20",
            }
        )

    project_id = create_project(client)
    _, candidates = parse_and_generate(
        client,
        project_id,
        dxf_bytes(build),
        "建施-05_二层平面图_B版_20260521.dxf",
    )

    assert any(item["field_name"] == "drawing_no" and item["normalized_value"] == "建施-03" for item in by_source(candidates, "cad_block_attr"))
    assert any(item["field_name"] == "drawing_name" and item["candidate_value"] == "一层平面图" for item in by_source(candidates, "cad_block_attr"))
    assert any(item["field_name"] == "version" and item["normalized_value"] == "A" for item in by_source(candidates, "cad_block_attr"))
    assert any(item["field_name"] == "issue_date" and item["normalized_value"] == "2026-05-20" for item in by_source(candidates, "cad_block_attr"))
    assert any(item["field_name"] == "drawing_no" and item["normalized_value"] == "建施-04" for item in by_source(candidates, "cad_text"))
    assert any(item["field_name"] == "drawing_name" and item["candidate_value"] == "二层平面图" for item in by_source(candidates, "cad_mtext"))
    assert all(item["field_name"] == "discipline" for item in by_source(candidates, "cad_layer"))
    assert any(item["field_name"] == "discipline" and item["normalized_value"] == "建筑" for item in by_source(candidates, "cad_layer"))
    assert any(item["field_name"] == "drawing_no" and item["source_type"] == "cad_filename" for item in candidates)
    assert any(item["field_name"] == "drawing_name" and item["source_type"] == "cad_filename" for item in candidates)

    attr_drawing_no = by_source(candidates, "cad_block_attr", "drawing_no")[0]
    text_drawing_no = by_source(candidates, "cad_text", "drawing_no")[0]
    assert attr_drawing_no["confidence"] >= text_drawing_no["confidence"]
    assert not any(item["candidate_value"] == "KZ-1" and item["confidence"] >= 70 for item in candidates)
    assert not any(item["candidate_value"] == "本图尺寸以毫米为单位" and item["field_name"] == "drawing_name" for item in candidates)


def test_dxf_invalid_date_normalized_value_is_empty(client: TestClient):
    def build(doc):
        block = doc.blocks.new(name="TITLE_BLOCK")
        block.add_attdef("DATE", insert=(0, 0, 0))
        insert = doc.modelspace().add_blockref("TITLE_BLOCK", (0, 0, 0))
        insert.add_auto_attribs({"DATE": "2026-99-99"})

    project_id = create_project(client)
    _, candidates = parse_and_generate(client, project_id, dxf_bytes(build), "bad-date.dxf")
    date_candidates = by_source(candidates, "cad_block_attr", "issue_date")
    assert date_candidates
    assert date_candidates[0]["normalized_value"] is None
    assert date_candidates[0]["confidence"] <= 50


def test_dxf_generate_candidates_requires_parse(client: TestClient):
    project_id = create_project(client)
    upload = upload_dxf(client, project_id, dxf_bytes(), "not-parsed.dxf")
    prepare = client.post(f"/api/files/{upload['files'][0]['id']}/prepare-dxf-sheet")
    assert prepare.status_code == 200
    response = client.post(f"/api/sheets/{prepare.json()['sheet_id']}/generate-candidates")
    assert response.status_code == 404
    assert response.json()["detail"]["error_code"] == "CAD_PARSE_NOT_FOUND"


def test_dxf_generate_candidates_is_idempotent_and_delete_clears_cad_sources(client: TestClient):
    def build(doc):
        doc.modelspace().add_text("建施-08", dxfattribs={"insert": (0, 0, 0)})

    project_id = create_project(client)
    parse, _ = parse_and_generate(client, project_id, dxf_bytes(build), "repeat.dxf")
    sheet_id = parse["sheet_id"]
    first_count = len(client.get(f"/api/sheets/{sheet_id}/candidates").json())
    second = client.post(f"/api/sheets/{sheet_id}/generate-candidates")
    assert second.status_code == 200
    second_count = len(client.get(f"/api/sheets/{sheet_id}/candidates").json())
    assert second_count == first_count
    deleted = client.delete(f"/api/sheets/{sheet_id}/candidates")
    assert deleted.status_code == 200
    assert deleted.json()["deleted_count"] == second_count
    assert client.get(f"/api/sheets/{sheet_id}/candidates").json() == []


def test_batch_generate_candidates_handles_pdf_and_dxf_mix(client: TestClient):
    def build(doc):
        doc.modelspace().add_text("建施-09", dxfattribs={"insert": (0, 0, 0)})

    project_id = create_project(client)
    response = client.post(
        f"/api/projects/{project_id}/imports",
            files=[
                ("files", ("cad.dxf", dxf_bytes(build), "application/dxf")),
                ("files", ("建施-10_三层平面图.pdf", make_pdf_bytes(), "application/pdf")),
            ],
        )
    assert response.status_code == 201
    batch_id = response.json()["id"]
    dxf_file_id = next(item["id"] for item in response.json()["files"] if item["source_format"] == "dxf")
    pdf_file_id = next(item["id"] for item in response.json()["files"] if item["source_format"] == "pdf")
    parse = client.post(f"/api/files/{dxf_file_id}/parse-dxf")
    assert parse.status_code == 200
    split = client.post(f"/api/files/{pdf_file_id}/split")
    assert split.status_code == 200
    result = client.post(f"/api/imports/{batch_id}/generate-candidates")
    assert result.status_code == 200
    assert result.json()["success_count"] == 2
    assert result.json()["failed_count"] == 0
