import io

import ezdxf
import pymupdf as fitz
from fastapi.testclient import TestClient

from backend.core.database import SessionLocal
from backend.main import app
from backend.models.recognition_candidate import RecognitionCandidate
from recognizer.cad_engine.cad_candidate_adapter import generate_candidates_from_cad_json
from recognizer.cad_engine.cad_text_rules import infer_candidates_from_text
from recognizer.cad_engine.tag_mapper import field_for_tag
from recognizer.filename_parser.parser import find_drawing_no
from recognizer.normalizer.discipline import infer_discipline
from recognizer.normalizer.drawing_no import normalize_drawing_no


def create_project(client: TestClient, name: str = "DXF质量规则测试") -> int:
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


def make_pdf_bytes(text: str = "建施-88 PDF旧流程回归图") -> bytes:
    document = fitz.open()
    page = document.new_page(width=360, height=240)
    page.insert_text((36, 72), text, fontsize=12)
    payload = document.tobytes()
    document.close()
    return payload


def upload_file(client: TestClient, project_id: int, name: str, content: bytes, mime: str) -> dict:
    response = client.post(
        f"/api/projects/{project_id}/imports",
        files=[("files", (name, content, mime))],
    )
    assert response.status_code == 201
    return response.json()


def run_dxf_candidates(client: TestClient, project_id: int, content: bytes, name: str = "quality.dxf") -> tuple[int, list[dict]]:
    upload = upload_file(client, project_id, name, content, "application/dxf")
    file_id = upload["files"][0]["id"]
    parse = client.post(f"/api/files/{file_id}/parse-dxf")
    assert parse.status_code == 200
    sheet_id = parse.json()["sheet_id"]
    generate = client.post(f"/api/sheets/{sheet_id}/generate-candidates")
    assert generate.status_code == 200
    return sheet_id, client.get(f"/api/sheets/{sheet_id}/candidates").json()


def issue_codes(client: TestClient, project_id: int, sheet_id: int) -> list[str]:
    response = client.get(f"/api/projects/{project_id}/issues", params={"sheet_id": sheet_id, "status": "open"})
    assert response.status_code == 200
    return [item["issue_code"] for item in response.json()["items"]]


def by_source(candidates: list[dict], source_type: str, field_name: str | None = None) -> list[dict]:
    return [
        item
        for item in candidates
        if item["source_type"] == source_type and (field_name is None or item["field_name"] == field_name)
    ]


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
                raw_text=value,
                bbox=None,
                run_id=None,
                parser_name="test",
                parser_version="test",
            )
        )
        db.commit()


def test_quality_tag_mapping_variants():
    assert field_for_tag("DrawingNo") == "drawing_no"
    assert field_for_tag("图纸编码") == "drawing_no"
    assert field_for_tag("图 号") == "drawing_no"
    assert field_for_tag("NO.") == "drawing_no"
    assert field_for_tag("图纸标题") == "drawing_name"
    assert field_for_tag("制图日期") == "issue_date"
    assert field_for_tag("RevNo") == "version"
    assert field_for_tag("工程图号") == "drawing_no"
    assert field_for_tag("DRAWINGTITLE") == "drawing_name"
    assert field_for_tag("SUBJECT") == "discipline"


def test_quality_drawing_no_normalization_and_component_filtering():
    assert normalize_drawing_no("建施 03") == "建施-03"
    assert normalize_drawing_no("建施_03") == "建施-03"
    assert normalize_drawing_no("建施—03") == "建施-03"
    assert normalize_drawing_no("JS 03") == "JS-03"
    assert normalize_drawing_no("A 101") == "A-101"
    assert normalize_drawing_no("建施总 01") == "建施总-01"
    for value in ["KZ-1", "KL-1", "门-1"]:
        assert not infer_candidates_from_text(value, "cad_text")


def test_quality_drawing_name_keywords_and_note_filtering():
    assert not any(
        item["field_name"] == "drawing_name"
        for item in infer_candidates_from_text("本图尺寸以毫米为单位", "cad_text")
    )
    assert not any(
        item["field_name"] == "drawing_name"
        for item in infer_candidates_from_text("总说明", "cad_text")
    )
    assert any(
        item["field_name"] == "drawing_name" and item["candidate_value"] == "一层平面图"
        for item in infer_candidates_from_text("一层平面图", "cad_text")
    )
    assert any(
        item["field_name"] == "drawing_name" and item["candidate_value"] == "梁配筋图"
        for item in infer_candidates_from_text("梁配筋图", "cad_text")
    )


def test_quality_discipline_from_drawing_no_prefixes():
    assert infer_discipline("建施-03") == "建筑"
    assert infer_discipline("结施-03") == "结构"
    assert infer_discipline("电施-03") == "电气"


def test_quality_cad_layer_only_generates_discipline():
    cad_json = {"layers": ["ARCH", "KZ-1"], "spaces": []}
    candidates = generate_candidates_from_cad_json(cad_json, {"original_name": "no-match.dxf"})
    layer_candidates = [item for item in candidates if item["source_type"] == "cad_layer"]
    assert layer_candidates
    assert all(item["field_name"] == "discipline" for item in layer_candidates)
    assert not any(item["field_name"] == "drawing_no" for item in layer_candidates)


def test_quality_invalid_date_and_block_attr_confidence():
    attr_date = infer_candidates_from_text("2026-99-99", "cad_block_attr", tagged_field="issue_date")[0]
    assert attr_date["normalized_value"] is None
    assert attr_date["confidence"] <= 50

    attr_no = infer_candidates_from_text("建施-03", "cad_block_attr", tagged_field="drawing_no")[0]
    text_no = infer_candidates_from_text("建施-03", "cad_text")[0]
    assert attr_no["confidence"] > text_no["confidence"]


