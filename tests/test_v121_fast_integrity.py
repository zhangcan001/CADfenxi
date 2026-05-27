"""v1.2.1 版本、路由、接口、打包一致性快速修复测试。"""
from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient

from backend.core.config import settings
from backend.main import app
from dwg_test_helpers import (
    DWG_BYTES,
    clear_converter_tables,
    create_converter_setting,
    run_cad_pipeline_blocking,
    write_mock_converter,
)
from scripts.build_portable_package import DEFAULT_VERSION, build_portable_package, package_name
from test_full_flow_stability_v055 import make_pdf_bytes, title_block_dxf
from test_project_backup_restore import backup_project, create_project, upload_files
from test_v11_fast_ux import export_excel


VERSION = "v1.4-fast-real-project-trial"


def test_v121_version_is_unified_across_backend_frontend_and_package_script():
    frontend_package = json.loads((settings.root_dir / "frontend" / "package.json").read_text(encoding="utf-8"))
    with TestClient(app) as client:
        response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "version": VERSION, "database": "ok", "storage": "ok"}
    assert settings.version == VERSION
    assert DEFAULT_VERSION == VERSION
    assert frontend_package["version"] == VERSION


def test_v121_existing_routers_are_mounted_and_accessible():
    with TestClient(app) as client:
        project_id = create_project(client, "v1.2.1 router 挂载")
        checks = {
            "projects": client.get("/api/projects"),
            "imports": client.get(f"/api/projects/{project_id}/files"),
            "backups": client.get("/api/backups"),
            "data_health": client.get("/api/system/health-check"),
            "maintenance": client.get("/api/system/maintenance-report"),
            "tables": client.get(f"/api/projects/{project_id}/tables"),
            "block_stats": client.get(f"/api/projects/{project_id}/block-stats"),
            "consistency": client.post(f"/api/projects/{project_id}/consistency-check"),
        }

    assert all(response.status_code == 200 for response in checks.values()), {
        name: response.status_code for name, response in checks.items()
    }


def test_v121_mixed_import_summary_duplicate_unsupported_next_actions_and_workbench():
    duplicate_bytes = make_pdf_bytes("重复")
    with TestClient(app) as client:
        project_id = create_project(client, "v1.2.1 混合导入")
        first = upload_files(client, project_id, [("duplicate.pdf", duplicate_bytes, "application/pdf")])
        response = client.post(
            f"/api/projects/{project_id}/imports",
            files=[
                ("files", ("pdf-new.pdf", make_pdf_bytes("PDF"), "application/pdf")),
                ("files", ("cad-new.dxf", title_block_dxf("建施-121", "混合 DXF"), "application/dxf")),
                ("files", ("cad-new.dwg", DWG_BYTES, "application/acad")),
                ("files", ("duplicate-again.pdf", duplicate_bytes, "application/pdf")),
                ("files", ("notes.docx", b"word", "application/vnd.openxmlformats-officedocument.wordprocessingml.document")),
            ],
        )
        summary = client.get(f"/api/projects/{project_id}/workbench-summary")

    assert first["imported_count"] == 1
    assert response.status_code == 201, response.text
    data = response.json()
    assert data["total_selected"] == 5
    assert data["imported_count"] == 3
    assert data["duplicate_count"] == 1
    assert data["unsupported_count"] == 1
    assert data["file_type_counts"] == {"pdf": 2, "dxf": 1, "dwg": 1, "unsupported": 1}
    assert any(item["status"] == "duplicate" and item["warning"] == "duplicate_file" for item in data["items"])
    assert any(item["status"] == "unsupported" and item["error_code"] == "UNSUPPORTED_FILE_TYPE" for item in data["items"])
    assert data["next_actions"] == ["split_pdf", "convert_dwg", "run_cad_pipeline"]
    assert summary.status_code == 200
    assert summary.json()["drawing_file_count"] == 5
    assert summary.json()["last_import_at"] is not None


def test_v121_pdf_flow_does_not_regress():
    with TestClient(app) as client:
        project_id = create_project(client, "v1.2.1 PDF 回归")
        upload = upload_files(client, project_id, [("v121.pdf", make_pdf_bytes("图号 建施-121"), "application/pdf")])
        batch_id = upload["id"]
        file_id = upload["files"][0]["id"]
        split = client.post(f"/api/files/{file_id}/split")
        title_crops = client.post(f"/api/imports/{batch_id}/title-crops")
        extract_text = client.post(f"/api/imports/{batch_id}/extract-text")

    assert split.status_code == 200
    assert len(split.json()["sheets"]) >= 1
    assert title_crops.status_code == 200
    assert extract_text.status_code == 200


def test_v121_dxf_dwg_pipeline_preview_excel_backup_and_health_regression(tmp_path: Path):
    clear_converter_tables()
    converter = write_mock_converter(tmp_path)
    with TestClient(app) as client:
        create_converter_setting(client, converter)
        project_id = create_project(client, "v1.2.1 CAD 闭环")
        upload = upload_files(
            client,
            project_id,
            [
                ("v121-pipeline.dxf", title_block_dxf("建施-121", "DXF pipeline"), "application/dxf"),
                ("v121-pipeline.dwg", DWG_BYTES, "application/acad"),
            ],
        )
        pipeline = run_cad_pipeline_blocking(
            client,
            upload["id"],
            {
                "steps": [
                    "convert_dwg",
                    "prepare_dxf_sheet",
                    "parse_dxf",
                    "generate_candidates",
                    "fuse_fields",
                    "generate_cad_preview",
                ],
                "skip_completed": True,
                "continue_on_error": True,
            },
        )
        sheets = client.get(f"/api/projects/{project_id}/sheets?page_size=100").json()["items"]
        first_sheet_id = sheets[0]["id"]
        preview = client.post(f"/api/sheets/{first_sheet_id}/cad-preview")
        export = export_excel(client, project_id)
        backup = backup_project(client, project_id)
        project_health = client.get(f"/api/projects/{project_id}/health-check")
        system_health = client.get("/api/system/health-check")

    assert pipeline["summary"]["dwg_files"] == 1
    assert pipeline["summary"]["converted_success"] == 1
    assert pipeline["summary"]["parse_success"] >= 2
    assert len(sheets) >= 2
    assert preview.status_code == 200
    assert preview.json()["status"] in {"success", "failed"}
    assert export["ledger_row_count"] >= 1
    assert backup["backup_id"] > 0
    assert project_health.status_code == 200
    assert system_health.status_code == 200


def test_v121_portable_package_can_be_generated():
    dist = settings.root_dir / "frontend" / "dist"
    dist.mkdir(parents=True, exist_ok=True)
    (dist / "index.html").write_text("<!doctype html><html></html>", encoding="utf-8")

    summary = build_portable_package(version=VERSION, clean=True, skip_tests=True)
    package_dir = settings.root_dir / "release" / package_name(VERSION)
    package_info = summary.package_info_path.read_text(encoding="utf-8")

    assert summary.integrity_ok is True
    assert summary.package_dir == package_dir
    assert f"版本：{VERSION}" in package_info
    assert (package_dir / "frontend" / "dist" / "index.html").is_file()
