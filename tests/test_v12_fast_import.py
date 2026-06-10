from pathlib import Path

import pytest
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
from scripts.build_portable_package import DEFAULT_VERSION
from test_full_flow_stability_v055 import make_pdf_bytes, title_block_dxf
from test_project_backup_restore import backup_project, create_project, upload_files
from test_v11_fast_ux import export_excel


VERSION = "v1.5.1-fast-delivery-package-fix"


@pytest.mark.parametrize(
    ("filename", "content", "mime_type", "source_format", "next_action"),
    [
        ("v12.pdf", make_pdf_bytes("图号 建施-120"), "application/pdf", "pdf", "split_pdf"),
        ("v12.dxf", title_block_dxf("建施-121", "DXF 导入"), "application/dxf", "dxf", "run_cad_pipeline"),
        ("v12.dwg", DWG_BYTES, "application/acad", "dwg", "convert_dwg"),
    ],
)
def test_v12_single_file_import_result_has_type_counts(
    filename: str,
    content: bytes,
    mime_type: str,
    source_format: str,
    next_action: str,
):
    with TestClient(app) as client:
        project_id = create_project(client, f"v1.2 {source_format} 导入")
        response = client.post(
            f"/api/projects/{project_id}/imports",
            files=[("files", (filename, content, mime_type))],
        )

    assert response.status_code == 201, response.text
    data = response.json()
    assert data["total_selected"] == 1
    assert data["imported_count"] == 1
    assert data["file_type_counts"][source_format] == 1
    assert data["items"][0]["file_type"] == source_format
    assert data["items"][0]["status"] == "imported"
    assert next_action in data["next_actions"]


def test_v12_health_version_and_empty_project_workbench_are_safe():
    with TestClient(app) as client:
        health = client.get("/api/health")
        project_id = create_project(client, "v1.2 空项目")
        summary = client.get(f"/api/projects/{project_id}/workbench-summary")

    assert health.status_code == 200
    assert health.json() == {"status": "ok", "version": VERSION, "database": "ok", "storage": "ok"}
    assert settings.version == VERSION
    assert DEFAULT_VERSION == VERSION
    assert summary.status_code == 200
    assert summary.json()["drawing_file_count"] == 0
    assert summary.json()["drawing_sheet_count"] == 0


def test_v12_mixed_import_duplicate_unsupported_and_workbench_refresh():
    duplicate_bytes = make_pdf_bytes("重复")
    with TestClient(app) as client:
        project_id = create_project(client, "v1.2 混合导入")
        first = upload_files(client, project_id, [("duplicate.pdf", duplicate_bytes, "application/pdf")])
        response = client.post(
            f"/api/projects/{project_id}/imports",
            files=[
                ("files", ("pdf-new.pdf", make_pdf_bytes("PDF"), "application/pdf")),
                ("files", ("cad-new.dxf", title_block_dxf("建施-122", "混合 DXF"), "application/dxf")),
                ("files", ("cad-new.dwg", DWG_BYTES, "application/acad")),
                ("files", ("duplicate-again.pdf", duplicate_bytes, "application/pdf")),
                ("files", ("notes.docx", b"word", "application/vnd.openxmlformats-officedocument.wordprocessingml.document")),
            ],
        )
        summary = client.get(f"/api/projects/{project_id}/workbench-summary")
        project = client.get(f"/api/projects/{project_id}")

    assert first["imported_count"] == 1
    assert response.status_code == 201, response.text
    data = response.json()
    assert data["total_selected"] == 5
    assert data["imported_count"] == 3
    assert data["duplicate_count"] == 1
    assert data["unsupported_count"] == 1
    assert data["failed_count"] == 0
    assert data["file_type_counts"] == {"pdf": 2, "dxf": 1, "dwg": 1, "unsupported": 1}
    assert any(item["status"] == "duplicate" and item["warning"] == "duplicate_file" for item in data["items"])
    assert any(item["status"] == "unsupported" and item["error_code"] == "UNSUPPORTED_FILE_TYPE" for item in data["items"])
    assert data["next_actions"] == ["split_pdf", "convert_dwg", "run_cad_pipeline"]
    assert summary.json()["drawing_file_count"] == 5
    assert summary.json()["last_import_at"] is not None
    assert project.json()["stats"]["file_count"] == 5


def test_v12_pdf_import_flow_does_not_regress():
    with TestClient(app) as client:
        project_id = create_project(client, "v1.2 PDF 流程")
        upload = upload_files(client, project_id, [("v12-flow.pdf", make_pdf_bytes("图号 建施-123"), "application/pdf")])
        batch_id = upload["id"]
        file_id = upload["files"][0]["id"]
        split = client.post(f"/api/files/{file_id}/split")
        title_crops = client.post(f"/api/imports/{batch_id}/title-crops")
        extract_text = client.post(f"/api/imports/{batch_id}/extract-text")

    assert split.status_code == 200
    assert len(split.json()["sheets"]) >= 1
    assert title_crops.status_code == 200
    assert extract_text.status_code == 200


def test_v12_cad_pipeline_preview_review_excel_backup_and_health_do_not_regress(tmp_path: Path):
    clear_converter_tables()
    converter = write_mock_converter(tmp_path)
    with TestClient(app) as client:
        create_converter_setting(client, converter)
        project_id = create_project(client, "v1.2 CAD 闭环")
        upload = upload_files(
            client,
            project_id,
            [
                ("v12-pipeline.dxf", title_block_dxf("建施-124", "DXF pipeline"), "application/dxf"),
                ("v12-pipeline.dwg", DWG_BYTES, "application/acad"),
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
        update = client.patch(
            f"/api/sheets/{first_sheet_id}/fields",
            json={"fields": {"drawing_no": "人工-v12", "drawing_name": "导入体验", "discipline": "建筑"}},
        )
        confirm = client.post(f"/api/sheets/{first_sheet_id}/confirm", json={"force": True, "note": "v1.2"})
        export = export_excel(client, project_id)
        backup = backup_project(client, project_id)
        project_health = client.get(f"/api/projects/{project_id}/health-check")
        system_health = client.get("/api/system/health-check")

    assert pipeline["summary"]["dwg_files"] == 1
    assert pipeline["summary"]["converted_success"] == 1
    assert pipeline["summary"]["parse_success"] >= 2
    assert pipeline["summary"]["candidate_success"] >= 1
    assert len(sheets) >= 2
    assert update.status_code == 200
    assert confirm.status_code == 200
    assert export["ledger_row_count"] >= 1
    assert backup["backup_id"] > 0
    assert project_health.status_code == 200
    assert system_health.status_code == 200
