"""v1.2.2 导入流程真实使用问题快速修复测试。"""
from __future__ import annotations

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
from test_full_flow_stability_v055 import make_pdf_bytes, title_block_dxf
from test_project_backup_restore import backup_project, create_project, upload_files
from test_v11_fast_ux import export_excel


VERSION = "v1.4-fast-real-project-trial"


def post_import(client: TestClient, project_id: int, files: list[tuple[str, bytes, str]]) -> dict:
    response = client.post(
        f"/api/projects/{project_id}/imports",
        files=[("files", (name, content, mime_type)) for name, content, mime_type in files],
    )
    assert response.status_code == 201, response.text
    return response.json()


def assert_actions(data: dict, expected: list[str], forbidden: list[str] | None = None) -> None:
    assert data["next_actions"] == expected
    for action in forbidden or []:
        assert action not in data["next_actions"]


def test_v122_health_version():
    with TestClient(app) as client:
        response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "version": VERSION, "database": "ok", "storage": "ok"}
    assert settings.version == VERSION


def test_v122_pdf_only_import_counts_duplicate_next_actions_and_workbench():
    pdf_bytes = make_pdf_bytes("PDF only")
    with TestClient(app) as client:
        project_id = create_project(client, "v1.2.2 PDF only")
        first = post_import(client, project_id, [("a.pdf", pdf_bytes, "application/pdf")])
        second = post_import(
            client,
            project_id,
            [
                ("b.pdf", make_pdf_bytes("PDF b"), "application/pdf"),
                ("a-again.pdf", pdf_bytes, "application/pdf"),
            ],
        )
        summary = client.get(f"/api/projects/{project_id}/workbench-summary").json()

    assert first["imported_count"] == 1
    assert second["total_selected"] == 2
    assert second["file_type_counts"] == {"pdf": 2, "dxf": 0, "dwg": 0, "unsupported": 0}
    assert second["imported_count"] == 1
    assert second["duplicate_count"] == 1
    assert_actions(second, ["split_pdf"], forbidden=["run_cad_pipeline", "convert_dwg", "parse_dxf"])
    assert summary["drawing_file_count"] == 3
    assert summary["last_import_at"] is not None


def test_v122_dxf_only_import_counts_duplicate_and_next_actions():
    dxf_bytes = title_block_dxf("建施-122", "DXF only")
    with TestClient(app) as client:
        project_id = create_project(client, "v1.2.2 DXF only")
        post_import(client, project_id, [("a.dxf", dxf_bytes, "application/dxf")])
        data = post_import(
            client,
            project_id,
            [
                ("b.dxf", title_block_dxf("建施-123", "DXF b"), "application/dxf"),
                ("a-again.dxf", dxf_bytes, "application/dxf"),
            ],
        )

    assert data["file_type_counts"] == {"pdf": 0, "dxf": 2, "dwg": 0, "unsupported": 0}
    assert data["imported_count"] == 1
    assert data["duplicate_count"] == 1
    assert_actions(data, ["run_cad_pipeline", "generate_cad_preview"])


def test_v122_dwg_only_without_converter_prompts_configuration_not_parse_dxf():
    clear_converter_tables()
    with TestClient(app) as client:
        project_id = create_project(client, "v1.2.2 DWG no converter")
        data = post_import(client, project_id, [("a.dwg", DWG_BYTES, "application/acad")])

    assert data["file_type_counts"] == {"pdf": 0, "dxf": 0, "dwg": 1, "unsupported": 0}
    assert data["warnings"] == ["dwg_converter_not_configured"]
    assert_actions(data, ["configure_dwg_converter"], forbidden=["parse_dxf", "run_cad_pipeline"])


def test_v122_dwg_only_with_converter_suggests_convert_then_pipeline(tmp_path: Path):
    clear_converter_tables()
    converter = write_mock_converter(tmp_path)
    with TestClient(app) as client:
        create_converter_setting(client, converter)
        project_id = create_project(client, "v1.2.2 DWG converter")
        data = post_import(client, project_id, [("a.dwg", DWG_BYTES, "application/acad")])

    assert_actions(data, ["convert_dwg", "run_cad_pipeline"], forbidden=["parse_dxf"])


def test_v122_pdf_dxf_mixed_import_next_actions_order():
    with TestClient(app) as client:
        project_id = create_project(client, "v1.2.2 PDF DXF")
        data = post_import(
            client,
            project_id,
            [
                ("a.pdf", make_pdf_bytes("PDF"), "application/pdf"),
                ("a.dxf", title_block_dxf("建施-124", "PDF DXF"), "application/dxf"),
            ],
        )

    assert data["file_type_counts"] == {"pdf": 1, "dxf": 1, "dwg": 0, "unsupported": 0}
    assert_actions(data, ["split_pdf", "run_cad_pipeline"], forbidden=["convert_dwg", "configure_dwg_converter"])


