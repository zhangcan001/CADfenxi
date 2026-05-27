from datetime import UTC, datetime, timedelta
from pathlib import Path

from fastapi.testclient import TestClient

from backend.core.config import settings
from backend.core.database import SessionLocal
from backend.main import app
from backend.models.backup_record import BackupRecord
from backend.models.drawing_issue import DrawingIssue
from backend.models.drawing_sheet import DrawingSheet
from backend.models.export_record import ExportRecord
from backend.models.project import Project
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
from test_recognition_raw import _wait_for_ocr_job
from test_v11_fast_ux import add_manual_sheet, export_excel


VERSION = "v1.2.1-fast-integrity"


def test_v113_health_version():
    with TestClient(app) as client:
        response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "version": VERSION, "database": "ok", "storage": "ok"}
    assert settings.version == VERSION
    assert DEFAULT_VERSION == VERSION


def test_v113_workbench_summary_empty_project_is_safe():
    with TestClient(app) as client:
        project_id = create_project(client, "v1.1.3 空项目摘要")
        response = client.get(f"/api/projects/{project_id}/workbench-summary")

    assert response.status_code == 200
    assert response.json() == {
        "project_id": project_id,
        "drawing_file_count": 0,
        "drawing_sheet_count": 0,
        "unreviewed_count": 0,
        "low_confidence_count": 0,
        "missing_drawing_no_count": 0,
        "missing_drawing_name_count": 0,
        "open_error_count": 0,
        "open_warning_count": 0,
        "cad_preview_missing_count": 0,
        "last_import_at": None,
        "last_export_at": None,
        "last_backup_at": None,
    }


def test_v113_workbench_summary_counts_data_and_history():
    with TestClient(app) as client:
        project_id = create_project(client, "v1.1.3 有数据摘要")

    first_sheet_id = add_manual_sheet(
        project_id,
        drawing_no=None,
        drawing_name=None,
        trust_level="D",
        review_status="unreviewed",
        status="need_review",
        source_format="dxf",
        cad_preview_status="pending",
        cad_preview_path=None,
    )
    second_sheet_id = add_manual_sheet(
        project_id,
        drawing_no="建施-113",
        drawing_name="稳定包",
        trust_level="A",
        review_status="confirmed",
        status="confirmed",
        source_format="pdf",
    )
    export_time = datetime.now(UTC) - timedelta(minutes=8)
    backup_time = datetime.now(UTC) - timedelta(minutes=2)
    with SessionLocal() as db:
        first = db.get(DrawingSheet, first_sheet_id)
        second = db.get(DrawingSheet, second_sheet_id)
        assert first is not None
        assert second is not None
        db.add_all(
            [
                DrawingIssue(
                    project_id=project_id,
                    batch_id=first.batch_id,
                    file_id=first.file_id,
                    sheet_id=first.id,
                    issue_code="DRAWING_NO_EMPTY",
                    severity="error",
                    message="缺图号",
                    suggestion="补充图号",
                    status="open",
                ),
                DrawingIssue(
                    project_id=project_id,
                    batch_id=first.batch_id,
                    file_id=first.file_id,
                    sheet_id=first.id,
                    issue_code="LOW_CONFIDENCE_NEED_REVIEW",
                    severity="warning",
                    message="低可信",
                    suggestion="人工校核",
                    status="open",
                ),
                ExportRecord(
                    project_id=project_id,
                    file_path="app_data/projects/project_x/exports/v113.xlsx",
                    file_name="v113.xlsx",
                    sheet_count=2,
                    issue_count=2,
                    created_at=export_time,
                ),
                BackupRecord(
                    project_id=project_id,
                    file_name="v113.zip",
                    file_path="app_data/backups/v113.zip",
                    file_size=1,
                    status="success",
                    created_at=backup_time,
                ),
            ]
        )
        db.commit()

    with TestClient(app) as client:
        data = client.get(f"/api/projects/{project_id}/workbench-summary").json()

    assert data["drawing_sheet_count"] == 2
    assert data["unreviewed_count"] == 1
    assert data["low_confidence_count"] == 1
    assert data["missing_drawing_no_count"] == 1
    assert data["missing_drawing_name_count"] == 1
    assert data["open_error_count"] == 1
    assert data["open_warning_count"] == 1
    assert data["cad_preview_missing_count"] == 1
    assert data["last_export_at"] is not None
    assert data["last_backup_at"] is not None


def test_v113_project_list_sorting_does_not_regress():
    now = datetime.now(UTC)
    with SessionLocal() as db:
        older = Project(name="v1.1.3 older", last_opened_at=now - timedelta(days=3))
        updated = Project(name="v1.1.3 updated fallback", updated_at=now - timedelta(days=1))
        recent = Project(name="v1.1.3 recent", last_opened_at=now)
        db.add_all([older, updated, recent])
        db.commit()

    with TestClient(app) as client:
        names = [item["name"] for item in client.get("/api/projects").json()]

    assert names.index("v1.1.3 recent") < names.index("v1.1.3 older")
    assert names.index("v1.1.3 recent") < names.index("v1.1.3 updated fallback")


