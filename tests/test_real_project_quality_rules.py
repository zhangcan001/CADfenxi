import io

import ezdxf
import pymupdf as fitz
from fastapi.testclient import TestClient

from backend.core.database import SessionLocal
from backend.main import app
from backend.models.field_value import FieldValue
from recognizer.cad_engine.cad_candidate_adapter import generate_candidates_from_cad_json
from recognizer.cad_engine.cad_text_rules import infer_candidates_from_text
from recognizer.cad_engine.tag_mapper import field_for_tag, normalize_tag
from recognizer.filename_parser.parser import parse_filename
from recognizer.normalizer.date import normalize_issue_date
from recognizer.normalizer.discipline import infer_discipline
from recognizer.normalizer.drawing_no import is_supported_drawing_no, normalize_drawing_no


def make_pdf(text: str) -> bytes:
    document = fitz.open()
    page = document.new_page(width=360, height=240)
    page.insert_text((36, 72), text, fontsize=12)
    payload = document.tobytes()
    document.close()
    return payload


def make_dxf(text: str) -> bytes:
    doc = ezdxf.new("R2010")
    doc.modelspace().add_text(text, dxfattribs={"insert": (0, 0, 0)})
    stream = io.StringIO()
    doc.write(stream)
    return stream.getvalue().encode("utf-8")


def create_project(client: TestClient, name: str = "质量规则测试") -> int:
    response = client.post("/api/projects", json={"name": name})
    assert response.status_code == 201
    return response.json()["id"]


def upload_file(client: TestClient, project_id: int, name: str, content: bytes, mime: str) -> dict:
    response = client.post(f"/api/projects/{project_id}/imports", files=[("files", (name, content, mime))])
    assert response.status_code == 201
    return response.json()


def test_drawing_no_rules_and_filters():
    assert normalize_drawing_no("建施 03") == "建施-03"
    assert normalize_drawing_no("建施_03") == "建施-03"
    assert normalize_drawing_no("建施—03") == "建施-03"
    assert normalize_drawing_no("JZ 03") == "JZ-03"
    assert normalize_drawing_no("A 101") == "A-101"
    assert is_supported_drawing_no("建施-01")
    assert not infer_candidates_from_text("KZ-1", "cad_text")
    assert not infer_candidates_from_text("1轴", "cad_text")


def test_drawing_name_keywords_and_note_filtering():
    assert any(item["field_name"] == "drawing_name" for item in infer_candidates_from_text("一层平面图", "cad_text"))
    assert not any(item["field_name"] == "drawing_name" for item in infer_candidates_from_text("本图尺寸以毫米为单位", "cad_text"))


def test_discipline_rules_and_tag_mapping():
    assert infer_discipline("建施-01") == "建筑"
    assert infer_discipline("结施-01") == "结构"
    assert infer_discipline("电施-01") == "电气"
    assert field_for_tag("图 号") == "drawing_no"
    assert field_for_tag("图纸标题") == "drawing_name"
    assert field_for_tag("RevNo") == "version"
    assert field_for_tag("日 期") == "issue_date"
    assert field_for_tag("SUBJECT") == "discipline"
    assert normalize_tag("图　号") == normalize_tag("图号")


def test_invalid_date_does_not_normalize():
    assert normalize_issue_date("2026-13-40") is None


def test_cad_block_attr_has_higher_confidence_than_cad_text():
    attr = infer_candidates_from_text("建施-03", "cad_block_attr", tagged_field="drawing_no")[0]
    text = infer_candidates_from_text("建施-03", "cad_text")[0]
    assert attr["confidence"] > text["confidence"]


def test_parse_filename_and_filename_only_issue_flow():
    values = parse_filename("建施总01_一层平面图_A版_20260521.pdf")
    assert any(item["field_name"] == "drawing_no" and item["normalized_value"] == "建施总-01" for item in values)
    assert any(item["field_name"] == "version" and item["normalized_value"] == "A" for item in values)

    with TestClient(app) as client:
        project_id = create_project(client)
        upload = upload_file(client, project_id, "建施-21_一层平面图.dxf", make_dxf("0"), "application/dxf")
        file_id = upload["files"][0]["id"]
        parse = client.post(f"/api/files/{file_id}/parse-dxf")
        sheet_id = parse.json()["sheet_id"]
        client.post(f"/api/sheets/{sheet_id}/generate-candidates")
        client.post(f"/api/sheets/{sheet_id}/fuse-fields")
        issues = client.get(f"/api/projects/{project_id}/issues?sheet_id={sheet_id}&status=open").json()["items"]

    assert any(issue["issue_code"] == "ONLY_FROM_FILENAME" for issue in issues)


def test_pdf_and_ocr_empty_text_emit_issues():
    with TestClient(app) as client:
        project_id = create_project(client, "空文本问题")
        upload = upload_file(client, project_id, "建施-08_空文本.pdf", make_pdf(""), "application/pdf")
        file_id = upload["files"][0]["id"]
        split = client.post(f"/api/files/{file_id}/split")
        sheet_id = split.json()["sheets"][0]["id"]
        client.post(f"/api/sheets/{sheet_id}/extract-text")
        client.post(f"/api/sheets/{sheet_id}/title-crop")
        client.post(f"/api/sheets/{sheet_id}/ocr-title")
        issues = client.get(f"/api/projects/{project_id}/issues?sheet_id={sheet_id}&status=open").json()["items"]

    codes = {issue["issue_code"] for issue in issues}
    assert "PDF_TEXT_EMPTY" in codes
    assert "OCR_TEXT_EMPTY" in codes


def test_low_confidence_and_cad_note_filtering():
    cad_json = {
        "spaces": [
            {
                "texts": [{"clean_text": "本图尺寸以毫米为单位"}],
                "mtexts": [{"clean_text": "一层平面图"}],
                "inserts": [],
            }
        ]
    }
    candidates = generate_candidates_from_cad_json(cad_json, {"original_name": "建施-01_一层平面图.dxf"})
    assert any(item["field_name"] == "drawing_name" and item["candidate_value"] == "一层平面图" for item in candidates)
    assert not any(item["field_name"] == "drawing_name" and "本图尺寸" in item["candidate_value"] for item in candidates)


def test_manual_reviewed_field_not_overwritten():
    with TestClient(app) as client:
        project_id = create_project(client, "人工保护")
        upload = upload_file(client, project_id, "建施-09_屋面平面图.dxf", make_dxf("建施-09"), "application/dxf")
        file_id = upload["files"][0]["id"]
        parse = client.post(f"/api/files/{file_id}/parse-dxf")
        sheet_id = parse.json()["sheet_id"]
        client.patch(f"/api/sheets/{sheet_id}/fields", json={"fields": {"drawing_no": "人工-001"}})
        client.post(f"/api/sheets/{sheet_id}/generate-candidates")
        client.post(f"/api/sheets/{sheet_id}/fuse-fields")
        sheet = client.get(f"/api/sheets/{sheet_id}").json()

    assert sheet["drawing_no"] == "人工-001"
    with SessionLocal() as db:
        reviewed = db.query(FieldValue).filter(FieldValue.sheet_id == sheet_id, FieldValue.field_name == "drawing_no").first()
        assert reviewed is not None
        assert reviewed.is_reviewed is True
