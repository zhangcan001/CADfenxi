from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import select

from backend.core.config import settings
from backend.core.database import SessionLocal
from backend.main import app
from backend.models.backup_record import BackupRecord
from backend.models.drawing_file import DrawingFile
from backend.models.drawing_issue import DrawingIssue
from backend.models.drawing_sheet import DrawingSheet
from backend.models.export_record import ExportRecord
from backend.models.import_batch import ImportBatch
from backend.models.project import Project
from scripts.build_portable_package import DEFAULT_VERSION


VERSION = "v1.2.2-fast-import-fix"
ROOT = Path(__file__).resolve().parents[1]


def create_manual_project(name: str = "v0.9.1 健康检查项目") -> tuple[int, int, int, Path]:
    with SessionLocal() as db:
        project = Project(name=name)
        db.add(project)
        db.flush()
        batch = ImportBatch(project_id=project.id, batch_name="manual", file_count=1)
        db.add(batch)
        db.flush()
        project_dir = settings.projects_dir / f"project_{project.id}"
        originals_dir = project_dir / "originals"
        previews_dir = project_dir / "previews"
        originals_dir.mkdir(parents=True, exist_ok=True)
        previews_dir.mkdir(parents=True, exist_ok=True)
        original_path = originals_dir / "健康 检查.dwg"
        original_path.write_bytes(b"DWG")
        drawing_file = DrawingFile(
            project_id=project.id,
            batch_id=batch.id,
            original_name="健康 检查.dwg",
            file_ext=".dwg",
            source_format="dwg",
            file_size=3,
            file_hash="h091",
            storage_path=original_path.relative_to(settings.root_dir).as_posix(),
            status="imported",
            convert_status="success",
            converted_format="dxf",
            converted_file_path=f"app_data/projects/project_{project.id}/cad/converted/missing.dxf",
        )
        db.add(drawing_file)
        db.flush()
        preview_path = previews_dir / "sheet preview.png"
        preview_path.write_bytes(b"preview")
        sheet = DrawingSheet(
            project_id=project.id,
            batch_id=batch.id,
            file_id=drawing_file.id,
            page_no=1,
            status="need_review",
            review_status="pending",
            trust_level="C",
            preview_path=str(preview_path.relative_to(settings.root_dir)).replace("/", "\\"),
        )
        db.add(sheet)
        db.commit()
        return project.id, drawing_file.id, sheet.id, preview_path


def test_v091_health_version_and_release_materials():
    with TestClient(app) as client:
        health = client.get("/api/health")

    assert health.status_code == 200
    assert health.json() == {"status": "ok", "version": VERSION, "database": "ok", "storage": "ok"}
    assert settings.version == VERSION
    assert DEFAULT_VERSION == VERSION
    assert (ROOT / "samples" / "data_health_real_v0_9_1" / "README.md").is_file()
    assert (ROOT / "docs" / "DATA_HEALTH_REAL_PROJECT_REPORT_v0.9.1.md").is_file()
    assert (ROOT / "docs" / "RELEASE_CHECKLIST_v1.0-local-stable.md").is_file()


def test_grouped_summary_and_info_level_are_returned():
    temp_file = settings.temp_dir / "v091_info.tmp"
    temp_file.parent.mkdir(parents=True, exist_ok=True)
    temp_file.write_text("temp", encoding="utf-8")

    with TestClient(app) as client:
        response = client.get("/api/system/health-check")

    assert response.status_code == 200, response.text
    data = response.json()
    assert "grouped_summary" in data
    assert "temp" in data["grouped_summary"]
    assert data["summary"]["info_count"] >= 1
    assert any(item["status"] == "info" and item["error_code"] == "TEMP_CLEANUP_FILES_FOUND" for item in data["items"])


