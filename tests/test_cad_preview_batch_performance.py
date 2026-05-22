from backend.core.config import settings
from backend.core.database import SessionLocal
from backend.main import app
from backend.models.drawing_file import DrawingFile
from backend.models.drawing_sheet import DrawingSheet
from fastapi.testclient import TestClient
from test_cad_preview import prepare_dxf_sheet
from test_project_backup_restore import create_project, upload_files


def create_bad_dxf_sheet(client: TestClient, project_id: int, batch_id: int) -> int:
    upload = upload_files(client, project_id, [("bad-preview.dxf", b"broken dxf", "application/dxf")])
    file_id = upload["files"][0]["id"]
    prepare = client.post(f"/api/files/{file_id}/prepare-dxf-sheet")
    assert prepare.status_code == 200, prepare.text
    sheet_id = prepare.json()["sheet_id"]
    with SessionLocal() as db:
        drawing_file = db.get(DrawingFile, file_id)
        sheet = db.get(DrawingSheet, sheet_id)
        assert drawing_file is not None
        assert sheet is not None
        drawing_file.batch_id = batch_id
        sheet.batch_id = batch_id
        db.commit()
    return sheet_id


def test_project_and_batch_cad_preview_summary_skip_force_and_missing_cache():
    with TestClient(app) as client:
        project_id = create_project(client, "v0.8.3 CAD 批量预览")
        _file_id, sheet_id, batch_id = prepare_dxf_sheet(client, project_id, "batch-good.dxf")

        first = client.post(
            f"/api/projects/{project_id}/cad-preview",
            json={"skip_completed": True, "force": False, "continue_on_error": True},
        )
        skipped = client.post(
            f"/api/imports/{batch_id}/cad-preview",
            json={"skip_completed": True, "force": False, "continue_on_error": True},
        )
        with SessionLocal() as db:
            sheet = db.get(DrawingSheet, sheet_id)
            assert sheet is not None
            assert sheet.cad_preview_path
            preview_path = settings.root_dir / sheet.cad_preview_path
            preview_path.unlink()
        regenerated = client.post(
            f"/api/imports/{batch_id}/cad-preview",
            json={"skip_completed": True, "force": False, "continue_on_error": True},
        )
        forced = client.post(
            f"/api/imports/{batch_id}/cad-preview",
            json={"skip_completed": True, "force": True, "continue_on_error": True},
        )

    assert first.status_code == 200, first.text
    assert first.json()["scope"] == "project"
    assert first.json()["summary"]["total_count"] == 1
    assert first.json()["summary"]["success_count"] == 1
    assert first.json()["summary"]["duration_seconds"] >= 0
    assert skipped.status_code == 200, skipped.text
    assert skipped.json()["summary"]["skipped_count"] == 1
    assert regenerated.status_code == 200, regenerated.text
    assert regenerated.json()["summary"]["success_count"] == 1
    assert "CAD_PREVIEW_FILE_MISSING_REGENERATED" in regenerated.json()["items"][0]["warnings"]
    assert forced.status_code == 200, forced.text
    assert forced.json()["summary"]["success_count"] == 1


def test_batch_cad_preview_single_failure_continue_or_stop():
    with TestClient(app) as client:
        project_id = create_project(client, "v0.8.3 CAD 批量失败保护")
        _file_id, _sheet_id, batch_id = prepare_dxf_sheet(client, project_id, "good-preview.dxf")
        create_bad_dxf_sheet(client, project_id, batch_id)

        continued = client.post(
            f"/api/imports/{batch_id}/cad-preview",
            json={"skip_completed": False, "force": True, "continue_on_error": True},
        )
        stopped = client.post(
            f"/api/imports/{batch_id}/cad-preview",
            json={"skip_completed": False, "force": True, "continue_on_error": False},
        )

    assert continued.status_code == 200, continued.text
    assert continued.json()["status"] == "completed_with_errors"
    assert continued.json()["summary"]["success_count"] == 1
    assert continued.json()["summary"]["failed_count"] == 1
    assert continued.json()["errors"][0]["error_code"] in {"CAD_PREVIEW_DXF_OPEN_FAILED", "CAD_PREVIEW_RENDER_FAILED"}
    assert stopped.status_code == 200, stopped.text
    assert stopped.json()["summary"]["failed_count"] == 1
    assert len(stopped.json()["items"]) <= 2