def test_quality_filename_parser_handles_common_real_project_patterns():
    from recognizer.filename_parser.parser import parse_filename

    candidates = parse_filename("建施总01_总说明_A版_20260521.pdf")
    assert any(item["field_name"] == "drawing_no" and item["normalized_value"] == "建施总-01" for item in candidates)
    assert any(item["field_name"] == "version" and item["normalized_value"] == "A" for item in candidates)
    assert any(item["field_name"] == "issue_date" and item["normalized_value"] == "2026-05-21" for item in candidates)


def test_quality_filename_only_and_missing_block_attr_issues():
    with TestClient(app) as client:
        project_id = create_project(client, "DXF仅文件名与无块属性")

        filename_sheet_id, _ = run_dxf_candidates(
            client,
            project_id,
            dxf_bytes(lambda doc: doc.modelspace().add_line((0, 0), (1, 1))),
            "建施-21_一层平面图.dxf",
        )
        assert client.post(f"/api/sheets/{filename_sheet_id}/fuse-fields").status_code == 200
        assert "CAD_ONLY_FROM_FILENAME" in issue_codes(client, project_id, filename_sheet_id)

        text_sheet_id, _ = run_dxf_candidates(
            client,
            project_id,
            dxf_bytes(lambda doc: doc.modelspace().add_text("建施-22", dxfattribs={"insert": (0, 0, 0)})),
            "text-title.dxf",
        )
        assert client.post(f"/api/sheets/{text_sheet_id}/fuse-fields").status_code == 200
        assert "CAD_BLOCK_ATTR_MISSING" in issue_codes(client, project_id, text_sheet_id)


def test_quality_filename_only_triggers_low_confidence_issue_on_fusion():
    with TestClient(app) as client:
        project_id = create_project(client, "DXF文件名低可信")
        sheet_id, _ = run_dxf_candidates(
            client,
            project_id,
            dxf_bytes(lambda doc: doc.modelspace().add_line((0, 0), (1, 1))),
            "建施-21_一层平面图.dxf",
        )
        client.post(f"/api/sheets/{sheet_id}/fuse-fields")
        codes = issue_codes(client, project_id, sheet_id)

    assert "LOW_CONFIDENCE" in codes


def test_quality_generate_and_fuse_are_idempotent():
    with TestClient(app) as client:
        project_id = create_project(client, "DXF质量幂等")
        sheet_id, first_candidates = run_dxf_candidates(
            client,
            project_id,
            dxf_bytes(lambda doc: doc.modelspace().add_text("建施-23", dxfattribs={"insert": (0, 0, 0)})),
            "repeat-quality.dxf",
        )
        second = client.post(f"/api/sheets/{sheet_id}/generate-candidates")
        assert second.status_code == 200
        assert len(client.get(f"/api/sheets/{sheet_id}/candidates").json()) == len(first_candidates)

        assert client.post(f"/api/sheets/{sheet_id}/fuse-fields").status_code == 200
        first_issue_count = len(issue_codes(client, project_id, sheet_id))
        assert client.post(f"/api/sheets/{sheet_id}/fuse-fields").status_code == 200
        second_issue_count = len(issue_codes(client, project_id, sheet_id))
        assert second_issue_count == first_issue_count


def test_quality_pdf_candidates_old_logic_regression():
    with TestClient(app) as client:
        project_id = create_project(client, "PDF旧候选逻辑回归")
        upload = upload_file(client, project_id, "建施-88_PDF回归图.pdf", make_pdf_bytes(), "application/pdf")
        file_id = upload["files"][0]["id"]
        split = client.post(f"/api/files/{file_id}/split")
        assert split.status_code == 200
        sheet_id = split.json()["sheets"][0]["id"]
        generate = client.post(f"/api/sheets/{sheet_id}/generate-candidates")
        assert generate.status_code == 200
        candidates = client.get(f"/api/sheets/{sheet_id}/candidates").json()
        assert any(item["field_name"] == "drawing_no" for item in candidates)
        assert client.post(f"/api/sheets/{sheet_id}/fuse-fields").status_code == 200


def test_quality_dxf_complete_flow_regression():
    def build(doc):
        doc.layers.add("ARCH")
        block = doc.blocks.new(name="TITLE_BLOCK")
        for tag in ["DrawingNo", "图纸标题", "制图日期", "RevNo"]:
            block.add_attdef(tag, insert=(0, 0, 0))
        insert = doc.modelspace().add_blockref("TITLE_BLOCK", (0, 0, 0))
        insert.add_auto_attribs(
            {
                "DrawingNo": "建施 24",
                "图纸标题": "一层平面图",
                "制图日期": "2026-05-21",
                "RevNo": "A版",
            }
        )

    with TestClient(app) as client:
        project_id = create_project(client, "DXF完整流程质量回归")
        sheet_id, candidates = run_dxf_candidates(client, project_id, dxf_bytes(build), "quality-flow.dxf")
        assert any(item["normalized_value"] == "建施-24" for item in by_source(candidates, "cad_block_attr", "drawing_no"))
        fuse = client.post(f"/api/sheets/{sheet_id}/fuse-fields")
        assert fuse.status_code == 200
        detail = client.get(f"/api/sheets/{sheet_id}").json()
        assert detail["drawing_no"] == "建施-24"
        assert detail["drawing_name"] == "一层平面图"
