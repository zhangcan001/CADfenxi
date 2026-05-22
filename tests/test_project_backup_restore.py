import io
import json
import zipfile
from pathlib import Path

from fastapi.testclient import TestClient
from openpyxl import load_workbook
from sqlalchemy import func, select

from backend.core.config import settings
from backend.core.database import SessionLocal
from backend.main import app
from backend.models.backup_record import BackupRecord
from backend.models.drawing_file import DrawingFile
from backend.models.drawing_sheet import DrawingSheet
from backend.models.export_record import ExportRecord
from backend.models.restore_record import RestoreRecord
from dwg_test_helpers import DWG_BYTES, clear_converter_tables, create_converter_setting, write_mock_converter
from test_full_flow_stability_v055 import make_pdf_bytes, title_block_dxf


DXF_BYTES = title_block_dxf("建施-70", "备份恢复 DXF")


def create_project(client: TestClient, name: str = "备份恢复测试项目") -> int:
    response = client.post("/api/projects", json={"name": name, "description": "备份恢复说明"})
    assert response.status_code == 201, response.text
    return response.json()["id"]


def upload_files(client: TestClient, project_id: int, files: list[tuple[str, bytes, str]]) -> dict:
    response = client.post(
        f"/api/projects/{project_id}/imports",
        files=[("files", item) for item in files],
    )
    assert response.status_code == 201, response.text
    return response.json()


def backup_project(client: TestClient, project_id: int) -> dict:
    response = client.post(f"/api/projects/{project_id}/backup")
    assert response.status_code == 200, response.text
    return response.json()


def read_zip_json(zip_path: Path, name: str) -> dict:
    with zipfile.ZipFile(zip_path) as archive:
        assert name in archive.namelist()
        return json.loads(archive.read(name).decode("utf-8"))


def db_count(model: type, project_id: int) -> int:
    with SessionLocal() as db:
        return db.scalar(select(func.count()).select_from(model).where(model.project_id == project_id)) or 0


def project_file_paths(project_id: int) -> list[str]:
    with SessionLocal() as db:
        return [
            item.storage_path
            for item in db.scalars(select(DrawingFile).where(DrawingFile.project_id == project_id)).all()
        ]


def assert_backup_zip(project_id: int, result: dict, expected_files: int) -> tuple[dict, dict]:
    zip_path = settings.root_dir / result["file_path"]
    assert zip_path.exists()
    assert result["backup_id"] > 0
    assert result["file_size"] == zip_path.stat().st_size
    with zipfile.ZipFile(zip_path) as archive:
        names = archive.namelist()
        assert "backup_manifest.json" in names
        assert "database/project_data.json" in names
        if expected_files:
            assert any(name.startswith("files/") for name in names)

    manifest = read_zip_json(zip_path, "backup_manifest.json")
    project_data = read_zip_json(zip_path, "database/project_data.json")
    assert manifest["backup_type"] == "project"
    assert manifest["app_name"] == settings.app_name
    assert manifest["app_version"] == settings.version
    assert manifest["project"]["id"] == project_id
    assert manifest["project"]["name"] == "备份恢复测试项目"
    assert manifest["counts"]["drawing_files"] == expected_files
    assert len(project_data["drawing_files"]) == expected_files
    assert "import_batches" in project_data
    assert "field_evidence" in project_data
    for item in manifest["files"]:
        assert item["relative_path"].startswith("files/")
        assert item["sha256"]
    return manifest, project_data


def test_empty_pdf_dxf_projects_can_be_backed_up_and_listed_downloaded_deleted():
    with TestClient(app) as client:
        empty_project = create_project(client)
        empty_backup = backup_project(client, empty_project)
        assert_backup_zip(empty_project, empty_backup, expected_files=0)

        pdf_project = create_project(client)
        upload_files(client, pdf_project, [("图纸.pdf", make_pdf_bytes("图号 建施-70"), "application/pdf")])
        pdf_backup = backup_project(client, pdf_project)
        manifest, data = assert_backup_zip(pdf_project, pdf_backup, expected_files=1)

        dxf_project = create_project(client)
        upload_files(client, dxf_project, [("总平面.dxf", DXF_BYTES, "application/dxf")])
        dxf_backup = backup_project(client, dxf_project)
        assert_backup_zip(dxf_project, dxf_backup, expected_files=1)

        all_backups = client.get("/api/backups")
        project_backups = client.get(f"/api/projects/{pdf_project}/backups")
        download = client.get(pdf_backup["download_url"])
        delete_response = client.delete(f"/api/backups/{dxf_backup['backup_id']}")
        deleted_download = client.get(dxf_backup["download_url"])

    assert manifest["counts"]["import_batches"] == 1
    assert data["drawing_files"][0]["source_format"] == "pdf"
    assert all_backups.status_code == 200
    assert any(item["backup_id"] == pdf_backup["backup_id"] for item in all_backups.json())
    assert project_backups.status_code == 200
    assert project_backups.json()[0]["project_id"] == pdf_project
    assert download.status_code == 200
    assert download.content.startswith(b"PK")
    assert delete_response.status_code == 204
    assert deleted_download.status_code == 404


