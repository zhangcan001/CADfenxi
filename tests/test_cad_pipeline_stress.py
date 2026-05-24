import io
from pathlib import Path

import ezdxf
import pymupdf as fitz
import pytest
from fastapi.testclient import TestClient

from backend.core.database import SessionLocal
from backend.main import app
from backend.models.drawing_issue import DrawingIssue
from backend.models.drawing_sheet import DrawingSheet
from backend.models.field_value import FieldValue
from backend.models.recognition_candidate import RecognitionCandidate
from dwg_test_helpers import (
    DWG_BYTES,
    DXF_TEXT,
    clear_converter_tables,
    create_converter_setting,
    create_project,
    run_cad_pipeline_blocking,
    upload_dwg,
    upload_dxf,
    write_mock_converter,
)


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as test_client:
        yield test_client


def dxf_bytes(text: str = "建施-01") -> bytes:
    doc = ezdxf.new("R2010")
    if text:
        doc.modelspace().add_text(text, dxfattribs={"insert": (0, 0, 0)})
    stream = io.StringIO()
    doc.write(stream)
    return stream.getvalue().encode("utf-8")


def pdf_bytes(text: str = "PDF drawing") -> bytes:
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), text)
    payload = doc.tobytes()
    doc.close()
    return payload


def upload_files(client: TestClient, project_id: int, files: list[tuple[str, bytes, str]]) -> dict:
    response = client.post(
        f"/api/projects/{project_id}/imports",
        files=[("files", item) for item in files],
    )
    assert response.status_code == 201
    return response.json()


def run_pipeline(client: TestClient, batch_id: int, **overrides) -> dict:
    payload = {
        "steps": [
            "convert_dwg",
            "prepare_dxf_sheet",
            "parse_dxf",
            "generate_candidates",
            "fuse_fields",
        ],
        "skip_completed": True,
        "continue_on_error": True,
    }
    payload.update(overrides)
    return run_cad_pipeline_blocking(client, batch_id, payload)


def sheet_count(batch_id: int) -> int:
    with SessionLocal() as db:
        return db.query(DrawingSheet).filter(DrawingSheet.batch_id == batch_id).count()


def candidate_count(batch_id: int) -> int:
    with SessionLocal() as db:
        return db.query(RecognitionCandidate).filter(RecognitionCandidate.batch_id == batch_id).count()


def open_issue_count(batch_id: int) -> int:
    with SessionLocal() as db:
        return db.query(DrawingIssue).filter(
            DrawingIssue.batch_id == batch_id,
            DrawingIssue.status == "open",
        ).count()


def field_value_count(batch_id: int) -> int:
    with SessionLocal() as db:
        return db.query(FieldValue).filter(FieldValue.batch_id == batch_id).count()


def write_partial_converter(tmp_path: Path) -> Path:
    script = tmp_path / "mock_converter_partial.py"
    script.write_text(
        f"""
import sys
from pathlib import Path

if len(sys.argv) == 1:
    raise SystemExit(0)
input_dir = Path(sys.argv[1])
output_dir = Path(sys.argv[2])
output_dir.mkdir(parents=True, exist_ok=True)
failed = False
for source in input_dir.glob("*.dwg"):
    if "bad" in source.name.lower():
        failed = True
        continue
    (output_dir / (source.stem + ".dxf")).write_text({DXF_TEXT!r}, encoding="utf-8")
raise SystemExit(2 if failed else 0)
""".strip()
        + "\n",
        encoding="utf-8",
    )
    return script


def assert_summary_shape(result: dict) -> None:
    summary = result["summary"]
    assert "duration_seconds" in summary
    assert "start_time" in summary
    assert "finish_time" in summary
    assert "pdf_files" in summary
    assert "error_count" in summary
    assert "warning_count" in summary
    for step in result["steps"]:
        assert "duration_seconds" in step
        assert "success_count" in step
        assert "failed_count" in step
        assert "skipped_count" in step
        assert "errors" in step


