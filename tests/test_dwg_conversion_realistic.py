import os
from pathlib import Path

from fastapi.testclient import TestClient

from backend.core.config import settings
from backend.core.database import SessionLocal
from backend.main import app
from backend.models.field_value import FieldValue
from backend.models.recognition_candidate import RecognitionCandidate
from dwg_test_helpers import (
    DXF_TEXT,
    clear_converter_tables,
    create_converter_setting,
    create_project,
    upload_dwg,
    upload_dxf,
)

PDF_BYTES = b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF\n"


def realistic_converter(tmp_path: Path, mode: str = "same") -> Path:
    directory = tmp_path / "中文 工具目录"
    directory.mkdir(parents=True, exist_ok=True)
    script = directory / f"mock converter {mode}.py"
    body = f"""
import sys
import time
from pathlib import Path

DXF = {DXF_TEXT!r}
mode = {mode!r}
if len(sys.argv) == 1:
    if mode == "check_fail":
        raise SystemExit(2)
    raise SystemExit(0)
input_dir = Path(sys.argv[1])
output_dir = Path(sys.argv[2])
output_dir.mkdir(parents=True, exist_ok=True)
sources = sorted(input_dir.glob("*.dwg"))
if mode == "sleep":
    time.sleep(3)
    raise SystemExit(0)
if mode == "failed":
    print("stdout before failure")
    print("stderr failure", file=sys.stderr)
    raise SystemExit(9)
if mode == "missing":
    print("no output generated")
    raise SystemExit(0)
for source in sources:
    if mode == "batch_selective" and "bad" in source.name:
        continue
    if mode == "upper":
        target = output_dir / (source.stem + ".DXF")
    elif mode == "similar":
        target = output_dir / (source.stem + "_converted.dxf")
    elif mode == "ambiguous":
        (output_dir / (source.stem + "_A.dxf")).write_text(DXF, encoding="utf-8")
        time.sleep(0.02)
        target = output_dir / (source.stem + "_B.dxf")
    else:
        target = output_dir / (source.stem + ".dxf")
    target.write_text(DXF, encoding="utf-8")
print("converted", len(sources))
print("mock stderr summary", file=sys.stderr)
raise SystemExit(0)
"""
    script.write_text(body.strip() + "\n", encoding="utf-8")
    return script


def test_converter_path_with_spaces_and_chinese_executes(tmp_path):
    clear_converter_tables()
    converter = realistic_converter(tmp_path)
    assert " " in str(converter)
    assert "中文" in str(converter)
    with TestClient(app) as client:
        setting = create_converter_setting(client, converter)
        response = client.post(f"/api/cad/converter-settings/{setting['id']}/check")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_converter_not_found_returns_structured_extra(tmp_path):
    clear_converter_tables()
    missing = tmp_path / "missing dir" / "missing.exe"
    with TestClient(app) as client:
        setting = client.post(
            "/api/cad/converter-settings",
            json={
                "converter_name": "Missing",
                "converter_exe_path": str(missing),
                "output_version": "ACAD2018",
                "output_type": "DXF",
                "is_enabled": True,
            },
        ).json()
        response = client.post(f"/api/cad/converter-settings/{setting['id']}/check")

    assert response.status_code == 404
    detail = response.json()["detail"]
    assert detail["error_code"] == "CONVERTER_NOT_FOUND"
    assert detail["extra"] == {}


def test_existing_but_not_executable_path_returns_code(tmp_path):
    clear_converter_tables()
    not_exe = tmp_path / "not-executable.txt"
    not_exe.write_text("plain text", encoding="utf-8")
    with TestClient(app) as client:
        setting = client.post(
            "/api/cad/converter-settings",
            json={
                "converter_name": "Plain Text",
                "converter_exe_path": str(not_exe),
                "output_version": "ACAD2018",
                "output_type": "DXF",
                "is_enabled": True,
            },
        ).json()
        response = client.post(f"/api/cad/converter-settings/{setting['id']}/check")

    assert response.status_code == 400
    assert response.json()["detail"]["error_code"] == "CONVERTER_NOT_EXECUTABLE"


def test_dwg_upload_pending_with_chinese_and_space_filename():
    clear_converter_tables()
    with TestClient(app) as client:
        project_id = create_project(client, "v0.3.1真实DWG转换测试")
        upload = upload_dwg(client, project_id, "结构 首层 平面图.dwg")

    file = upload["files"][0]
    assert file["source_format"] == "dwg"
    assert file["file_ext"] == ".dwg"
    assert file["convert_status"] == "pending"