def test_dwg_conversion_result_can_be_backed_up_and_restored_as_new_project(tmp_path: Path):
    clear_converter_tables()
    converter = write_mock_converter(tmp_path)
    with TestClient(app) as client:
        create_converter_setting(client, converter)
        project_id = create_project(client)
        upload = upload_files(client, project_id, [("结构-70.dwg", DWG_BYTES, "application/acad")])
        file_id = upload["files"][0]["id"]
        assert client.post(f"/api/files/{file_id}/convert-dwg-to-dxf").status_code == 200
        assert client.post(f"/api/files/{file_id}/prepare-dxf-sheet").status_code == 200
        assert client.post(f"/api/files/{file_id}/parse-dxf").status_code == 200
        sheets = client.get(f"/api/projects/{project_id}/sheets?page_size=100").json()["items"]
        sheet_id = sheets[0]["id"]
        assert client.post(f"/api/sheets/{sheet_id}/generate-candidates").status_code == 200
        assert client.post(f"/api/sheets/{sheet_id}/fuse-fields").status_code == 200
        backup = backup_project(client, project_id)
        before_paths = project_file_paths(project_id)
        restore = client.post(
            f"/api/backups/{backup['backup_id']}/restore",
            json={"restore_mode": "new_project"},
        )
        restored_project_id = restore.json()["new_project_id"]
        restored_project = client.get(f"/api/projects/{restored_project_id}")
        restored_sheets = client.get(f"/api/projects/{restored_project_id}/sheets?page_size=100")
        export = client.post(
            f"/api/projects/{restored_project_id}/exports/excel",
            json={"confirm_incomplete": True, "include_issues": True, "filter": None},
        )

    assert restore.status_code == 200, restore.text
    result = restore.json()
    assert result["source_project_name"] == "备份恢复测试项目"
    assert "恢复" in result["new_project_name"]
    assert result["status"] == "success"
    assert result["restored_counts"]["drawing_files"] == db_count(DrawingFile, project_id)
    assert result["restored_counts"]["drawing_sheets"] == db_count(DrawingSheet, project_id)
    assert restored_project.status_code == 200
    assert restored_sheets.status_code == 200
    assert restored_sheets.json()["total"] == db_count(DrawingSheet, restored_project_id)
    assert db_count(DrawingFile, restored_project_id) == db_count(DrawingFile, project_id)
    assert db_count(ExportRecord, project_id) == 0
    assert export.status_code == 200, export.text
    assert load_workbook(settings.root_dir / export.json()["file_path"])["导出说明"]["B3"].value == settings.version
    assert all(f"project_{project_id}" in path for path in before_paths)
    assert all(f"project_{restored_project_id}" in path for path in project_file_paths(restored_project_id))
    assert (settings.root_dir / backup["file_path"]).exists()
    with SessionLocal() as db:
        record = db.scalar(select(RestoreRecord).where(RestoreRecord.new_project_id == restored_project_id))
        restored_file = db.scalar(select(DrawingFile).where(DrawingFile.project_id == restored_project_id))
        restored_sheet = db.scalar(select(DrawingSheet).where(DrawingSheet.project_id == restored_project_id))
        assert record is not None and record.status == "success"
        assert restored_file and f"project_{restored_project_id}" in restored_file.storage_path
        assert restored_file.converted_file_path and f"project_{restored_project_id}" in restored_file.converted_file_path
        assert restored_sheet and restored_sheet.preview_path is None