def test_v113_pdf_flow_review_export_regression():
    with TestClient(app) as client:
        project_id = create_project(client, "v1.1.3 PDF 流程")
        upload = upload_files(client, project_id, [("v113.pdf", make_pdf_bytes("图号 建施-113"), "application/pdf")])
        batch_id = upload["id"]
        file_id = upload["files"][0]["id"]
        split = client.post(f"/api/files/{file_id}/split")
        sheet_id = split.json()["sheets"][0]["id"]
        assert client.post(f"/api/imports/{batch_id}/title-crops").status_code == 200
        assert client.post(f"/api/imports/{batch_id}/extract-text").status_code == 200
        assert client.post(f"/api/imports/{batch_id}/ocr-titles").status_code == 200
        _wait_for_ocr_job(client, batch_id)
        assert client.post(f"/api/sheets/{sheet_id}/generate-candidates").status_code == 200
        assert client.post(f"/api/sheets/{sheet_id}/fuse-fields").status_code == 200
        update = client.patch(
            f"/api/sheets/{sheet_id}/fields",
            json={"fields": {"drawing_no": "人工-PDF-113", "drawing_name": "PDF 稳定回归", "discipline": "建筑"}},
        )
        confirm = client.post(f"/api/sheets/{sheet_id}/confirm", json={"force": True, "note": "v1.1.3"})
        export = export_excel(client, project_id)

    assert split.status_code == 200
    assert update.status_code == 200
    assert confirm.status_code == 200
    assert export["ledger_row_count"] == 1


def test_v113_dxf_preview_export_backup_and_health_regression():
    with TestClient(app) as client:
        project_id = create_project(client, "v1.1.3 DXF 回归")
        upload = upload_files(client, project_id, [("v113.dxf", title_block_dxf("建施-113", "v1.1.3 DXF"), "application/dxf")])
        file_id = upload["files"][0]["id"]
        parse = client.post(f"/api/files/{file_id}/parse-dxf")
        sheet_id = parse.json()["sheet_id"]
        preview = client.post(f"/api/sheets/{sheet_id}/cad-preview")
        assert client.post(f"/api/sheets/{sheet_id}/generate-candidates").status_code == 200
        assert client.post(f"/api/sheets/{sheet_id}/fuse-fields").status_code == 200
        export = export_excel(client, project_id)
        backup = backup_project(client, project_id)
        health = client.get(f"/api/projects/{project_id}/health-check")

    assert parse.status_code == 200
    assert preview.status_code == 200
    assert preview.json()["status"] in {"success", "failed"}
    assert export["ledger_row_count"] == 1
    assert backup["backup_id"] > 0
    assert health.status_code == 200


def test_v113_dwg_mock_conversion_cad_pipeline_restore_and_data_health(tmp_path):
    clear_converter_tables()
    converter = write_mock_converter(tmp_path)
    with TestClient(app) as client:
        create_converter_setting(client, converter)
        project_id = create_project(client, "v1.1.3 DWG mock pipeline")
        upload = upload_files(
            client,
            project_id,
            [
                ("v113.dwg", DWG_BYTES, "application/acad"),
                ("v113-pipe.dxf", title_block_dxf("建施-114", "v1.1.3 pipeline"), "application/dxf"),
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
        repeat = run_cad_pipeline_blocking(
            client,
            upload["id"],
            {
                "steps": ["generate_candidates", "fuse_fields", "generate_cad_preview"],
                "skip_completed": True,
                "continue_on_error": True,
            },
        )
        sheets = client.get(f"/api/projects/{project_id}/sheets?page_size=100").json()["items"]
        export = export_excel(client, project_id)
        backup = backup_project(client, project_id)
        restore = client.post(f"/api/backups/{backup['backup_id']}/restore", json={"restore_mode": "new_project"})
        system_health = client.get("/api/system/health-check")
        project_health = client.get(f"/api/projects/{project_id}/health-check")
        cleanup = client.post("/api/system/cleanup-temp")

    assert pipeline["summary"]["dwg_files"] == 1
    assert pipeline["summary"]["converted_success"] == 1
    assert pipeline["summary"]["parse_success"] == 2
    assert repeat["summary"]["skipped_count"] >= 0
    assert len(sheets) == 2
    assert export["ledger_row_count"] == 2
    assert restore.status_code == 200
    assert restore.json()["new_project_id"] != project_id
    assert system_health.status_code == 200
    assert project_health.status_code == 200
    assert cleanup.status_code == 200


def test_v113_portable_package_can_be_generated():
    root = Path(__file__).resolve().parents[1]
    summary = build_portable_package(root, version=VERSION, clean=True)
    package_dir = summary.package_dir

    assert package_dir == root / "release" / package_name(VERSION)
    assert summary.integrity_ok is True
    for relative in [
        "backend",
        "recognizer",
        "frontend/dist",
        "scripts",
        "app_data",
        "docs",
        "requirements.txt",
        "README.md",
        "README_本地使用说明.md",
        "RELEASE_NOTES.md",
        "package_info.txt",
        "start.bat",
        "stop.bat",
        "check_env.bat",
    ]:
        assert (package_dir / relative).exists()

    forbidden_parts = {".git", "node_modules", "__pycache__"}
    for path in package_dir.rglob("*"):
        parts = set(path.relative_to(package_dir).parts)
        assert not (parts & forbidden_parts)
        assert path.name not in {".env", ".env.local"}
        assert path.suffix not in {".pyc", ".pyo", ".log", ".tmp", ".bak", ".map"}

    package_info = (package_dir / "package_info.txt").read_text(encoding="utf-8")
    assert VERSION in package_info

