import io

import ezdxf
import pymupdf as fitz
from fastapi.testclient import TestClient

from backend.core.database import SessionLocal
from backend.main import app
from backend.models.drawing_file import DrawingFile
from backend.models.drawing_sheet import DrawingSheet
from backend.models.field_value import FieldValue
from backend.models.recognition_candidate import RecognitionCandidate
from dwg_test_helpers import (
    DWG_BYTES,
    DXF_TEXT,
    clear_converter_tables,
    create_converter_setting,
    create_project,
    upload_dwg,
    upload_dxf,
    write_mock_converter,
)


def make_pdf_bytes(text: str = "PDF drawing") -> bytes:
    document = fitz.open()
    page = document.new_page()
    page.insert_text((72, 72), text)
    payload = document.tobytes()
    document.close()
    return payload


def dxf_bytes(text: str = "建施-11") -> bytes:
    doc = ezdxf.new("R2010")
    doc.modelspace().add_text(text, dxfattribs={"insert": (0, 0, 0)})
    stream = io.StringIO()
    doc.write(stream)
    return stream.getvalue().encode("utf-8")


def upload_mixed(client: TestClient, project_id: int, files: list[tuple[str, bytes, str]]) -> dict:
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
    response = client.post(f"/api/imports/{batch_id}/cad-pipeline", json=payload)
    assert response.status_code == 200, response.text
    return response.json()


def sheet_count_for_file(file_id: int) -> int:
    with SessionLocal() as db:
        return db.query(DrawingSheet).filter(DrawingSheet.file_id == file_id).count()


def candidate_count(sheet_id: int) -> int:
    with SessionLocal() as db:
        return db.query(RecognitionCandidate).filter(RecognitionCandidate.sheet_id == sheet_id).count()


def field_values(sheet_id: int) -> dict[str, FieldValue]:
    with SessionLocal() as db:
        values = db.query(FieldValue).filter(FieldValue.sheet_id == sheet_id).all()
        return {value.field_name: value for value in values}


def test_pipeline_handles_pure_dxf_batch_and_exports_excel():
    clear_converter_tables()
    with TestClient(app) as client:
        project_id = create_project(client, "pipeline pure dxf")
        upload = upload_dxf(client, project_id, "pipeline-pure.dxf")
        batch_id = upload["id"]

        result = run_pipeline(client, batch_id, steps=[
            "prepare_dxf_sheet",
            "parse_dxf",
            "generate_candidates",
            "fuse_fields",
        ])
        sheets = client.get(f"/api/projects/{project_id}/sheets").json()["items"]
        export_response = client.post(
            f"/api/projects/{project_id}/exports/excel",
            json={"confirm_incomplete": True, "include_issues": True, "filter": None},
        )

    assert result["status"] == "success"
    assert result["summary"]["dxf_files"] == 1
    assert result["summary"]["sheet_prepared_success"] == 1
    assert result["summary"]["parse_success"] == 1
    assert result["summary"]["candidate_success"] == 1
    assert result["summary"]["fusion_success"] == 1
    assert sheets and sheets[0]["source_format"] == "dxf"
    assert export_response.status_code == 200


def test_pipeline_handles_mixed_dwg_and_dxf_batch(tmp_path):
    clear_converter_tables()
    converter = write_mock_converter(tmp_path)
    with TestClient(app) as client:
        create_converter_setting(client, converter)
        project_id = create_project(client, "pipeline mixed")
        upload = upload_mixed(
            client,
            project_id,
            [
                ("mixed.dwg", DWG_BYTES, "application/acad"),
                ("mixed.dxf", DXF_TEXT.encode("utf-8"), "application/dxf"),
            ],
        )
        result = run_pipeline(client, upload["id"])

    assert result["status"] == "success"
    assert result["summary"]["dwg_files"] == 1
    assert result["summary"]["dxf_files"] == 1
    assert result["summary"]["converted_success"] == 1
    assert result["summary"]["parse_success"] == 2
    assert result["summary"]["candidate_success"] == 2
    assert result["summary"]["fusion_success"] == 2