def test_restore_empty_pdf_and_dxf_backups_as_new_projects():
    with TestClient(app) as client:
        empty_project = create_project(client)
        empty_backup = backup_project(client, empty_project)
        empty_restore = client.post(
            f"/api/backups/{empty_backup['backup_id']}/restore",
            json={"restore_mode": "new_project"},
        )

        pdf_project = create_project(client)
        upload = upload_files(client, pdf_project, [("建施-71.pdf", make_pdf_bytes("图号 建施-71"), "application/pdf")])
        pdf_file_id = upload["files"][0]["id"]
        assert client.post(f"/api/files/{pdf_file_id}/split").status_code == 200
        pdf_backup = backup_project(client, pdf_project)
        pdf_restore = client.post(
            f"/api/backups/{pdf_backup['backup_id']}/restore",
            json={"restore_mode": "new_project"},
        )

        dxf_project = create_project(client)
        upload = upload_files(client, dxf_project, [("建施-72.dxf", DXF_BYTES, "application/dxf")])
        dxf_file_id = upload["files"][0]["id"]
        assert client.post(f"/api/files/{dxf_file_id}/prepare-dxf-sheet").status_code == 200
        dxf_backup = backup_project(client, dxf_project)
        dxf_restore = client.post(
            f"/api/backups/{dxf_backup['backup_id']}/restore",
            json={"restore_mode": "new_project"},
        )

    assert empty_restore.status_code == 200
    assert pdf_restore.status_code == 200
    assert dxf_restore.status_code == 200
    assert db_count(DrawingFile, pdf_restore.json()["new_project_id"]) == 1
    assert db_count(DrawingSheet, pdf_restore.json()["new_project_id"]) == 1
    assert db_count(DrawingFile, dxf_restore.json()["new_project_id"]) == 1
    assert db_count(DrawingSheet, dxf_restore.json()["new_project_id"]) == 1


def make_bad_backup(client: TestClient, project_id: int, missing: str | None = None, bad_zip: bool = False) -> int:
    backup = backup_project(client, project_id)
    path = settings.root_dir / backup["file_path"]
    if bad_zip:
        path.write_bytes(b"not a zip")
    else:
        with zipfile.ZipFile(path) as archive:
            entries = {name: archive.read(name) for name in archive.namelist() if name != missing}
        with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for name, content in entries.items():
                archive.writestr(name, content)
    return backup["backup_id"]


def test_restore_validation_errors_are_structured_and_do_not_delete_existing_project():
    with TestClient(app) as client:
        project_id = create_project(client)
        backup_id = make_bad_backup(client, project_id, missing="backup_manifest.json")
        missing_manifest = client.post(f"/api/backups/{backup_id}/restore", json={"restore_mode": "new_project"})

        project_data_backup_id = make_bad_backup(client, project_id, missing="database/project_data.json")
        missing_data = client.post(f"/api/backups/{project_data_backup_id}/restore", json={"restore_mode": "new_project"})

        bad_zip_backup_id = make_bad_backup(client, project_id, bad_zip=True)
        bad_zip = client.post(f"/api/backups/{bad_zip_backup_id}/restore", json={"restore_mode": "new_project"})

        valid_backup = backup_project(client, project_id)
        overwrite = client.post(f"/api/backups/{valid_backup['backup_id']}/restore", json={"restore_mode": "overwrite"})
        original_project = client.get(f"/api/projects/{project_id}")
        restores = client.get("/api/restores")

    assert missing_manifest.status_code == 400
    assert missing_manifest.json()["detail"]["error_code"] == "BACKUP_MANIFEST_MISSING"
    assert missing_data.status_code == 400
    assert missing_data.json()["detail"]["error_code"] == "BACKUP_DATA_MISSING"
    assert bad_zip.status_code == 400
    assert bad_zip.json()["detail"]["error_code"] == "RESTORE_FAILED"
    assert overwrite.status_code == 400
    assert overwrite.json()["detail"]["error_code"] == "RESTORE_MODE_NOT_SUPPORTED"
    assert original_project.status_code == 200
    assert any(item["status"] == "failed" for item in restores.json())


def test_backup_missing_project_returns_structured_error():
    with TestClient(app) as client:
        response = client.post("/api/projects/999999999/backup")

    assert response.status_code == 404
    assert response.json()["detail"] == {
        "error_code": "BACKUP_PROJECT_NOT_FOUND",
        "message": "项目不存在，无法创建备份。",
    }


def test_delete_missing_backup_returns_structured_error():
    with TestClient(app) as client:
        response = client.delete("/api/backups/999999999")

    assert response.status_code == 404
    assert response.json()["detail"]["error_code"] == "BACKUP_FILE_NOT_FOUND"
