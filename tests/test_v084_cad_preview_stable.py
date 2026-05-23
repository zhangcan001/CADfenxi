import zipfile
from pathlib import Path

from fastapi.testclient import TestClient

from backend.core.config import settings
from backend.core.database import SessionLocal
from backend.main import app
from backend.models.drawing_file import DrawingFile
from backend.models.drawing_sheet import DrawingSheet
from dwg_test_helpers import DWG_BYTES, clear_converter_tables, create_converter_setting, write_mock_converter
from scripts.build_portable_package import build_portable_package, package_name
from test_cad_preview import prepare_dxf_sheet
from test_full_flow_stability_v055 import make_pdf_bytes, title_block_dxf
from test_project_backup_restore import backup_project, create_project, upload_files


VERSION = "v1.0.2-fast-stable"
ROOT = Path(__file__).resolve().parents[1]


def test_v084_health_version_and_release_documents():
    with TestClient(app) as client:
        health = client.get("/api/health")

    assert health.status_code == 200
    assert health.json() == {"status": "ok", "version": VERSION, "database": "ok", "storage": "ok"}
    assert settings.version == VERSION
    assert (ROOT / "docs" / "CAD_PREVIEW_STABILITY_REPORT_v0.8.4.md").is_file()
    assert (ROOT / "docs" / "RELEASE_CHECKLIST_v1.0-local-stable.md").is_file()


def test_v084_dxf_single_preview_pipeline_and_excel_regression():
    with TestClient(app) as client:
        project_id = create_project(client, "v0.8.4 DXF 单张预览")
        file_id, sheet_id, _batch_id = prepare_dxf_sheet(client, project_id, "v084-single.dxf")
        parse = client.post(f"/api/files/{file_id}/parse-dxf")
        candidates = client.post(f"/api/sheets/{sheet_id}/generate-candidates")
        fusion = client.post(f"/api/sheets/{sheet_id}/fuse-fields")
        preview = client.post(f"/api/sheets/{sheet_id}/cad-preview")
        image = client.get(f"/api/sheets/{sheet_id}/cad-preview-image")
        export = client.post(
            f"/api/projects/{project_id}/exports/excel",
            json={"confirm_incomplete": True, "include_issues": True, "filter": None},
        )
        sheet = client.get(f"/api/sheets/{sheet_id}").json()

    assert parse.status_code == 200, parse.text
    assert candidates.status_code == 200, candidates.text
    assert fusion.status_code == 200, fusion.text
    assert preview.status_code == 200, preview.text
    assert preview.json()["status"] == "success"
    assert sheet["cad_preview_status"] == "success"
    assert (settings.root_dir / sheet["cad_preview_path"]).is_file()
    assert image.status_code == 200
    assert image.headers["content-type"].startswith("image/png")
    assert image.content.startswith(b"\x89PNG")
    assert export.status_code == 200, export.text


def test_v084_missing_preview_errors_are_structured_and_force_regenerates():
    with TestClient(app) as client:
        project_id = create_project(client, "v0.8.4 预览缺失恢复")
        _file_id, sheet_id, batch_id = prepare_dxf_sheet(client, project_id, "v084-missing.dxf")
        not_generated = client.get(f"/api/sheets/{sheet_id}/cad-preview-image")
        first = client.post(
            f"/api/imports/{batch_id}/cad-preview",
            json={"skip_completed": True, "force": False, "continue_on_error": True},
        )
        with SessionLocal() as db:
            sheet = db.get(DrawingSheet, sheet_id)
            assert sheet and sheet.cad_preview_path
            (settings.root_dir / sheet.cad_preview_path).unlink()
        missing = client.get(f"/api/sheets/{sheet_id}/cad-preview-image")
        regenerated = client.post(
            f"/api/imports/{batch_id}/cad-preview",
            json={"skip_completed": True, "force": False, "continue_on_error": True},
        )
        skipped = client.post(
            f"/api/imports/{batch_id}/cad-preview",
            json={"skip_completed": True, "force": False, "continue_on_error": True},
        )
        forced = client.post(
            f"/api/imports/{batch_id}/cad-preview",
            json={"skip_completed": True, "force": True, "continue_on_error": True},
        )

    assert not_generated.status_code == 404
    assert not_generated.json()["detail"]["error_code"] == "CAD_PREVIEW_FILE_NOT_FOUND"
    assert first.status_code == 200
    assert first.json()["summary"]["success_count"] == 1
    assert missing.status_code == 404
    assert missing.json()["detail"]["error_code"] == "CAD_PREVIEW_FILE_MISSING"
    assert regenerated.status_code == 200
    assert "CAD_PREVIEW_FILE_MISSING_REGENERATED" in regenerated.json()["items"][0]["warnings"]
    assert skipped.json()["summary"]["skipped_count"] == 1
    assert forced.json()["summary"]["success_count"] == 1


def test_v084_dwg_converted_preview_uses_converted_file_path(tmp_path: Path):
    clear_converter_tables()
    converter = write_mock_converter(tmp_path)
    with TestClient(app) as client:
        create_converter_setting(client, converter)
        project_id = create_project(client, "v0.8.4 DWG 转 DXF 预览")
        upload = upload_files(client, project_id, [("v084.dwg", DWG_BYTES, "application/acad")])
        file_id = upload["files"][0]["id"]
        convert = client.post(f"/api/files/{file_id}/convert-dwg-to-dxf")
        prepare = client.post(f"/api/files/{file_id}/prepare-dxf-sheet")
        sheet_id = prepare.json()["sheet_id"]
        preview = client.post(f"/api/sheets/{sheet_id}/cad-preview")
        export = client.post(
            f"/api/projects/{project_id}/exports/excel",
            json={"confirm_incomplete": True, "include_issues": True, "filter": None},
        )
        with SessionLocal() as db:
            drawing_file = db.get(DrawingFile, file_id)
            assert drawing_file is not None
            converted_path = drawing_file.converted_file_path

    assert convert.status_code == 200, convert.text
    assert converted_path
    assert preview.status_code == 200, preview.text
    assert preview.json()["status"] == "success"
    assert export.status_code == 200, export.text


