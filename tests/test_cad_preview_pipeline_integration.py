from fastapi.testclient import TestClient

from backend.main import app
from dwg_test_helpers import run_cad_pipeline_blocking
from test_cad_preview import prepare_dxf_sheet
from test_project_backup_restore import create_project


def test_cad_pipeline_generate_preview_step_reports_summary_counts():
    with TestClient(app) as client:
        project_id = create_project(client, "v0.8.3 pipeline CAD 预览")
        _file_id, sheet_id, batch_id = prepare_dxf_sheet(client, project_id, "pipeline-preview.dxf")

        first_data = run_cad_pipeline_blocking(
            client,
            batch_id,
            {
                "steps": ["generate_cad_preview"],
                "skip_completed": True,
                "continue_on_error": True,
            },
        )
        second_data = run_cad_pipeline_blocking(
            client,
            batch_id,
            {
                "steps": ["generate_cad_preview"],
                "skip_completed": True,
                "continue_on_error": True,
            },
        )
        image = client.get(f"/api/sheets/{sheet_id}/cad-preview-image")

    assert first_data["summary"]["cad_preview_success"] == 1
    assert first_data["summary"]["cad_preview_failed"] == 0
    assert first_data["summary"]["cad_preview_skipped"] == 0
    assert first_data["steps"][0]["warning_count"] >= 0
    assert second_data["summary"]["cad_preview_skipped"] == 1
    assert image.status_code == 200
    assert image.content.startswith(b"\x89PNG")


def test_pipeline_preview_failure_does_not_block_excel_export():
    with TestClient(app) as client:
        project_id = create_project(client, "v0.8.3 pipeline 失败不阻断导出")
        _file_id, _sheet_id, batch_id = prepare_dxf_sheet(client, project_id, "pipeline-export.dxf")
        result = run_cad_pipeline_blocking(
            client,
            batch_id,
            {
                "steps": ["parse_dxf", "generate_candidates", "fuse_fields", "generate_cad_preview"],
                "skip_completed": True,
                "continue_on_error": True,
            },
        )
        export = client.post(
            f"/api/projects/{project_id}/exports/excel",
            json={"confirm_incomplete": True, "include_issues": True, "filter": None},
        )

    assert result["summary"]["cad_preview_success"] == 1
    assert export.status_code == 200, export.text
