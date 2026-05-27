from pathlib import Path

import ezdxf
from fastapi.testclient import TestClient
from openpyxl import load_workbook
from sqlalchemy import func, select

from backend.core.config import settings
from backend.core.database import SessionLocal
from backend.main import app
from backend.models.drawing_issue import DrawingIssue
from backend.models.field_value import FieldValue
from backend.models.recognition_candidate import RecognitionCandidate
from recognizer.cad_engine.cad_candidate_adapter import generate_candidates_from_cad_json
from recognizer.cad_engine.tag_mapper import field_for_tag
from recognizer.cad_engine.cad_text_rules import infer_candidates_from_text
from recognizer.filename_parser.parser import parse_filename
from recognizer.normalizer.date import normalize_issue_date
from recognizer.normalizer.discipline import infer_discipline
from recognizer.normalizer.drawing_no import is_supported_drawing_no, normalize_drawing_no
from recognizer.rules.issue_rules import issue_template
from test_recognition_raw import _wait_for_ocr_job
from test_full_flow_stability_v055 import (
    create_project,
    export_excel,
    make_pdf_bytes,
    run_pipeline,
    title_block_dxf,
    upload,
)
from dwg_test_helpers import DWG_BYTES, clear_converter_tables, create_converter_setting, write_mock_converter


VERSION = "v1.2.1-fast-integrity"


def field_candidates(candidates: list[dict], field_name: str) -> list[dict]:
    return [item for item in candidates if item["field_name"] == field_name]


def issue_codes(sheet_id: int) -> list[str]:
    with SessionLocal() as db:
        return [
            item.issue_code
            for item in db.scalars(
                select(DrawingIssue).where(DrawingIssue.sheet_id == sheet_id, DrawingIssue.status == "open")
            ).all()
        ]


def counts(sheet_id: int) -> tuple[int, int]:
    with SessionLocal() as db:
        return (
            db.scalar(select(func.count()).select_from(RecognitionCandidate).where(RecognitionCandidate.sheet_id == sheet_id)) or 0,
            db.scalar(
                select(func.count()).select_from(DrawingIssue).where(
                    DrawingIssue.sheet_id == sheet_id,
                    DrawingIssue.status == "open",
                )
            )
            or 0,
        )


def test_v07_health_version_and_portable_default():
    from scripts.build_portable_package import DEFAULT_VERSION, package_name

    with TestClient(app) as client:
        health = client.get("/api/health")

    assert health.status_code == 200
    assert health.json() == {"status": "ok", "version": VERSION, "database": "ok", "storage": "ok"}
    assert settings.version == VERSION
    assert DEFAULT_VERSION == VERSION
    assert package_name() == f"工程图纸智能台账识别系统-{VERSION}"


def test_v062_drawing_no_formats_normalization_and_misread_filters():
    examples = {
        "建施 03": "建施-03",
        "建施_03": "建施-03",
        "建施—03": "建施-03",
        "建施-A01": "建施-A-01",
        "建施-A-01": "建施-A-01",
        "JZ03": "JZ-03",
        "JG-01": "JG-01",
        "A101": "A-101",
        "S101": "S-101",
        "E-101": "E-101",
    }
    for raw, expected in examples.items():
        assert normalize_drawing_no(raw) == expected
        assert is_supported_drawing_no(raw)

    candidates = infer_candidates_from_text("图号 A101", "cad_text")
    assert any(item["normalized_value"] == "A-101" for item in candidates)
    assert not is_supported_drawing_no("KZ-1")
    assert not is_supported_drawing_no("A轴")
    assert not any(item["candidate_value"] == "KZ-1" and item["confidence"] >= 70 for item in infer_candidates_from_text("KZ-1", "cad_text"))


def test_v062_drawing_name_keywords_and_note_text_filtering():
    candidates = infer_candidates_from_text("喷淋系统图", "cad_mtext")
    assert any(item["field_name"] == "drawing_name" and item["candidate_value"] == "喷淋系统图" for item in candidates)

    note_candidates = infer_candidates_from_text("本图尺寸以毫米为单位，详见设计说明。", "cad_mtext")
    assert not any(item["field_name"] == "drawing_name" and item["confidence"] >= 70 for item in note_candidates)


def test_v062_discipline_keywords_and_priority():
    assert infer_discipline("防雷接地平面图") == "电气"
    assert infer_discipline("综合布线系统图") == "弱电"
    assert infer_discipline("A-101 给排水平面图") == "建筑"
    assert infer_discipline("S101 建筑平面图") == "结构"


