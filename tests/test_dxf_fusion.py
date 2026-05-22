import io

import ezdxf
import pymupdf as fitz
import pytest
from fastapi.testclient import TestClient

from backend.core.database import SessionLocal
from backend.main import app
from backend.models.recognition_candidate import RecognitionCandidate


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as test_client:
        yield test_client


def create_project(client: TestClient, name: str = "DXF 融合测试") -> int:
    response = client.post("/api/projects", json={"name": name})
    assert response.status_code == 201
    return response.json()["id"]


def dxf_bytes(text: str | None = None) -> bytes:
    doc = ezdxf.new("R2010")
    if text:
        doc.modelspace().add_text(text, dxfattribs={"insert": (0, 0, 0)})
    stream = io.StringIO()
    doc.write(stream)
    return stream.getvalue().encode("utf-8")


def make_pdf_bytes(text: str = "建施-88 PDF测试图") -> bytes:
    document = fitz.open()
    page = document.new_page()
    page.insert_text((72, 72), text)
    payload = document.tobytes()
    document.close()
    return payload


def upload_dxf(client: TestClient, project_id: int, name: str = "fusion.dxf") -> dict:
    response = client.post(
        f"/api/projects/{project_id}/imports",
        files=[("files", (name, dxf_bytes(), "application/dxf"))],
    )
    assert response.status_code == 201
    return response.json()


def prepare_dxf_sheet(client: TestClient, project_id: int, name: str = "fusion.dxf") -> tuple[dict, dict]:
    upload = upload_dxf(client, project_id, name)
    prepare = client.post(f"/api/files/{upload['files'][0]['id']}/prepare-dxf-sheet")
    assert prepare.status_code == 200
    return upload, prepare.json()


def add_candidate(
    *,
    project_id: int,
    batch_id: int,
    file_id: int,
    sheet_id: int,
    field_name: str,
    value: str,
    source_type: str,
    confidence: float,
    normalized: str | None = "__default__",
    raw_text: str | None = None,
) -> None:
    with SessionLocal() as db:
        db.add(
            RecognitionCandidate(
                project_id=project_id,
                batch_id=batch_id,
                file_id=file_id,
                sheet_id=sheet_id,
                field_name=field_name,
                candidate_value=value,
                normalized_value=value if normalized == "__default__" else normalized,
                source_type=source_type,
                confidence=confidence,
                raw_text=raw_text or value,
                bbox=None,
                run_id=None,
                parser_name="test",
                parser_version="test",
            )
        )
        db.commit()


def add_core_dxf_candidates(project_id: int, batch_id: int, file_id: int, sheet_id: int) -> None:
    add_candidate(project_id=project_id, batch_id=batch_id, file_id=file_id, sheet_id=sheet_id, field_name="drawing_no", value="建施-03", source_type="cad_block_attr", confidence=90, raw_text="DRAWING_NO=建施-03")
    add_candidate(project_id=project_id, batch_id=batch_id, file_id=file_id, sheet_id=sheet_id, field_name="drawing_no", value="建施-04", source_type="cad_text", confidence=80)
    add_candidate(project_id=project_id, batch_id=batch_id, file_id=file_id, sheet_id=sheet_id, field_name="drawing_name", value="一层平面图", source_type="cad_block_attr", confidence=88, raw_text="DRAWING_TITLE=一层平面图")
    add_candidate(project_id=project_id, batch_id=batch_id, file_id=file_id, sheet_id=sheet_id, field_name="drawing_name", value="二层平面图", source_type="cad_mtext", confidence=75)
    add_candidate(project_id=project_id, batch_id=batch_id, file_id=file_id, sheet_id=sheet_id, field_name="discipline", value="建筑", source_type="cad_layer", confidence=60)
    add_candidate(project_id=project_id, batch_id=batch_id, file_id=file_id, sheet_id=sheet_id, field_name="version", value="A版", normalized="A", source_type="cad_block_attr", confidence=85)
    add_candidate(project_id=project_id, batch_id=batch_id, file_id=file_id, sheet_id=sheet_id, field_name="issue_date", value="2026-05-20", source_type="cad_block_attr", confidence=85)
    add_candidate(project_id=project_id, batch_id=batch_id, file_id=file_id, sheet_id=sheet_id, field_name="drawing_no", value="L-1", source_type="cad_layer", confidence=65)


def field_map(values: list[dict]) -> dict[str, dict]:
    return {item["field_name"]: item for item in values}


def issue_codes(client: TestClient, project_id: int, sheet_id: int) -> list[str]:
    response = client.get(f"/api/projects/{project_id}/issues", params={"sheet_id": sheet_id, "status": "open"})
    assert response.status_code == 200
    return [item["issue_code"] for item in response.json()["items"]]


def test_dxf_cad_sources_fuse_to_field_values_sheet_and_issues(client: TestClient):
    project_id = create_project(client)
    upload, prepare = prepare_dxf_sheet(client, project_id)
    file_id = upload["files"][0]["id"]
    sheet_id = prepare["sheet_id"]
    add_core_dxf_candidates(project_id, upload["id"], file_id, sheet_id)

    response = client.post(f"/api/sheets/{sheet_id}/fuse-fields")
    detail = client.get(f"/api/sheets/{sheet_id}").json()
    values = field_map(client.get(f"/api/sheets/{sheet_id}/field-values").json())
    evidence = client.get(f"/api/sheets/{sheet_id}/evidence").json()
    codes = issue_codes(client, project_id, sheet_id)

    assert response.status_code == 200
    assert values["drawing_no"]["display_value"] == "建施-03"
    assert values["drawing_no"]["final_source"] == "cad_block_attr"
    assert values["drawing_name"]["display_value"] == "一层平面图"
    assert values["discipline"]["display_value"] == "建筑"
    assert values["discipline"]["final_source"] == "cad_layer"
    assert detail["drawing_no"] == "建施-03"
    assert detail["drawing_name"] == "一层平面图"
    assert detail["discipline"] == "建筑"
    assert detail["confidence_score"] > 0
    assert detail["trust_level"] in {"A", "B", "C", "D"}
    assert "CAD_FIELD_CONFLICT" in codes
    assert "CAD_ONLY_FROM_LAYER" in codes
    assert any(item["source_type"] == "cad_block_attr" and "DRAWING_NO=建施-03" in item["raw_text"] for item in evidence)
    assert all(not (item["field_name"] == "drawing_no" and item["source_type"] == "cad_layer") for item in evidence)