def test_single_convert_success_and_logs_are_truncated(tmp_path):
    clear_converter_tables()
    converter = realistic_converter(tmp_path)
    with TestClient(app) as client:
        create_converter_setting(client, converter)
        project_id = create_project(client)
        upload = upload_dwg(client, project_id, "中文 文件.dwg")
        file_id = upload["files"][0]["id"]
        response = client.post(f"/api/files/{file_id}/convert-dwg-to-dxf")
        runs = client.get(f"/api/files/{file_id}/cad-conversion-runs").json()

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert (settings.root_dir / data["converted_file_path"]).exists()
    assert runs[0]["status"] == "success"
    assert runs[0]["stdout_log"] is not None
    assert runs[0]["stderr_log"] is not None
    assert len(runs[0]["stdout_log"]) <= 5000
    assert len(runs[0]["stderr_log"]) <= 5000


def test_uppercase_dxf_output_is_detected(tmp_path):
    clear_converter_tables()
    converter = realistic_converter(tmp_path, "upper")
    with TestClient(app) as client:
        create_converter_setting(client, converter)
        project_id = create_project(client)
        file_id = upload_dwg(client, project_id, "upper-output.dwg")["files"][0]["id"]
        response = client.post(f"/api/files/{file_id}/convert-dwg-to-dxf")

    assert response.status_code == 200
    assert response.json()["status"] == "success"
    assert response.json()["converted_file_path"].endswith(".dxf")


def test_similar_output_name_is_detected(tmp_path):
    clear_converter_tables()
    converter = realistic_converter(tmp_path, "similar")
    with TestClient(app) as client:
        create_converter_setting(client, converter)
        project_id = create_project(client)
        file_id = upload_dwg(client, project_id, "similar-name.dwg")["files"][0]["id"]
        response = client.post(f"/api/files/{file_id}/convert-dwg-to-dxf")

    assert response.status_code == 200
    assert response.json()["status"] == "success"


def test_ambiguous_output_records_warning(tmp_path):
    clear_converter_tables()
    converter = realistic_converter(tmp_path, "ambiguous")
    with TestClient(app) as client:
        create_converter_setting(client, converter)
        project_id = create_project(client)
        file_id = upload_dwg(client, project_id, "ambiguous.dwg")["files"][0]["id"]
        response = client.post(f"/api/files/{file_id}/convert-dwg-to-dxf")
        runs = client.get(f"/api/files/{file_id}/cad-conversion-runs").json()

    assert response.status_code == 200
    assert response.json()["status"] == "success"
    assert response.json()["warning_code"] == "DWG_CONVERT_OUTPUT_AMBIGUOUS"
    assert runs[0]["error_code"] == "DWG_CONVERT_OUTPUT_AMBIGUOUS"


def test_success_without_output_returns_missing(tmp_path):
    clear_converter_tables()
    converter = realistic_converter(tmp_path, "missing")
    with TestClient(app) as client:
        create_converter_setting(client, converter)
        project_id = create_project(client)
        file_id = upload_dwg(client, project_id, "missing.dwg")["files"][0]["id"]
        response = client.post(f"/api/files/{file_id}/convert-dwg-to-dxf")

    assert response.status_code == 200
    assert response.json()["status"] == "failed"
    assert response.json()["error_code"] == "DWG_CONVERT_OUTPUT_MISSING"


def test_non_zero_converter_returns_failed(tmp_path):
    clear_converter_tables()
    converter = realistic_converter(tmp_path, "failed")
    with TestClient(app) as client:
        create_converter_setting(client, converter)
        project_id = create_project(client)
        file_id = upload_dwg(client, project_id, "failed.dwg")["files"][0]["id"]
        response = client.post(f"/api/files/{file_id}/convert-dwg-to-dxf")

    assert response.status_code == 200
    assert response.json()["status"] == "failed"
    assert response.json()["error_code"] == "DWG_CONVERT_FAILED"


def test_timeout_returns_failed(monkeypatch, tmp_path):
    clear_converter_tables()
    converter = realistic_converter(tmp_path, "sleep")
    monkeypatch.setattr("backend.core.config.settings.convert_timeout_seconds", 1)
    with TestClient(app) as client:
        create_converter_setting(client, converter)
        project_id = create_project(client)
        file_id = upload_dwg(client, project_id, "timeout.dwg")["files"][0]["id"]
        response = client.post(f"/api/files/{file_id}/convert-dwg-to-dxf")

    assert response.status_code == 200
    assert response.json()["status"] == "failed"
    assert response.json()["error_code"] == "DWG_CONVERT_TIMEOUT"