def test_v084_batch_preview_statistics_and_single_failure_continue():
    with TestClient(app) as client:
        project_id = create_project(client, "v0.8.4 批量预览统计")
        _file_id, _sheet_id, batch_id = prepare_dxf_sheet(client, project_id, "v084-good.dxf")
        bad_upload = upload_files(client, project_id, [("v084-bad.dxf", b"broken dxf", "application/dxf")])
        bad_file_id = bad_upload["files"][0]["id"]
        bad_prepare = client.post(f"/api/files/{bad_file_id}/prepare-dxf-sheet")
        with SessionLocal() as db:
            bad_file = db.get(DrawingFile, bad_file_id)
            bad_sheet = db.get(DrawingSheet, bad_prepare.json()["sheet_id"])
            assert bad_file and bad_sheet
            bad_file.batch_id = batch_id
            bad_sheet.batch_id = batch_id
            db.commit()
        result = client.post(
            f"/api/imports/{batch_id}/cad-preview",
            json={"skip_completed": False, "force": True, "continue_on_error": True},
        )

    assert result.status_code == 200, result.text
    data = result.json()
    assert data["summary"]["total_count"] == 2
    assert data["summary"]["success_count"] == 1
    assert data["summary"]["failed_count"] == 1
    assert data["summary"]["duration_seconds"] >= 0
    assert data["errors"][0]["file_name"] == "v084-bad.dxf"
    assert data["errors"][0]["sheet_id"] is not None
    assert data["errors"][0]["error_code"] in {"CAD_PREVIEW_DXF_OPEN_FAILED", "CAD_PREVIEW_RENDER_FAILED"}


def test_v084_pipeline_preview_failure_does_not_block_export():
    with TestClient(app) as client:
        project_id = create_project(client, "v0.8.4 pipeline 预览稳定")
        _file_id, _sheet_id, batch_id = prepare_dxf_sheet(client, project_id, "v084-pipeline.dxf")
        pipeline = client.post(
            f"/api/imports/{batch_id}/cad-pipeline",
            json={
                "steps": ["parse_dxf", "generate_candidates", "fuse_fields", "generate_cad_preview"],
                "skip_completed": True,
                "continue_on_error": True,
            },
        )
        export = client.post(
            f"/api/projects/{project_id}/exports/excel",
            json={"confirm_incomplete": True, "include_issues": True, "filter": None},
        )

    assert pipeline.status_code == 200, pipeline.text
    assert pipeline.json()["summary"]["cad_preview_success"] == 1
    assert pipeline.json()["summary"]["fusion_success"] >= 1
    assert export.status_code == 200, export.text


def test_v084_backup_restore_keeps_preview_paths_and_image_access():
    with TestClient(app) as client:
        project_id = create_project(client, "v0.8.4 预览备份恢复")
        _file_id, sheet_id, _batch_id = prepare_dxf_sheet(client, project_id, "v084-backup.dxf")
        preview = client.post(f"/api/sheets/{sheet_id}/cad-preview")
        backup = backup_project(client, project_id)
        with zipfile.ZipFile(settings.root_dir / backup["file_path"]) as archive:
            names = archive.namelist()
        restore = client.post(f"/api/backups/{backup['backup_id']}/restore", json={"restore_mode": "new_project"})
        restored_project_id = restore.json()["new_project_id"]
        restored_sheets = client.get(f"/api/projects/{restored_project_id}/sheets?page_size=100").json()["items"]
        restored_sheet = restored_sheets[0]
        image = client.get(f"/api/sheets/{restored_sheet['id']}/cad-preview-image")
        export = client.post(
            f"/api/projects/{restored_project_id}/exports/excel",
            json={"confirm_incomplete": True, "include_issues": True, "filter": None},
        )

    assert preview.status_code == 200
    assert any("files/cad/previews/" in name for name in names)
    assert restore.status_code == 200
    assert f"project_{restored_project_id}" in restored_sheet["cad_preview_path"]
    assert f"project_{project_id}" not in restored_sheet["cad_preview_path"]
    assert image.status_code == 200
    assert image.content.startswith(b"\x89PNG")
    assert export.status_code == 200


def test_v084_pdf_preview_and_portable_package_regressions():
    with TestClient(app) as client:
        project_id = create_project(client, "v0.8.4 PDF 预览回归")
        upload = upload_files(client, project_id, [("v084.pdf", make_pdf_bytes("图号 建施-084"), "application/pdf")])
        split = client.post(f"/api/files/{upload['files'][0]['id']}/split")
        sheet_id = split.json()["sheets"][0]["id"]
        pdf_preview = client.get(f"/api/sheets/{sheet_id}/preview")
        cad_preview = client.post(f"/api/sheets/{sheet_id}/cad-preview")

    summary = build_portable_package(ROOT, version=VERSION, clean=True)
    package_dir = ROOT / "release" / package_name(VERSION)
    package_info = (package_dir / "package_info.txt").read_text(encoding="utf-8")

    assert split.status_code == 200, split.text
    assert pdf_preview.status_code == 200
    assert cad_preview.status_code == 400
    assert cad_preview.json()["detail"]["error_code"] == "CAD_PREVIEW_UNSUPPORTED_FORMAT"
    assert summary.package_dir == package_dir
    assert package_dir.is_dir()
    assert VERSION in package_info
    assert "CAD 预览仅用于辅助查看" in package_info