def test_pipeline_convert_dwg_uses_mock_converter(tmp_path):
    clear_converter_tables()
    converter = write_mock_converter(tmp_path)
    with TestClient(app) as client:
        create_converter_setting(client, converter)
        project_id = create_project(client, "pipeline mock converter")
        upload = upload_dwg(client, project_id, "convert-me.dwg")
        result = run_pipeline(client, upload["id"], steps=["convert_dwg"])

    assert result["summary"]["converted_success"] == 1
    assert result["steps"][0]["status"] == "success"


def test_pipeline_prepare_dxf_sheet_is_idempotent():
    clear_converter_tables()
    with TestClient(app) as client:
        project_id = create_project(client, "pipeline prepare idempotent")
        upload = upload_dxf(client, project_id, "repeat.dxf")
        file_id = upload["files"][0]["id"]
        first = run_pipeline(client, upload["id"], steps=["prepare_dxf_sheet"])
        second = run_pipeline(client, upload["id"], steps=["prepare_dxf_sheet"])

    assert first["summary"]["sheet_prepared_success"] == 1
    assert second["status"] == "skipped"
    assert second["summary"]["skipped_count"] == 1
    assert sheet_count_for_file(file_id) == 1


def test_pipeline_generates_cad_json_candidates_and_field_values():
    clear_converter_tables()
    with TestClient(app) as client:
        project_id = create_project(client, "pipeline full dxf")
        upload = upload_mixed(
            client,
            project_id,
            [("建施-12_一层平面图_A_20260521.dxf", dxf_bytes("建施-12"), "application/dxf")],
        )
        result = run_pipeline(client, upload["id"], steps=[
            "prepare_dxf_sheet",
            "parse_dxf",
            "generate_candidates",
            "fuse_fields",
        ])
        sheet_id = result["steps"][1]["items"][0]["sheet_id"]
        parse_summary = client.get(f"/api/sheets/{sheet_id}/cad-parse")

    assert parse_summary.status_code == 200
    assert parse_summary.json()["counts"]["text_count"] >= 1
    assert candidate_count(sheet_id) > 0
    assert field_values(sheet_id)


def test_pipeline_skip_completed_and_rerun_repeatable_steps():
    clear_converter_tables()
    with TestClient(app) as client:
        project_id = create_project(client, "pipeline rerun")
        upload = upload_dxf(client, project_id, "rerun.dxf")
        first = run_pipeline(client, upload["id"], steps=[
            "prepare_dxf_sheet",
            "parse_dxf",
            "generate_candidates",
        ])
        sheet_id = first["steps"][1]["items"][0]["sheet_id"]
        first_count = candidate_count(sheet_id)
        skipped = run_pipeline(client, upload["id"], steps=["generate_candidates"], skip_completed=True)
        rerun = run_pipeline(client, upload["id"], steps=["generate_candidates"], skip_completed=False)
        second_count = candidate_count(sheet_id)

    assert skipped["status"] == "skipped"
    assert rerun["status"] == "success"
    assert second_count == first_count


def test_pipeline_continue_on_error_true_keeps_processing_dxf(tmp_path):
    clear_converter_tables()
    converter = write_mock_converter(tmp_path, mode="failed")
    with TestClient(app) as client:
        create_converter_setting(client, converter)
        project_id = create_project(client, "pipeline continue")
        upload = upload_mixed(
            client,
            project_id,
            [
                ("bad.dwg", DWG_BYTES, "application/acad"),
                ("good.dxf", DXF_TEXT.encode("utf-8"), "application/dxf"),
            ],
        )
        result = run_pipeline(client, upload["id"], continue_on_error=True)

    assert result["status"] == "completed_with_errors"
    assert result["summary"]["converted_failed"] == 1
    assert result["summary"]["parse_success"] == 1
    assert result["errors"][0]["error_code"] == "DWG_CONVERT_FAILED"