def test_dxf_missing_and_invalid_issue_rules(client: TestClient):
    project_id = create_project(client)
    upload, prepare = prepare_dxf_sheet(client, project_id, "missing.dxf")
    file_id = upload["files"][0]["id"]
    sheet_id = prepare["sheet_id"]
    add_candidate(project_id=project_id, batch_id=upload["id"], file_id=file_id, sheet_id=sheet_id, field_name="discipline", value="建筑", source_type="cad_layer", confidence=60)
    add_candidate(project_id=project_id, batch_id=upload["id"], file_id=file_id, sheet_id=sheet_id, field_name="issue_date", value="2026-99-99", normalized=None, source_type="cad_block_attr", confidence=50)

    response = client.post(f"/api/sheets/{sheet_id}/fuse-fields")
    codes = issue_codes(client, project_id, sheet_id)

    assert response.status_code == 200
    assert "DRAWING_NO_EMPTY" in codes
    assert "DRAWING_NAME_EMPTY" in codes
    assert "ISSUE_DATE_INVALID" in codes
    assert "CAD_ONLY_FROM_LAYER" in codes


def test_dxf_empty_cad_parse_generates_empty_content_issue(client: TestClient):
    project_id = create_project(client)
    upload = upload_dxf(client, project_id, "empty-parse.dxf")
    file_id = upload["files"][0]["id"]
    parse = client.post(f"/api/files/{file_id}/parse-dxf")
    assert parse.status_code == 200
    generate = client.post(f"/api/sheets/{parse.json()['sheet_id']}/generate-candidates")
    assert generate.status_code == 200
    fuse = client.post(f"/api/sheets/{parse.json()['sheet_id']}/fuse-fields")
    codes = issue_codes(client, project_id, parse.json()["sheet_id"])

    assert fuse.status_code == 200
    assert "CAD_PARSE_EMPTY_CONTENT" in codes


def test_dxf_fuse_is_idempotent_and_preserves_reviewed_value(client: TestClient):
    project_id = create_project(client)
    upload, prepare = prepare_dxf_sheet(client, project_id, "manual.dxf")
    file_id = upload["files"][0]["id"]
    sheet_id = prepare["sheet_id"]
    add_core_dxf_candidates(project_id, upload["id"], file_id, sheet_id)
    client.post(f"/api/sheets/{sheet_id}/fuse-fields")
    first_issue_count = len(issue_codes(client, project_id, sheet_id))
    client.post(f"/api/sheets/{sheet_id}/fuse-fields")
    second_issue_count = len(issue_codes(client, project_id, sheet_id))
    assert second_issue_count == first_issue_count

    manual = client.patch(
        f"/api/sheets/{sheet_id}/fields",
        json={"fields": {"drawing_no": "建施-03A"}, "note": "人工确认"},
    )
    assert manual.status_code == 200
    add_candidate(project_id=project_id, batch_id=upload["id"], file_id=file_id, sheet_id=sheet_id, field_name="drawing_no", value="建施-99", source_type="cad_block_attr", confidence=95)
    client.post(f"/api/sheets/{sheet_id}/fuse-fields")
    values = field_map(client.get(f"/api/sheets/{sheet_id}/field-values").json())
    detail = client.get(f"/api/sheets/{sheet_id}").json()

    assert values["drawing_no"]["display_value"] == "建施-03A"
    assert values["drawing_no"]["is_reviewed"] is True
    assert detail["drawing_no"] == "建施-03A"


def test_batch_fuse_handles_dxf_and_pdf_mix(client: TestClient):
    project_id = create_project(client)
    response = client.post(
        f"/api/projects/{project_id}/imports",
        files=[
            ("files", ("cad.dxf", dxf_bytes(), "application/dxf")),
            ("files", ("建施-77_四层平面图.pdf", make_pdf_bytes(), "application/pdf")),
        ],
    )
    assert response.status_code == 201
    batch_id = response.json()["id"]
    dxf_file_id = next(item["id"] for item in response.json()["files"] if item["source_format"] == "dxf")
    pdf_file_id = next(item["id"] for item in response.json()["files"] if item["source_format"] == "pdf")
    dxf_prepare = client.post(f"/api/files/{dxf_file_id}/prepare-dxf-sheet").json()
    add_core_dxf_candidates(project_id, batch_id, dxf_file_id, dxf_prepare["sheet_id"])
    pdf_split = client.post(f"/api/files/{pdf_file_id}/split")
    assert pdf_split.status_code == 200
    pdf_sheet_id = pdf_split.json()["sheets"][0]["id"]
    assert client.post(f"/api/sheets/{pdf_sheet_id}/generate-candidates").status_code == 200

    result = client.post(f"/api/imports/{batch_id}/fuse-fields")

    assert result.status_code == 200
    assert result.json()["success_count"] == 2
    assert result.json()["failed_count"] == 0
