import io
import json

import ezdxf
import pytest
from fastapi.testclient import TestClient

from backend.core.config import settings
from backend.main import app

PDF_BYTES = b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF\n"


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as test_client:
        yield test_client


def create_project(client: TestClient, name: str = "DXF 解析测试") -> int:
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


def upload_file(client: TestClient, project_id: int, name: str, content: bytes, mime: str) -> dict:
    response = client.post(
        f"/api/projects/{project_id}/imports",
        files=[("files", (name, content, mime))],
    )
    assert response.status_code == 201
    return response.json()


def upload_dxf(client: TestClient, project_id: int, content: bytes, name: str = "parse.dxf") -> dict:
    return upload_file(client, project_id, name, content, "application/dxf")


def upload_pdf(client: TestClient, project_id: int) -> dict:
    return upload_file(client, project_id, "not-cad.pdf", PDF_BYTES, "application/pdf")


def parse_uploaded_dxf(client: TestClient, project_id: int, content: bytes) -> tuple[dict, dict]:
    upload = upload_dxf(client, project_id, content)
    file_id = upload["files"][0]["id"]
    response = client.post(f"/api/files/{file_id}/parse-dxf")
    assert response.status_code == 200
    return upload, response.json()


def test_parse_dxf_text_saves_cad_json_and_recognition_run(client: TestClient):
    def build(doc):
        doc.layers.add("TITLE")
        doc.modelspace().add_text("建施-03", dxfattribs={"layer": "TITLE", "insert": (100, 200, 0), "height": 3.5})

    project_id = create_project(client)
    upload, result = parse_uploaded_dxf(client, project_id, dxf_bytes(build))
    runs = client.get(f"/api/sheets/{result['sheet_id']}/recognition-runs").json()

    assert result["status"] == "success"
    assert result["counts"]["text_count"] == 1
    assert result["counts"]["layer_count"] >= 2
    output_path = settings.root_dir / result["output_path"]
    assert output_path.exists()
    data = json.loads(output_path.read_text(encoding="utf-8"))
    assert data["project_id"] == project_id
    assert data["file_id"] == upload["files"][0]["id"]
    assert data["sheet_id"] == result["sheet_id"]
    assert data["engine"] == "ezdxf"
    assert data["engine_version"]
    assert data["spaces"][0]["space"] == "modelspace"
    assert data["layers"]
    assert data["counts"]["text_count"] == 1
    assert data["spaces"][0]["texts"][0]["clean_text"] == "建施-03"
    assert any(run["run_type"] == "cad_parse" and run["status"] == "success" for run in runs)


def test_parse_dxf_mtext_extracts_clean_text(client: TestClient):
    def build(doc):
        doc.layers.add("TITLE")
        doc.modelspace().add_mtext("二层\\P平面图", dxfattribs={"layer": "TITLE", "insert": (120, 210, 0), "char_height": 3.5})

    project_id = create_project(client)
    _, result = parse_uploaded_dxf(client, project_id, dxf_bytes(build))
    data = json.loads((settings.root_dir / result["output_path"]).read_text(encoding="utf-8"))

    assert result["counts"]["mtext_count"] == 1
    assert data["spaces"][0]["mtexts"][0]["clean_text"] in {"二层 平面图", "二层平面图"}


def test_parse_dxf_insert_attrib_layers_and_summary(client: TestClient):
    def build(doc):
        doc.layers.add("TITLE")
        block = doc.blocks.new(name="TITLE_BLOCK")
        block.add_attdef("DRAWING_NO", insert=(0, 0, 0), dxfattribs={"layer": "TITLE", "height": 3.5})
        insert = doc.modelspace().add_blockref("TITLE_BLOCK", (0, 0, 0), dxfattribs={"layer": "0"})
        insert.add_auto_attribs({"DRAWING_NO": "建施-03"})

    project_id = create_project(client)
    _, result = parse_uploaded_dxf(client, project_id, dxf_bytes(build))
    summary = client.get(f"/api/sheets/{result['sheet_id']}/cad-parse")

    assert result["counts"]["insert_count"] == 1
    assert result["counts"]["attrib_count"] == 1
    assert result["counts"]["layer_count"] >= 2
    assert summary.status_code == 200
    data = summary.json()
    assert data["counts"]["insert_count"] == 1
    assert data["sample_attribs"][0]["tag"] == "DRAWING_NO"
    assert data["sample_attribs"][0]["clean_text"] == "建施-03"
    assert "TITLE" in data["layers"]


def test_parse_empty_dxf_returns_warning_not_failure(client: TestClient):
    project_id = create_project(client)
    _, result = parse_uploaded_dxf(client, project_id, dxf_bytes())

    assert result["status"] == "success"
    assert result["counts"]["text_count"] == 0
    assert result["counts"]["mtext_count"] == 0
    assert result["counts"]["attrib_count"] == 0
    assert "DXF_EMPTY_CONTENT" in result["warnings"]


def test_parse_damaged_dxf_returns_structured_failure_and_run(client: TestClient):
    project_id = create_project(client)
    upload = upload_dxf(client, project_id, b"not a real dxf")
    file_id = upload["files"][0]["id"]
    response = client.post(f"/api/files/{file_id}/parse-dxf")
    result = response.json()
    runs = client.get(f"/api/sheets/{result['sheet_id']}/recognition-runs").json()

    assert response.status_code == 200
    assert result["status"] == "failed"
    assert result["error_code"] in {"DXF_PARSE_FAILED", "DXF_OPEN_FAILED"}
    assert any(run["run_type"] == "cad_parse" and run["status"] == "failed" for run in runs)


def test_parse_dxf_rejects_pdf_and_missing_file(client: TestClient):
    project_id = create_project(client)
    upload = upload_pdf(client, project_id)
    pdf_response = client.post(f"/api/files/{upload['files'][0]['id']}/parse-dxf")
    missing_response = client.post("/api/files/999999999/parse-dxf")

    assert pdf_response.status_code == 400
    assert pdf_response.json()["detail"]["error_code"] == "UNSUPPORTED_CAD_FORMAT"
    assert missing_response.status_code == 404


def test_batch_parse_dxf_continues_after_single_failure_and_skips_pdf(client: TestClient):
    def build(doc):
        doc.modelspace().add_text("A-001", dxfattribs={"insert": (0, 0, 0)})

    project_id = create_project(client)
    response = client.post(
        f"/api/projects/{project_id}/imports",
        files=[
            ("files", ("good.dxf", dxf_bytes(build), "application/dxf")),
            ("files", ("bad.dxf", b"broken", "application/dxf")),
            ("files", ("skip.pdf", PDF_BYTES, "application/pdf")),
        ],
    )
    assert response.status_code == 201
    batch_id = response.json()["id"]
    first = client.post(f"/api/imports/{batch_id}/parse-dxf")
    second = client.post(f"/api/imports/{batch_id}/parse-dxf")
    sheets = client.get(f"/api/projects/{project_id}/sheets").json()

    assert first.status_code == 200
    data = first.json()
    assert data["total_count"] == 2
    assert data["success_count"] == 1
    assert data["failed_count"] == 1
    assert data["skipped_count"] == 1
    assert second.status_code == 200
    assert sheets["total"] == 2