def test_pipeline_continue_on_error_false_stops_after_first_failure(tmp_path):
    clear_converter_tables()
    converter = write_mock_converter(tmp_path, mode="failed")
    with TestClient(app) as client:
        create_converter_setting(client, converter)
        project_id = create_project(client, "pipeline stop")
        upload = upload_mixed(
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


def test_pipeline_missing_converter_returns_config_error():
    clear_converter_tables()
    with TestClient(app) as client:
        project_id = create_project(client, "pipeline no converter")
        upload = upload_dwg(client, project_id, "needs-converter.dwg")
        result = run_pipeline(client, upload["id"], steps=["convert_dwg"])

    assert result["status"] == "failed"
    assert result["errors"][0]["error_code"] == "CONVERTER_NOT_CONFIGURED"


def test_pipeline_preserves_manual_reviewed_fields():
    clear_converter_tables()
    with TestClient(app) as client:
        project_id = create_project(client, "pipeline manual protect")
        upload = upload_dxf(client, project_id, "manual-protect.dxf")
        first = run_pipeline(client, upload["id"], steps=[
            "prepare_dxf_sheet",
            "parse_dxf",
            "generate_candidates",
            "fuse_fields",
        ])
        sheet_id = first["steps"][1]["items"][0]["sheet_id"]
        manual = client.patch(
            f"/api/sheets/{sheet_id}/fields",
            json={"fields": {"drawing_no": "人工-001"}, "note": "人工确认"},
        )
        second = run_pipeline(client, upload["id"], steps=[
            "generate_candidates",
            "fuse_fields",
        ], skip_completed=False)
        sheet = client.get(f"/api/sheets/{sheet_id}").json()

    assert manual.status_code == 200
    assert second["status"] == "success"
    assert sheet["drawing_no"] == "人工-001"
    assert field_values(sheet_id)["drawing_no"].is_reviewed is True


def test_pipeline_does_not_affect_pdf_sheets_and_pdf_old_flow_still_works():
    clear_converter_tables()
    with TestClient(app) as client:
        project_id = create_project(client, "pipeline pdf untouched")
        upload = upload_mixed(
            client,
            project_id,
            [
                ("old.pdf", make_pdf_bytes("建施-77 PDF"), "application/pdf"),
                ("old.dxf", DXF_TEXT.encode("utf-8"), "application/dxf"),
            ],
        )
        pdf_file_id = next(item["id"] for item in upload["files"] if item["source_format"] == "pdf")
        split = client.post(f"/api/files/{pdf_file_id}/split")
        result = run_pipeline(client, upload["id"], steps=[
            "prepare_dxf_sheet",
            "parse_dxf",
            "generate_candidates",
            "fuse_fields",
        ])

    assert split.status_code == 200
    assert result["summary"]["parse_success"] == 1
    assert sheet_count_for_file(pdf_file_id) == 1


def test_existing_dxf_and_dwg_flows_still_work(tmp_path):
    clear_converter_tables()
    converter = write_mock_converter(tmp_path)
    with TestClient(app) as client:
        create_converter_setting(client, converter)
        project_id = create_project(client, "pipeline old flows")
        dxf_upload = upload_dxf(client, project_id, "old-flow.dxf")
        dxf_parse = client.post(f"/api/files/{dxf_upload['files'][0]['id']}/parse-dxf")
        dwg_upload = upload_dwg(client, project_id, "old-flow.dwg")
        convert = client.post(f"/api/files/{dwg_upload['files'][0]['id']}/convert-dwg-to-dxf")
        parse = client.post(f"/api/files/{dwg_upload['files'][0]['id']}/parse-dxf")

    assert dxf_parse.status_code == 200
    assert dxf_parse.json()["status"] == "success"
    assert convert.status_code == 200
    assert convert.json()["status"] == "success"
    assert parse.status_code == 200
    assert parse.json()["status"] == "success"