def test_batch_convert_single_failure_does_not_block_others(tmp_path):
    clear_converter_tables()
    converter = realistic_converter(tmp_path, "batch_selective")
    with TestClient(app) as client:
        create_converter_setting(client, converter)
        project_id = create_project(client)
        upload = client.post(
            f"/api/projects/{project_id}/imports",
            files=[
                ("files", ("good.dwg", b"dwg", "application/acad")),
                ("files", ("bad.dwg", b"dwg", "application/acad")),
            ],
        )
        batch_id = upload.json()["id"]
        response = client.post(f"/api/imports/{batch_id}/convert-dwg-to-dxf")

    assert response.status_code == 200
    data = response.json()
    assert data["success_count"] == 1
    assert data["failed_count"] == 1
    assert data["items"][1]["error_code"] == "DWG_CONVERT_OUTPUT_MISSING"


def test_converted_dwg_full_dxf_candidate_fusion_review_export_flow(tmp_path):
    clear_converter_tables()
    converter = realistic_converter(tmp_path)
    with TestClient(app) as client:
        create_converter_setting(client, converter)
        project_id = create_project(client)
        file_id = upload_dwg(client, project_id, "full-flow.dwg")["files"][0]["id"]
        convert = client.post(f"/api/files/{file_id}/convert-dwg-to-dxf")
        parse = client.post(f"/api/files/{file_id}/parse-dxf")
        sheet_id = parse.json()["sheet_id"]
        candidates = client.post(f"/api/sheets/{sheet_id}/generate-candidates")
        fusion = client.post(f"/api/sheets/{sheet_id}/fuse-fields")
        review = client.patch(
            f"/api/sheets/{sheet_id}/fields",
            json={
                "fields": {
                    "drawing_no": "A-001",
                    "drawing_name": "首层平面图",
                    "discipline": "建筑",
                },
                "note": "DWG 转换后人工校核",
            },
        )
        confirm = client.post(f"/api/sheets/{sheet_id}/confirm", json={"force": True, "note": "确认"})
        export = client.post(
            f"/api/projects/{project_id}/exports/excel",
            json={"confirm_incomplete": True, "include_issues": True, "filter": None},
        )

    assert convert.status_code == 200
    assert parse.status_code == 200
    assert candidates.status_code == 200
    assert candidates.json()["candidate_count"] >= 1
    assert fusion.status_code == 200
    assert review.status_code == 200
    assert confirm.status_code == 200
    assert export.status_code == 200
    assert (settings.root_dir / export.json()["file_path"]).exists()
    with SessionLocal() as db:
        assert db.query(RecognitionCandidate).filter(RecognitionCandidate.sheet_id == sheet_id).count() >= 1
        assert db.query(FieldValue).filter(FieldValue.sheet_id == sheet_id).count() >= 1


def test_unconverted_dwg_parse_dxf_returns_code():
    clear_converter_tables()
    with TestClient(app) as client:
        project_id = create_project(client)
        file_id = upload_dwg(client, project_id, "not-converted.dwg")["files"][0]["id"]
        response = client.post(f"/api/files/{file_id}/parse-dxf")

    assert response.status_code == 400
    assert response.json()["detail"]["error_code"] == "DWG_NOT_CONVERTED"


def test_pdf_and_dxf_old_flows_still_work():
    clear_converter_tables()
    with TestClient(app) as client:
        project_id = create_project(client)
        pdf = client.post(
            f"/api/projects/{project_id}/imports",
            files=[("files", ("old.pdf", PDF_BYTES, "application/pdf"))],
        )
        dxf = upload_dxf(client, project_id, "old.dxf")
        parse = client.post(f"/api/files/{dxf['files'][0]['id']}/parse-dxf")

    assert pdf.status_code == 201
    assert parse.status_code == 200
    assert parse.json()["status"] == "success"


def test_manual_confirmed_field_is_not_overwritten_after_refusion(tmp_path):
    clear_converter_tables()
    converter = realistic_converter(tmp_path)
    with TestClient(app) as client:
        create_converter_setting(client, converter)
        project_id = create_project(client)
        file_id = upload_dwg(client, project_id, "manual-protect.dwg")["files"][0]["id"]
        client.post(f"/api/files/{file_id}/convert-dwg-to-dxf")
        parse = client.post(f"/api/files/{file_id}/parse-dxf")
        sheet_id = parse.json()["sheet_id"]
        client.post(f"/api/sheets/{sheet_id}/generate-candidates")
        client.patch(
            f"/api/sheets/{sheet_id}/fields",
            json={"fields": {"drawing_no": "人工-001"}, "note": "人工确认"},
        )
        client.post(f"/api/sheets/{sheet_id}/fuse-fields")
        values = client.get(f"/api/sheets/{sheet_id}/field-values").json()

    drawing_no = next(item for item in values if item["field_name"] == "drawing_no")
    assert drawing_no["display_value"] == "人工-001"
    assert drawing_no["is_reviewed"] is True
