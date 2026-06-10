from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import select

from backend.core.config import settings
from backend.core.database import SessionLocal
from backend.main import app
from backend.models.backup_record import BackupRecord
from backend.models.drawing_file import DrawingFile
from backend.models.drawing_sheet import DrawingSheet
from backend.models.export_record import ExportRecord
from backend.models.project import Project
from scripts.build_portable_package import DEFAULT_VERSION
from test_project_backup_restore import create_project, upload_files


VERSION = "v1.5.1-fast-delivery-package-fix"
ROOT = Path(__file__).resolve().parents[1]


def test_v09_health_version_and_docs():
    with TestClient(app) as client:
        health = client.get("/api/health")

    assert health.status_code == 200
    assert health.json() == {"status": "ok", "version": VERSION, "database": "ok", "storage": "ok"}
    assert settings.version == VERSION
    assert DEFAULT_VERSION == VERSION
    assert (ROOT / "docs" / "DATA_HEALTH_MAINTENANCE_GUIDE_v0.9.md").is_file()
    assert (ROOT / "docs" / "DATA_HEALTH_CHECK_REPORT_v0.9.md").is_file()


def test_system_health_check_and_data_safety_summary_return_structured_result():
    with TestClient(app) as client:
        health = client.get("/api/system/health-check")
        summary = client.get("/api/system/data-safety-summary")
        report = client.get("/api/system/maintenance-report")

    assert health.status_code == 200, health.text
    assert health.json()["status"] in {"ok", "info", "warning", "error"}
    assert "summary" in health.json()
    assert "grouped_summary" in health.json()
    assert "items" in health.json()
    assert summary.status_code == 200
    assert summary.json()["app_data_writable"] is True
    assert report.status_code == 200
    assert "数据健康检查报告" in report.json()["report_markdown"]


def test_project_health_detects_missing_drawing_preview_cad_preview_and_cad_json(tmp_path: Path):
    with TestClient(app) as client:
        project_id = create_project(client, "v0.9 项目健康检查")
        upload = upload_files(client, project_id, [("health.dxf", b"0\nSECTION\n2\nEOF\n0\nEOF\n", "application/dxf")])
        file_id = upload["files"][0]["id"]

        with SessionLocal() as db:
            drawing_file = db.get(DrawingFile, file_id)
            assert drawing_file is not None
            sheet = DrawingSheet(
                project_id=project_id,
                batch_id=drawing_file.batch_id,
                file_id=file_id,
                page_no=1,
                status="cad_parsed",
                preview_path=f"app_data/projects/project_{project_id}/previews/missing.png",
                cad_preview_path=f"app_data/projects/project_{project_id}/cad/previews/missing.png",
            )
            db.add(sheet)
            db.commit()

        response = client.get(f"/api/projects/{project_id}/health-check")

    assert response.status_code == 200, response.text
    data = response.json()
    error_codes = {item["error_code"] for item in data["items"] if item["error_code"]}
    assert data["status"] in {"warning", "error"}
    assert "SHEET_PREVIEW_MISSING" in error_codes
    assert "CAD_PREVIEW_MISSING" in error_codes
    assert "CAD_JSON_MISSING" in error_codes


def test_project_health_detects_missing_original_file_and_orphan_file():
    with TestClient(app) as client:
        project_id = create_project(client, "v0.9 缺失原图与孤儿文件")
        upload = upload_files(client, project_id, [("missing.pdf", b"%PDF-1.4\n%%EOF", "application/pdf")])
        file_id = upload["files"][0]["id"]

        with SessionLocal() as db:
            drawing_file = db.get(DrawingFile, file_id)
            assert drawing_file is not None
            original = settings.root_dir / drawing_file.storage_path
            original.unlink()
            orphan = settings.projects_dir / f"project_{project_id}" / "manual_orphan.tmp"
            orphan.write_text("orphan", encoding="utf-8")
            db.commit()

        response = client.get(f"/api/projects/{project_id}/health-check")
        orphan_scan = client.get(f"/api/projects/{project_id}/orphan-files")

    assert response.status_code == 200, response.text
    data = response.json()
    error_codes = {item["error_code"] for item in data["items"] if item["error_code"]}
    assert data["status"] == "error"
    assert "DRAWING_FILE_MISSING" in error_codes
    assert data["summary"]["orphan_file_count"] >= 1
    assert orphan_scan.status_code == 200
    assert any(item["path"].endswith("manual_orphan.tmp") for item in orphan_scan.json()["orphan_files"])


def test_backup_and_export_record_checks_detect_missing_files():
    with SessionLocal() as db:
        project = Project(name="v0.9 备份导出健康检查")
        db.add(project)
        db.flush()
        project_id = project.id
        backup = BackupRecord(
            project_id=project_id,
            file_name="missing.zip",
            file_path=f"app_data/backups/missing_{project_id}.zip",
            file_size=0,
            status="success",
        )
        export = ExportRecord(
            project_id=project_id,
            file_path=f"app_data/projects/project_{project_id}/exports/missing.xlsx",
            file_name="missing.xlsx",
            sheet_count=0,
            issue_count=0,
        )
        db.add_all([backup, export])
        db.commit()

    with TestClient(app) as client:
        backups = client.get("/api/backups/health-check")
        exports = client.get("/api/exports/health-check")

    assert backups.status_code == 200, backups.text
    assert exports.status_code == 200, exports.text
    assert any(item["error_code"] == "BACKUP_FILE_MISSING" for item in backups.json()["items"])
    assert any(item["error_code"] == "EXPORT_FILE_MISSING" for item in exports.json()["items"])


def test_cleanup_temp_files_only_cleans_temp_directory():
    temp_file = settings.temp_dir / "v09_cleanup.tmp"
    temp_file.parent.mkdir(parents=True, exist_ok=True)
    temp_file.write_text("temp", encoding="utf-8")

    with TestClient(app) as client:
        response = client.post("/api/system/cleanup-temp")

    assert response.status_code == 200, response.text
    assert response.json()["deleted_file_count"] >= 1
    assert response.json()["freed_bytes"] >= 4
    assert not temp_file.exists()


def test_missing_project_health_check_returns_structured_error():
    with TestClient(app) as client:
        response = client.get("/api/projects/999999999/health-check")

    assert response.status_code == 404
    assert response.json()["detail"]["error_code"] == "PROJECT_NOT_FOUND"