def test_v122_dxf_dwg_mixed_import_respects_converter_state(tmp_path: Path):
    clear_converter_tables()
    with TestClient(app) as client:
        project_id = create_project(client, "v1.2.2 DXF DWG no converter")
        no_converter = post_import(
            client,
            project_id,
            [
                ("a.dxf", title_block_dxf("建施-125", "DXF DWG"), "application/dxf"),
                ("a.dwg", DWG_BYTES, "application/acad"),
            ],
        )

    assert_actions(no_converter, ["configure_dwg_converter", "run_cad_pipeline"], forbidden=["convert_dwg"])

    clear_converter_tables()
    converter = write_mock_converter(tmp_path)
    with TestClient(app) as client:
        create_converter_setting(client, converter)
        project_id = create_project(client, "v1.2.2 DXF DWG converter")
        with_converter = post_import(
            client,
            project_id,
            [
                ("b.dxf", title_block_dxf("建施-126", "DXF DWG"), "application/dxf"),
                ("b.dwg", DWG_BYTES, "application/acad"),
            ],
        )

    assert_actions(with_converter, ["convert_dwg", "run_cad_pipeline"])


def test_v122_pdf_dxf_dwg_mixed_import_counts_unsupported_and_next_actions(tmp_path: Path):
    clear_converter_tables()
    converter = write_mock_converter(tmp_path)
    with TestClient(app) as client:
        create_converter_setting(client, converter)
        project_id = create_project(client, "v1.2.2 full mixed")
        data = post_import(
            client,
            project_id,
            [
                ("a.pdf", make_pdf_bytes("PDF"), "application/pdf"),
                ("a.dxf", title_block_dxf("建施-127", "Full mixed"), "application/dxf"),
                ("a.dwg", DWG_BYTES, "application/acad"),
                ("photo.jpg", b"jpg", "image/jpeg"),
                ("note.docx", b"docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"),
                ("table.xlsx", b"xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"),
                ("archive.zip", b"zip", "application/zip"),
            ],
        )

    assert data["total_selected"] == 7
    assert data["imported_count"] == 3
    assert data["unsupported_count"] == 4
    assert data["file_type_counts"] == {"pdf": 1, "dxf": 1, "dwg": 1, "unsupported": 4}
    assert_actions(data, ["split_pdf", "convert_dwg", "run_cad_pipeline"])
    assert "unsupported_files_rejected" in data["warnings"]
    unsupported_items = [item for item in data["items"] if item["status"] == "unsupported"]
    assert {item["file_name"] for item in unsupported_items} == {"photo.jpg", "note.docx", "table.xlsx", "archive.zip"}
    assert all(item["error_code"] == "UNSUPPORTED_FILE_TYPE" and item["message"] for item in unsupported_items)


def test_v122_import_errors_for_missing_project_and_empty_file():
    with TestClient(app) as client:
        missing = client.post(
            "/api/projects/999999/imports",
            files=[("files", ("missing.pdf", make_pdf_bytes("missing"), "application/pdf"))],
        )
        project_id = create_project(client, "v1.2.2 empty")
        empty = client.post(
            f"/api/projects/{project_id}/imports",
            files=[("files", ("empty.pdf", b"", "application/pdf"))],
        )

    assert missing.status_code == 404
    assert missing.json()["detail"]["error_code"] == "PROJECT_NOT_FOUND"
    assert empty.status_code == 201
    item = empty.json()["items"][0]
    assert item["status"] == "failed"
    assert item["error_code"] == "EMPTY_FILE"
    assert item["message"]


def test_v122_pdf_flow_does_not_regress():
    with TestClient(app) as client:
        project_id = create_project(client, "v1.2.2 PDF 回归")
        upload = upload_files(client, project_id, [("v122.pdf", make_pdf_bytes("图号 建施-122"), "application/pdf")])
        batch_id = upload["id"]
        file_id = upload["files"][0]["id"]
        split = client.post(f"/api/files/{file_id}/split")
        title_crops = client.post(f"/api/imports/{batch_id}/title-crops")
        extract_text = client.post(f"/api/imports/{batch_id}/extract-text")

    assert split.status_code == 200
    assert len(split.json()["sheets"]) >= 1
    assert title_crops.status_code == 200
    assert extract_text.status_code == 200


def test_v122_dxf_dwg_pipeline_preview_review_excel_backup_and_health_regression(tmp_path: Path):
    clear_converter_tables()
    converter = write_mock_converter(tmp_path)
    with TestClient(app) as client:
        create_converter_setting(client, converter)
        project_id = create_project(client, "v1.2.2 CAD 闭环")
        upload = upload_files(
            client,
            project_id,
            [
                ("v122-pipeline.dxf", title_block_dxf("建施-128", "DXF pipeline"), "application/dxf"),
                ("v122-pipeline.dwg", DWG_BYTES, "application/acad"),
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
            json={"fields": {"drawing_no": "人工-v122", "drawing_name": "导入修复", "discipline": "建筑"}},
        )
        confirm = client.post(f"/api/sheets/{first_sheet_id}/confirm", json={"force": True, "note": "v1.2.2"})
        preview = client.post(f"/api/sheets/{first_sheet_id}/cad-preview")
        export = export_excel(client, project_id)
        backup = backup_project(client, project_id)
        project_health = client.get(f"/api/projects/{project_id}/health-check")
        system_health = client.get("/api/system/health-check")

    assert pipeline["summary"]["dwg_files"] == 1
    assert pipeline["summary"]["converted_success"] == 1
    assert pipeline["summary"]["parse_success"] >= 2
    assert len(sheets) >= 2
    assert update.status_code == 200
    assert confirm.status_code == 200
    assert preview.status_code == 200
    assert export["ledger_row_count"] >= 1
    assert backup["backup_id"] > 0
    assert project_health.status_code == 200
    assert system_health.status_code == 200
