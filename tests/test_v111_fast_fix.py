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


VERSION = "v1.2.2-fast-import-fix"


def test_v111_health_version_and_package_default():
    with TestClient(app) as client:
        response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "version": VERSION, "database": "ok", "storage": "ok"}
    assert settings.version == VERSION
    assert DEFAULT_VERSION == VERSION


def test_v111_empty_project_workbench_summary_is_safe():
    with TestClient(app) as client:
        project_id = create_project(client, "v1.1.1 空项目摘要")
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


def test_v111_workbench_summary_matches_database_counts_and_deduplicates_issue_sheets():
    with TestClient(app) as client:
        project_id = create_project(client, "v1.1.1 项目待办真实统计")

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
        drawing_no="建施-111",
        drawing_name="已确认图纸",
        trust_level="A",
        review_status="confirmed",
        status="confirmed",
        source_format="pdf",
    )
    export_time = datetime.now(UTC) - timedelta(minutes=10)
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
                    issue_code="DRAWING_NAME_EMPTY",
                    severity="error",
                    message="缺图名",
                    suggestion="补充图名",
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
                DrawingIssue(
                    project_id=project_id,
                    batch_id=second.batch_id,
                    file_id=second.file_id,
                    sheet_id=second.id,
                    issue_code="REVIEW_NOTICE",
                    severity="warning",
                    message="提示",
                    suggestion="查看",
                    status="open",
                ),
                ExportRecord(
                    project_id=project_id,
                    file_path="app_data/projects/project_x/exports/v111.xlsx",
                    file_name="v111.xlsx",
                    sheet_count=2,
                    issue_count=4,
                    created_at=export_time,
                ),
                BackupRecord(
                    project_id=project_id,
                    file_name="v111.zip",
                    file_path="app_data/backups/v111.zip",
                    file_size=1,
                    status="success",
                    created_at=backup_time,
                ),
            ]
        )
        db.commit()

    with TestClient(app) as client:
        data = client.get(f"/api/projects/{project_id}/workbench-summary").json()
        missing_no_total = client.get(
            f"/api/projects/{project_id}/sheets",
            params={"missing_field": "drawing_no", "page_size": 100},
        ).json()["total"]
        missing_name_total = client.get(
            f"/api/projects/{project_id}/sheets",
            params={"missing_field": "drawing_name", "page_size": 100},
        ).json()["total"]
        unreviewed_total = client.get(
            f"/api/projects/{project_id}/sheets",
            params={"review_status": "unreviewed", "page_size": 100},
        ).json()["total"]
        error_total = client.get(
            f"/api/projects/{project_id}/sheets",
            params={"has_error": True, "page_size": 100},
        ).json()["total"]
        warning_total = client.get(
            f"/api/projects/{project_id}/sheets",
            params={"has_warning": True, "page_size": 100},
        ).json()["total"]

    assert data["drawing_sheet_count"] == 2
    assert data["unreviewed_count"] == unreviewed_total == 1
    assert data["low_confidence_count"] == 1
    assert data["missing_drawing_no_count"] == missing_no_total == 1
    assert data["missing_drawing_name_count"] == missing_name_total == 1
    assert data["open_error_count"] == error_total == 1
    assert data["open_warning_count"] == warning_total == 2
    assert data["cad_preview_missing_count"] == 1
    assert data["last_export_at"] is not None
    assert data["last_backup_at"] is not None


def test_v111_project_list_recent_opened_sort_does_not_regress():
    now = datetime.now(UTC)
    with SessionLocal() as db:
        older = Project(name="v1.1.1 older", last_opened_at=now - timedelta(days=3))
        updated = Project(name="v1.1.1 updated fallback", updated_at=now - timedelta(days=1))
        recent = Project(name="v1.1.1 recent", last_opened_at=now)
        db.add_all([older, updated, recent])
        db.commit()

    with TestClient(app) as client:
        names = [item["name"] for item in client.get("/api/projects").json()]

    assert names.index("v1.1.1 recent") < names.index("v1.1.1 older")
    assert names.index("v1.1.1 recent") < names.index("v1.1.1 updated fallback")