def test_v062_cad_tag_mapping_and_normalization():
    assert field_for_tag("DWG_NO.") == "drawing_no"
    assert field_for_tag("DRAWING_NUMBER") == "drawing_no"
    assert field_for_tag("图纸名称及内容") == "drawing_name"
    assert field_for_tag("SHEET_TITLE") == "drawing_name"
    assert field_for_tag("PLOTDATE") == "issue_date"
    assert field_for_tag("DRAWING_DATE") == "issue_date"
    assert field_for_tag("D W G _ N O .") == "drawing_no"


def test_v062_date_formats_and_invalid_dates():
    assert normalize_issue_date("2024.6") == "2024-06-01"
    assert normalize_issue_date("2024/6") == "2024-06-01"
    assert normalize_issue_date("2024年6月") == "2024-06-01"
    assert normalize_issue_date("2024-6-1") == "2024-06-01"
    assert normalize_issue_date("2024.6.1") == "2024-06-01"
    assert normalize_issue_date("24.06.01") == "2024-06-01"
    assert normalize_issue_date("202406") == "2024-06-01"
    assert normalize_issue_date("20240601") == "2024-06-01"

    invalid = infer_candidates_from_text("2024-02-31", "cad_block_attr", tagged_field="issue_date")[0]
    assert invalid["candidate_value"] == "2024-02-31"
    assert invalid["normalized_value"] is None
    assert invalid["confidence"] <= 50


def test_v062_filename_only_ocr_empty_and_low_confidence_issues_are_generated():
    with TestClient(app) as client:
        project_id = create_project(client, "v062-issue")
        upload_result = upload(client, project_id, [("建施-62_平面布置图.pdf", make_pdf_bytes(""), "application/pdf")])
        batch_id = upload_result["id"]
        file_id = upload_result["files"][0]["id"]
        split = client.post(f"/api/files/{file_id}/split")
        sheet_id = split.json()["sheets"][0]["id"]
        assert client.post(f"/api/imports/{batch_id}/extract-text").status_code == 200
        assert client.post(f"/api/imports/{batch_id}/title-crops").status_code == 200
        assert client.post(f"/api/imports/{batch_id}/ocr-titles").status_code == 200
        _wait_for_ocr_job(client, batch_id)
        ocr_codes = issue_codes(sheet_id)
        assert client.post(f"/api/sheets/{sheet_id}/generate-candidates").status_code == 200
        assert client.post(f"/api/sheets/{sheet_id}/fuse-fields").status_code == 200

    codes = issue_codes(sheet_id)
    assert "ONLY_FROM_FILENAME" in codes
    assert "OCR_TEXT_EMPTY" in ocr_codes
    assert "PDF_TEXT_EMPTY" in ocr_codes
    assert "LOW_CONFIDENCE_NEED_REVIEW" in codes
    assert issue_template("OCR_TEXT_EMPTY")[0] == "info"
    assert issue_template("PDF_TEXT_EMPTY")[0] == "info"
    assert issue_template("ONLY_FROM_FILENAME")[0] == "warning"


def test_v062_manual_review_protection_and_repeated_steps_are_idempotent():
    with TestClient(app) as client:
        project_id = create_project(client, "v062-manual")
        upload_result = upload(client, project_id, [("manual-v062.dxf", title_block_dxf("建施-62"), "application/dxf")])
        batch_id = upload_result["id"]
        result = run_pipeline(client, batch_id, steps=["prepare_dxf_sheet", "parse_dxf", "generate_candidates", "fuse_fields"])
        sheet_id = result["steps"][1]["items"][0]["sheet_id"]
        update = client.post(
            f"/api/review/sheets/{sheet_id}/update-fields",
            json={"fields": {"drawing_no": "人工-062", "drawing_name": "人工图名", "discipline": "建筑"}},
        )
        first = client.post(f"/api/sheets/{sheet_id}/generate-candidates")
        first_counts = counts(sheet_id)
        second = client.post(f"/api/sheets/{sheet_id}/generate-candidates")
        second_counts = counts(sheet_id)
        fuse_first = client.post(f"/api/sheets/{sheet_id}/fuse-fields")
        third_counts = counts(sheet_id)
        fuse_second = client.post(f"/api/sheets/{sheet_id}/fuse-fields")
        fourth_counts = counts(sheet_id)
        sheet = client.get(f"/api/sheets/{sheet_id}").json()

    with SessionLocal() as db:
        reviewed = db.scalar(
            select(FieldValue).where(
                FieldValue.sheet_id == sheet_id,
                FieldValue.field_name == "drawing_no",
                FieldValue.is_reviewed.is_(True),
            )
        )
    assert update.status_code == 200
    assert first.status_code == second.status_code == 200
    assert fuse_first.status_code == fuse_second.status_code == 200
    assert first_counts[0] == second_counts[0]
    assert third_counts[1] == fourth_counts[1]
    assert sheet["drawing_no"] == "人工-062"
    assert reviewed is not None


