from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy import select

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
from scripts.build_portable_package import DEFAULT_VERSION
from test_full_flow_stability_v055 import make_pdf_bytes, title_block_dxf
from test_project_backup_restore import backup_project, create_project, upload_files
from test_recognition_raw import _wait_for_ocr_job


VERSION = "v1.1.5-deep-extract"


def export_excel(client: TestClient, project_id: int) -> dict:
    response = client.post(
        f"/api/projects/{project_id}/exports/excel",
        json={"confirm_incomplete": True, "include_issues": True, "filter": None},
    )
    assert response.status_code == 200, response.text
    return response.json()


def add_manual_sheet(
    project_id: int,
    *,
    drawing_no: str | None = "建施-11",
    drawing_name: str | None = "快捷工作台",
    trust_level: str | None = "A",
    review_status: str = "confirmed",
    status: str = "confirmed",
    source_format: str = "pdf",
    cad_preview_status: str = "success",
    cad_preview_path: str | None = "app_data/projects/project_x/cad/previews/ok.png",
) -> int:
    with SessionLocal() as db:
        project = db.get(Project, project_id)
        assert project is not None
        batch = project.import_batches[0] if project.import_batches else None
        if batch is None:
            from backend.models.import_batch import ImportBatch

            batch = ImportBatch(project_id=project_id, batch_name="manual", file_count=1)
            db.add(batch)
            db.flush()
        from backend.models.drawing_file import DrawingFile

        drawing_file = DrawingFile(
            project_id=project_id,
            batch_id=batch.id,
            original_name=f"manual.{source_format}",
            file_ext=f".{source_format}",
            source_format=source_format,
            file_size=1,
            file_hash=f"hash-{project_id}-{source_format}-{datetime.now(UTC).timestamp()}",
            storage_path=f"app_data/projects/project_{project_id}/originals/manual.{source_format}",
            status="cad_parsed" if source_format in {"dxf", "dwg"} else "preprocessed",
            convert_status="success" if source_format == "dwg" else "skipped",
        )
        db.add(drawing_file)
        db.flush()
        sheet = DrawingSheet(
            project_id=project_id,
            batch_id=batch.id,
            file_id=drawing_file.id,
            page_no=1,
            drawing_no=drawing_no,
            drawing_name=drawing_name,
            trust_level=trust_level,
            review_status=review_status,
            status=status,
            cad_preview_status=cad_preview_status,
            cad_preview_path=cad_preview_path,
        )
        db.add(sheet)
        db.commit()
        return sheet.id


def test_v11_health_version_and_package_default():
    with TestClient(app) as client:
        response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "version": VERSION, "database": "ok", "storage": "ok"}
    assert settings.version == VERSION
    assert DEFAULT_VERSION == VERSION


def test_project_list_is_sorted_by_last_opened_at():
    now = datetime.now(UTC)
    with SessionLocal() as db:
        older = Project(name="v1.1 older", last_opened_at=now - timedelta(days=2))
        recent = Project(name="v1.1 recent", last_opened_at=now)
        never = Project(name="v1.1 never", updated_at=now - timedelta(days=1))
        db.add_all([older, recent, never])
        db.commit()

    with TestClient(app) as client:
        names = [item["name"] for item in client.get("/api/projects").json()]

    assert names.index("v1.1 recent") < names.index("v1.1 older")


def test_empty_project_workbench_summary_returns_zero_counts():
    with TestClient(app) as client:
        project_id = create_project(client, "v1.1 空项目摘要")
        response = client.get(f"/api/projects/{project_id}/workbench-summary")

    assert response.status_code == 200
    assert response.json() == {
        "project_id": project_id,
        "drawing_sheet_count": 0,
        "unreviewed_count": 0,
        "low_confidence_count": 0,
        "missing_drawing_no_count": 0,
        "missing_drawing_name_count": 0,
        "open_error_count": 0,
        "open_warning_count": 0,
        "cad_preview_missing_count": 0,
        "last_export_at": None,
        "last_backup_at": None,
    }