def test_missing_successful_converted_dxf_is_error_but_export_and_backup_are_warning():
    project_id, _file_id, _sheet_id, _preview = create_manual_project("v0.9.1 缺失文件分级")
    with SessionLocal() as db:
        db.add(
            ExportRecord(
                project_id=project_id,
                file_path=f"app_data/projects/project_{project_id}/exports/missing.xlsx",
                file_name="missing.xlsx",
                sheet_count=1,
                issue_count=0,
            )
        )
        db.add(
            BackupRecord(
                project_id=project_id,
                file_name="missing.zip",
                file_path=f"app_data/backups/v091_missing_{project_id}.zip",
                file_size=0,
                status="success",
            )
        )
        db.commit()

    with TestClient(app) as client:
        project_health = client.get(f"/api/projects/{project_id}/health-check").json()
        backup_health = client.get("/api/backups/health-check").json()
        export_health = client.get("/api/exports/health-check").json()

    converted = [item for item in project_health["items"] if item["error_code"] == "CONVERTED_DXF_MISSING"]
    assert converted and converted[0]["status"] == "error"
    backup = [item for item in backup_health["items"] if item["error_code"] == "BACKUP_FILE_MISSING"]
    export = [item for item in export_health["items"] if item["error_code"] == "EXPORT_FILE_MISSING"]
    assert backup and backup[-1]["status"] == "warning"
    assert export and export[-1]["status"] == "warning"


def test_path_normalization_prevents_referenced_file_from_becoming_orphan():
    project_id, _file_id, sheet_id, preview_path = create_manual_project("v0.9.1 路径归一化")
    with SessionLocal() as db:
        sheet = db.get(DrawingSheet, sheet_id)
        assert sheet is not None
        sheet.preview_path = str(preview_path.resolve())
        db.commit()

    with TestClient(app) as client:
        response = client.get(f"/api/projects/{project_id}/orphan-files")

    assert response.status_code == 200, response.text
    orphan_paths = [item["path"] for item in response.json()["orphan_files"]]
    assert not any(path.endswith("sheet preview.png") for path in orphan_paths)


def test_orphan_scan_ignores_readme_gitkeep_and_reports_only_unreferenced_files():
    project_id, _file_id, _sheet_id, _preview = create_manual_project("v0.9.1 孤儿文件谨慎判断")
    base = settings.projects_dir / f"project_{project_id}"
    (base / "README.md").write_text("manual note", encoding="utf-8")
    (base / ".gitkeep").write_text("", encoding="utf-8")
    orphan = base / "old_preview_leftover.tmp"
    orphan.write_text("orphan", encoding="utf-8")

    with TestClient(app) as client:
        response = client.get(f"/api/projects/{project_id}/orphan-files")

    assert response.status_code == 200, response.text
    orphan_paths = [item["path"] for item in response.json()["orphan_files"]]
    assert any(path.endswith("old_preview_leftover.tmp") for path in orphan_paths)
    assert not any(path.endswith("README.md") for path in orphan_paths)
    assert not any(path.endswith(".gitkeep") for path in orphan_paths)


def test_project_health_reports_low_confidence_unreviewed_as_info_and_open_error_as_warning():
    project_id, file_id, sheet_id, _preview = create_manual_project("v0.9.1 校核提示分级")
    with SessionLocal() as db:
        sheet = db.get(DrawingSheet, sheet_id)
        assert sheet is not None
        db.add(
            DrawingIssue(
                project_id=project_id,
                batch_id=sheet.batch_id,
                file_id=file_id,
                sheet_id=sheet_id,
                issue_code="DRAWING_NO_EMPTY",
                severity="error",
                message="缺图号",
                suggestion="补充图号",
                status="open",
            )
        )
        db.commit()

    with TestClient(app) as client:
        response = client.get(f"/api/projects/{project_id}/health-check")

    assert response.status_code == 200, response.text
    items = response.json()["items"]
    by_code = {item["error_code"]: item for item in items if item["error_code"]}
    assert by_code["LOW_CONFIDENCE_EXISTS"]["status"] == "info"
    assert by_code["UNREVIEWED_SHEETS_EXISTS"]["status"] == "info"
    assert by_code["OPEN_ERROR_EXISTS"]["status"] == "warning"