def test_v111_pdf_flow_does_not_regress():
    with TestClient(app) as client:
        project_id = create_project(client, "v1.1.1 PDF 流程")
        upload = upload_files(client, project_id, [("v111.pdf", make_pdf_bytes("图号 建施-111"), "application/pdf")])
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
        export = export_excel(client, project_id)

    assert split.status_code == 200
    assert export["ledger_row_count"] == 1


def test_v111_dxf_preview_review_export_backup_and_health_regression():
    with TestClient(app) as client:
        project_id = create_project(client, "v1.1.1 DXF 回归")
        upload = upload_files(client, project_id, [("v111.dxf", title_block_dxf("建施-111", "v1.1.1 DXF"), "application/dxf")])
        file_id = upload["files"][0]["id"]
        parse = client.post(f"/api/files/{file_id}/parse-dxf")
        sheet_id = parse.json()["sheet_id"]
        preview = client.post(f"/api/sheets/{sheet_id}/cad-preview")
        assert client.post(f"/api/sheets/{sheet_id}/generate-candidates").status_code == 200
        assert client.post(f"/api/sheets/{sheet_id}/fuse-fields").status_code == 200
        update = client.patch(
            f"/api/sheets/{sheet_id}/fields",
            json={"fields": {"drawing_no": "人工-V111", "drawing_name": "快捷修复", "discipline": "建筑"}},
        )
        confirm = client.post(f"/api/sheets/{sheet_id}/confirm", json={"force": True, "note": "v1.1.1"})
        export = export_excel(client, project_id)
        backup = backup_project(client, project_id)
        health = client.get(f"/api/projects/{project_id}/health-check")

    assert parse.status_code == 200
    assert preview.status_code == 200
    assert preview.json()["status"] in {"success", "failed"}
    assert update.status_code == 200
    assert confirm.status_code == 200
    assert export["ledger_row_count"] == 1
    assert backup["backup_id"] > 0
    assert health.status_code == 200


def test_v111_dwg_mock_conversion_and_cad_pipeline_do_not_regress(tmp_path):
    clear_converter_tables()
    converter = write_mock_converter(tmp_path)
    with TestClient(app) as client:
        create_converter_setting(client, converter)
        project_id = create_project(client, "v1.1.1 DWG mock pipeline")
        upload = upload_files(
            client,
            project_id,
            [
                ("v111.dwg", DWG_BYTES, "application/acad"),
                ("v111-pipe.dxf", title_block_dxf("建施-112", "v1.1.1 pipeline"), "application/dxf"),
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
        export = export_excel(client, project_id)
        system_health = client.get("/api/system/health-check")

    assert pipeline["summary"]["dwg_files"] == 1
    assert pipeline["summary"]["converted_success"] == 1
    assert pipeline["summary"]["parse_success"] == 2
    assert len(sheets) == 2
    assert export["ledger_row_count"] == 2
    assert system_health.status_code == 200


def test_v111_portable_package_can_be_generated_and_is_clean():
    root = Path(__file__).resolve().parents[1]
    summary = build_portable_package(root, version=VERSION, clean=True)
    package_dir = summary.package_dir

    assert package_dir == root / "release" / package_name(VERSION)
    assert summary.integrity_ok is True
    for relative in [
        "frontend/dist/index.html",
        "backend/main.py",
        "scripts/local_launcher.py",
        "app_data/projects",
        "app_data/backups",
        "app_data/database",
        "app_data/logs",
        "app_data/temp",
        "README.md",
        "README_本地使用说明.md",
        "RELEASE_NOTES.md",
        "package_info.txt",
        "start.bat",
        "check_env.bat",
        "stop.bat",
    ]:
        assert (package_dir / relative).exists()

    forbidden_parts = {".git", "__pycache__", "node_modules"}
    for path in package_dir.rglob("*"):
        parts = set(path.relative_to(package_dir).parts)
        assert not (parts & forbidden_parts)
        assert path.name not in {".env", ".env.local"}
        assert path.suffix not in {".pyc", ".pyo", ".log", ".tmp", ".bak", ".map"}

    assert [p.name for p in (package_dir / "app_data" / "projects").iterdir()] == [".gitkeep"]
    assert [p.name for p in (package_dir / "app_data" / "database").iterdir()] == [".gitkeep"]
    package_info = (package_dir / "package_info.txt").read_text(encoding="utf-8")
    assert VERSION in package_info