def test_workbench_summary_counts_unreviewed_missing_issues_preview_and_history():
    with TestClient(app) as client:
        project_id = create_project(client, "v1.1 项目待办摘要")

    sheet_id = add_manual_sheet(
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
    with SessionLocal() as db:
        sheet = db.get(DrawingSheet, sheet_id)
        assert sheet is not None
        db.add_all(
            [
                DrawingIssue(
                    project_id=project_id,
                    batch_id=sheet.batch_id,
                    file_id=sheet.file_id,
                    sheet_id=sheet.id,
                    issue_code="DRAWING_NO_EMPTY",
                    severity="error",
                    message="缺图号",
                    suggestion="补充图号",
                    status="open",
                ),
                DrawingIssue(
                    project_id=project_id,
                    batch_id=sheet.batch_id,
                    file_id=sheet.file_id,
                    sheet_id=sheet.id,
                    issue_code="LOW_CONFIDENCE_NEED_REVIEW",
                    severity="warning",
                    message="低可信",
                    suggestion="人工校核",
                    status="open",
                ),
                ExportRecord(
                    project_id=project_id,
                    file_path="app_data/projects/project_x/exports/v11.xlsx",
                    file_name="v11.xlsx",
                    sheet_count=1,
                    issue_count=2,
                    created_at=datetime.now(UTC) - timedelta(minutes=5),
                ),
                BackupRecord(
                    project_id=project_id,
                    file_name="v11.zip",
                    file_path="app_data/backups/v11.zip",
                    file_size=1,
                    status="success",
                    created_at=datetime.now(UTC),
                ),
            ]
        )
        db.commit()

    with TestClient(app) as client:
        data = client.get(f"/api/projects/{project_id}/workbench-summary").json()

    assert data["drawing_sheet_count"] == 1
    assert data["unreviewed_count"] == 1
    assert data["low_confidence_count"] == 1
    assert data["missing_drawing_no_count"] == 1
    assert data["missing_drawing_name_count"] == 1
    assert data["open_error_count"] == 1
    assert data["open_warning_count"] == 1
    assert data["cad_preview_missing_count"] == 1
    assert data["last_export_at"] is not None
    assert data["last_backup_at"] is not None


def test_v11_pdf_flow_does_not_regress():
    with TestClient(app) as client:
        project_id = create_project(client, "v1.1 PDF 流程")
        upload = upload_files(client, project_id, [("v11.pdf", make_pdf_bytes("图号 建施-11"), "application/pdf")])
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


def test_v11_dxf_cad_preview_review_export_backup_and_health_regression():
    with TestClient(app) as client:
        project_id = create_project(client, "v1.1 DXF 快捷入口回归")
        upload = upload_files(client, project_id, [("v11.dxf", title_block_dxf("建施-11", "v1.1 DXF"), "application/dxf")])
        file_id = upload["files"][0]["id"]
        parse = client.post(f"/api/files/{file_id}/parse-dxf")
        sheet_id = parse.json()["sheet_id"]
        preview = client.post(f"/api/sheets/{sheet_id}/cad-preview")
        assert client.post(f"/api/sheets/{sheet_id}/generate-candidates").status_code == 200
        assert client.post(f"/api/sheets/{sheet_id}/fuse-fields").status_code == 200
        update = client.patch(
            f"/api/sheets/{sheet_id}/fields",
            json={"fields": {"drawing_no": "人工-V11", "drawing_name": "快捷台账", "discipline": "建筑"}},
        )
        confirm = client.post(f"/api/sheets/{sheet_id}/confirm", json={"force": True, "note": "v1.1"})
        export = export_excel(client, project_id)
        backup = backup_project(client, project_id)
        health = client.get(f"/api/projects/{project_id}/health-check")
        summary = client.get(f"/api/projects/{project_id}/workbench-summary")

    assert parse.status_code == 200
    assert preview.status_code == 200
    assert preview.json()["status"] in {"success", "failed"}
    assert update.status_code == 200
    assert confirm.status_code == 200
    assert export["ledger_row_count"] == 1
    assert backup["backup_id"] > 0
    assert health.status_code == 200
    assert summary.json()["last_export_at"] is not None
    assert summary.json()["last_backup_at"] is not None


def test_v11_dwg_mock_conversion_and_cad_pipeline_do_not_regress(tmp_path):
    clear_converter_tables()
    converter = write_mock_converter(tmp_path)
    with TestClient(app) as client:
        create_converter_setting(client, converter)
        project_id = create_project(client, "v1.1 DWG mock pipeline")
        upload = upload_files(
            client,
            project_id,
            [
                ("v11.dwg", DWG_BYTES, "application/acad"),
                ("v11-pipe.dxf", title_block_dxf("建施-12", "v1.1 pipeline"), "application/dxf"),
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