def test_pure_dxf_batch_pipeline_summary_and_excel_consistency(client: TestClient):
    clear_converter_tables()
    project_id = create_project(client, "stress pure dxf")
    files = [
        (f"批量 DXF {index:02d}.dxf", dxf_bytes(f"建施-{index:02d}"), "application/dxf")
        for index in range(20)
    ]
    upload = upload_files(client, project_id, files)
    result = run_pipeline(
        client,
        upload["id"],
        steps=["prepare_dxf_sheet", "parse_dxf", "generate_candidates", "fuse_fields"],
    )
    export = client.post(
        f"/api/projects/{project_id}/exports/excel",
        json={"confirm_incomplete": True, "include_issues": True, "filter": None},
    )

    assert result["status"] in {"success", "completed_with_errors"}
    assert result["summary"]["dxf_files"] == 20
    assert result["summary"]["parse_success"] == 20
    assert result["summary"]["candidate_success"] == 20
    assert result["summary"]["fusion_success"] == 20
    assert sheet_count(upload["id"]) == 20
    assert export.status_code == 200
    assert export.json()["sheet_count"] == sheet_count(upload["id"])
    assert_summary_shape(result)


def test_pure_dwg_batch_pipeline_uses_mock_converter(client: TestClient, tmp_path):
    clear_converter_tables()
    converter = write_mock_converter(tmp_path)
    create_converter_setting(client, converter)
    project_id = create_project(client, "stress pure dwg")
    files = [(f"中文 DWG {index:02d}.dwg", DWG_BYTES, "application/acad") for index in range(10)]
    upload = upload_files(client, project_id, files)
    result = run_pipeline(client, upload["id"])

    assert result["status"] == "success"
    assert result["summary"]["dwg_files"] == 10
    assert result["summary"]["converted_success"] == 10
    assert result["summary"]["parse_success"] == 10
    assert result["summary"]["fusion_success"] == 10
    assert_summary_shape(result)


def test_mixed_dwg_dxf_pdf_pipeline_skips_pdf(client: TestClient, tmp_path):
    clear_converter_tables()
    converter = write_mock_converter(tmp_path)
    create_converter_setting(client, converter)
    project_id = create_project(client, "stress mixed")
    upload = upload_files(
        client,
        project_id,
        [
            ("混合 01.dwg", DWG_BYTES, "application/acad"),
            ("混合 02.dwg", DWG_BYTES, "application/acad"),
            ("混合 03.dxf", DXF_TEXT.encode("utf-8"), "application/dxf"),
            ("混合 04.dxf", dxf_bytes("建施-04"), "application/dxf"),
            ("混合 05.pdf", pdf_bytes(), "application/pdf"),
        ],
    )
    result = run_pipeline(client, upload["id"])

    assert result["summary"]["pdf_files"] == 1
    assert result["summary"]["dwg_files"] == 2
    assert result["summary"]["dxf_files"] == 2
    assert result["summary"]["converted_success"] == 2
    assert result["summary"]["parse_success"] == 4
    assert sheet_count(upload["id"]) == 4


def test_repeated_pipeline_is_idempotent_for_sheets_candidates_issues_and_allows_rerun(client: TestClient):
    clear_converter_tables()
    project_id = create_project(client, "stress repeated")
    upload = upload_files(
        client,
        project_id,
        [(f"repeat {index}.dxf", dxf_bytes(f"建施-{index}"), "application/dxf") for index in range(3)],
    )
    first = run_pipeline(
        client,
        upload["id"],
        steps=["prepare_dxf_sheet", "parse_dxf", "generate_candidates", "fuse_fields"],
    )
    first_sheets = sheet_count(upload["id"])
    first_candidates = candidate_count(upload["id"])
    first_issues = open_issue_count(upload["id"])
    skipped = run_pipeline(client, upload["id"])
    rerun = run_pipeline(client, upload["id"], skip_completed=False)

    assert first["summary"]["fusion_success"] == 3
    assert skipped["status"] == "skipped"
    assert rerun["status"] == "success"
    assert sheet_count(upload["id"]) == first_sheets
    assert candidate_count(upload["id"]) == first_candidates
    assert open_issue_count(upload["id"]) == first_issues


def test_manual_reviewed_field_is_not_overwritten_by_rerun(client: TestClient):
    clear_converter_tables()
    project_id = create_project(client, "stress manual")
    upload = upload_dxf(client, project_id, "manual.dxf")
    result = run_pipeline(
        client,
        upload["id"],
        steps=["prepare_dxf_sheet", "parse_dxf", "generate_candidates", "fuse_fields"],
    )
    sheet_id = result["steps"][1]["items"][0]["sheet_id"]
    manual = client.patch(
        f"/api/sheets/{sheet_id}/fields",
        json={"fields": {"drawing_no": "人工-压测-001"}, "note": "manual"},
    )
    rerun = run_pipeline(client, upload["id"], skip_completed=False)
    sheet = client.get(f"/api/sheets/{sheet_id}").json()

    assert manual.status_code == 200
    assert rerun["status"] == "success"
    assert sheet["drawing_no"] == "人工-压测-001"


