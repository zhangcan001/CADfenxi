import json
import zipfile
from pathlib import Path

from fastapi.testclient import TestClient

from backend.core.config import settings
from backend.main import app
from test_project_backup_restore import backup_project, create_project, upload_files
from test_full_flow_stability_v055 import make_pdf_bytes


def rewrite_zip_without(path: Path, missing: str) -> None:
    with zipfile.ZipFile(path) as archive:
        entries = {name: archive.read(name) for name in archive.namelist() if name != missing}
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, content in entries.items():
            archive.writestr(name, content)


def rewrite_zip_drop_first_file_entry(path: Path) -> str:
    with zipfile.ZipFile(path) as archive:
        entries = {name: archive.read(name) for name in archive.namelist()}
    manifest = json.loads(entries["backup_manifest.json"].decode("utf-8"))
    missing_file = manifest["files"][0]["relative_path"]
    entries.pop(missing_file)
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, content in entries.items():
            archive.writestr(name, content)
    return missing_file


def test_verify_backup_success_and_project_integrity_check():
    with TestClient(app) as client:
        project_id = create_project(client)
        upload_files(client, project_id, [("建施-81.pdf", make_pdf_bytes("图号 建施-81"), "application/pdf")])
        backup = backup_project(client, project_id)
        verify = client.get(f"/api/backups/{backup['backup_id']}/verify")
        integrity = client.get(f"/api/projects/{project_id}/integrity-check")

    assert verify.status_code == 200
    assert verify.json()["valid"] is True
    assert verify.json()["counts"]["manifest_files"] >= 1
    assert verify.json()["summary"]["has_manifest"] is True
    assert verify.json()["summary"]["has_project_data"] is True
    assert verify.json()["summary"]["file_count"] >= 1
    assert verify.json()["summary"]["missing_file_count"] == 0
    assert verify.json()["summary"]["checksum_failed_count"] == 0
    assert integrity.status_code == 200
    assert integrity.json()["valid"] is True
    assert integrity.json()["path_check"]["invalid_paths"] == 0


def test_verify_backup_reports_missing_manifest_project_data_and_file_warning():
    with TestClient(app) as client:
        project_id = create_project(client)
        upload_files(client, project_id, [("建施-82.pdf", make_pdf_bytes("图号 建施-82"), "application/pdf")])

        missing_manifest_backup = backup_project(client, project_id)
        rewrite_zip_without(settings.root_dir / missing_manifest_backup["file_path"], "backup_manifest.json")
        missing_manifest = client.get(f"/api/backups/{missing_manifest_backup['backup_id']}/verify")

        missing_data_backup = backup_project(client, project_id)
        rewrite_zip_without(settings.root_dir / missing_data_backup["file_path"], "database/project_data.json")
        missing_data = client.get(f"/api/backups/{missing_data_backup['backup_id']}/verify")

        missing_file_backup = backup_project(client, project_id)
        dropped = rewrite_zip_drop_first_file_entry(settings.root_dir / missing_file_backup["file_path"])
        missing_file = client.get(f"/api/backups/{missing_file_backup['backup_id']}/verify")

    assert missing_manifest.status_code == 200
    assert missing_manifest.json()["valid"] is False
    assert missing_manifest.json()["summary"]["has_manifest"] is False
    assert any("BACKUP_MANIFEST_MISSING" in item for item in missing_manifest.json()["errors"])
    assert missing_data.status_code == 200
    assert missing_data.json()["valid"] is False
    assert missing_data.json()["summary"]["has_project_data"] is False
    assert any("BACKUP_DATA_MISSING" in item for item in missing_data.json()["errors"])
    assert missing_file.status_code == 200
    assert missing_file.json()["valid"] is True
    assert missing_file.json()["counts"]["missing_files"] == 1
    assert missing_file.json()["summary"]["missing_file_count"] == 1
    assert any(dropped in item for item in missing_file.json()["warnings"])