def test_v062_pdf_dxf_dwg_pipeline_and_excel_regression(tmp_path: Path):
    clear_converter_tables()
    converter = write_mock_converter(tmp_path)
    with TestClient(app) as client:
        create_converter_setting(client, converter)
        project_id = create_project(client, "v062-regression")
        upload_result = upload(
            client,
            project_id,
            [
                ("建施-62_PDF.pdf", make_pdf_bytes("图号 建施-62\n图名 平面布置图"), "application/pdf"),
                ("建施-63_DXF.dxf", title_block_dxf("建施-63", "设备布置图"), "application/dxf"),
                ("建施-64_DWG.dwg", DWG_BYTES, "application/acad"),
            ],
        )
        batch_id = upload_result["id"]
        pdf_file_id = next(item["id"] for item in upload_result["files"] if item["source_format"] == "pdf")
        assert client.post(f"/api/files/{pdf_file_id}/split").status_code == 200
        assert client.post(f"/api/imports/{batch_id}/extract-text").status_code == 200
        pipeline = run_pipeline(client, batch_id)
        export = export_excel(client, project_id)

    workbook = load_workbook(settings.root_dir / export["file_path"])
    assert pipeline["summary"]["pdf_files"] == 1
    assert pipeline["summary"]["dxf_files"] == 1
    assert pipeline["summary"]["dwg_files"] == 1
    assert pipeline["summary"]["converted_success"] == 1
    assert pipeline["summary"]["parse_success"] >= 2
    assert export["ledger_row_count"] >= 3
    assert workbook["导出说明"]["B3"].value == VERSION


def test_v062_cad_json_candidate_examples_from_rule_fix_cases():
    cad_json = {
        "layers": ["HVAC-排烟"],
        "spaces": [
            {
                "texts": [{"clean_text": "JZ03"}, {"clean_text": "A轴"}],
                "mtexts": [{"clean_text": "综合管线图"}, {"clean_text": "本图未尽事宜详见设计说明"}],
                "inserts": [
                    {
                        "attribs": [
                            {"tag": "专业图号", "clean_text": "A101"},
                            {"tag": "图纸名称及内容", "clean_text": "防雷接地平面图"},
                            {"tag": "PLOTDATE", "clean_text": "2024.6"},
                        ]
                    }
                ],
            }
        ],
    }
    candidates = generate_candidates_from_cad_json(cad_json, {"original_name": "A101_综合管线图.dxf"})
    drawing_no = field_candidates(candidates, "drawing_no")
    drawing_name = field_candidates(candidates, "drawing_name")
    issue_date = field_candidates(candidates, "issue_date")
    discipline = field_candidates(candidates, "discipline")

    assert any(item["normalized_value"] == "A-101" and item["source_type"] == "cad_block_attr" for item in drawing_no)
    assert any(item["normalized_value"] == "JZ-03" for item in drawing_no)
    assert not any(item["candidate_value"] == "A轴" for item in drawing_no)
    assert any(item["candidate_value"] == "综合管线图" for item in drawing_name)
    assert not any("本图未尽事宜" in item["candidate_value"] for item in drawing_name)
    assert any(item["normalized_value"] == "2024-06-01" for item in issue_date)
    assert any(item["normalized_value"] == "暖通" and item["confidence"] <= 65 for item in discipline)


def test_v062_parse_filename_month_date_keeps_auxiliary_source():
    candidates = parse_filename("JZ03_平面布置图_202406.dxf")
    assert any(item["field_name"] == "drawing_no" and item["normalized_value"] == "JZ-03" for item in candidates)
    assert any(item["field_name"] == "issue_date" and item["candidate_value"] == "202406" and item["normalized_value"] == "2024-06-01" for item in candidates)