def test_continue_on_error_true_reports_clear_converter_error(client: TestClient, tmp_path):
    clear_converter_tables()
    converter = write_mock_converter(tmp_path, mode="failed")
    create_converter_setting(client, converter)
    project_id = create_project(client, "stress converter error")
    upload = upload_files(
        client,
        project_id,
        [
            ("bad file.dwg", DWG_BYTES, "application/acad"),
            ("good file.dxf", DXF_TEXT.encode("utf-8"), "application/dxf"),
        ],
    )
    result = run_pipeline(client, upload["id"], continue_on_error=True)

    assert result["status"] == "completed_with_errors"
    assert result["summary"]["converted_failed"] == 1
    assert result["summary"]["parse_success"] == 1
    assert result["errors"][0]["file_id"] is not None
    assert result["errors"][0]["file_name"] == "bad file.dwg"
    assert result["errors"][0]["step"] == "convert_dwg"
    assert result["errors"][0]["error_code"] == "DWG_CONVERT_FAILED"


def test_continue_on_error_false_stops_at_failure(client: TestClient, tmp_path):
    clear_converter_tables()
    converter = write_mock_converter(tmp_path, mode="failed")
    create_converter_setting(client, converter)
    project_id = create_project(client, "stress stop")
    upload = upload_files(
        client,
        project_id,
        [
            ("bad.dwg", DWG_BYTES, "application/acad"),
            ("good.dxf", DXF_TEXT.encode("utf-8"), "application/dxf"),
        ],
    )
    result = run_pipeline(client, upload["id"], continue_on_error=False)

    assert result["status"] == "failed"
    assert [step["step"] for step in result["steps"]] == ["convert_dwg"]
    assert result["summary"]["converted_failed"] == 1


def test_dxf_parse_failure_has_file_name_and_code(client: TestClient):
    clear_converter_tables()
    project_id = create_project(client, "stress parse failure")
    upload = upload_files(client, project_id, [("坏 DXF.dxf", b"not a dxf", "application/dxf")])
    result = run_pipeline(
        client,
        upload["id"],
        steps=["prepare_dxf_sheet", "parse_dxf", "generate_candidates"],
    )

    assert result["status"] == "completed_with_errors"
    assert result["summary"]["parse_failed"] == 1
    assert result["errors"][0]["file_name"] == "坏 DXF.dxf"
    assert result["errors"][0]["step"] == "parse_dxf"
    assert result["errors"][0]["error_code"]


def test_candidate_empty_error_is_clear(client: TestClient):
    clear_converter_tables()
    project_id = create_project(client, "stress empty candidates")
    upload = upload_files(client, project_id, [("empty.dxf", dxf_bytes(""), "application/dxf")])
    result = run_pipeline(
        client,
        upload["id"],
        steps=["prepare_dxf_sheet", "parse_dxf", "generate_candidates"],
    )

    assert result["status"] == "completed_with_errors"
    assert result["summary"]["candidate_failed"] == 1
    assert result["errors"][0]["step"] == "generate_candidates"
    assert result["errors"][0]["error_code"] in {"NO_CANDIDATES", "DXF_CANDIDATE_EMPTY"}


def test_existing_pdf_dxf_dwg_flows_still_work(client: TestClient, tmp_path):
    clear_converter_tables()
    converter = write_mock_converter(tmp_path)
    create_converter_setting(client, converter)
    project_id = create_project(client, "stress old flows")
    dxf_upload = upload_dxf(client, project_id, "old.dxf")
    dxf_parse = client.post(f"/api/files/{dxf_upload['files'][0]['id']}/parse-dxf")
    dwg_upload = upload_dwg(client, project_id, "old.dwg")
    dwg_convert = client.post(f"/api/files/{dwg_upload['files'][0]['id']}/convert-dwg-to-dxf")
    dwg_parse = client.post(f"/api/files/{dwg_upload['files'][0]['id']}/parse-dxf")
    pdf_upload = upload_files(client, project_id, [("old.pdf", pdf_bytes(), "application/pdf")])
    pdf_file_id = pdf_upload["files"][0]["id"]
    pdf_split = client.post(f"/api/files/{pdf_file_id}/split")

    assert dxf_parse.status_code == 200
    assert dwg_convert.status_code == 200
    assert dwg_parse.status_code == 200
    assert pdf_split.status_code == 200
