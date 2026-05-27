from pathlib import Path

from fastapi.testclient import TestClient

from backend.core.config import settings
from backend.main import app
from scripts.build_portable_package import build_portable_package, package_name
from test_full_flow_stability_v055 import make_pdf_bytes, title_block_dxf
from test_project_backup_restore import backup_project, create_project, upload_files


VERSION = "v1.2.2-fast-import-fix"
ROOT = Path(__file__).resolve().parents[1]


def test_v073_health_version_and_release_documents():
    with TestClient(app) as client:
        health = client.get("/api/health")

    assert health.status_code == 200
    assert health.json() == {"status": "ok", "version": VERSION, "database": "ok", "storage": "ok"}
    assert settings.version == VERSION
    assert (ROOT / "docs" / "RELEASE_CHECKLIST_v0.7.3-backup-stable.md").exists()
    assert (ROOT / "docs" / "FINAL_ACCEPTANCE_v0.7.3-backup-stable.md").exists()


def test_v073_portable_package_and_package_info():
    summary = build_portable_package(ROOT, version=VERSION, clean=True)
    package_dir = ROOT / "release" / package_name(VERSION)
    package_info = (package_dir / "package_info.txt").read_text(encoding="utf-8")

    assert summary.package_dir == package_dir
    assert package_dir.is_dir()
    assert VERSION in package_info
    assert (package_dir / "backend").is_dir()
    assert (package_dir / "recognizer").is_dir()
    assert (package_dir / "frontend" / "dist" / "index.html").is_file()
    assert (package_dir / "scripts").is_dir()
    assert (package_dir / "app_data" / "backups" / ".gitkeep").is_file()
    assert (package_dir / "docs" / "RELEASE_CHECKLIST_v0.7.3-backup-stable.md").is_file()
    assert not (package_dir / ".git").exists()
    assert not (package_dir / "frontend" / "node_modules").exists()
    assert not (package_dir / "app_data" / "database" / "app.db").exists()


def test_v073_backup_verify_delete_and_restore_as_new_project_regression():
    with TestClient(app) as client:
        project_id = create_project(client, "v0.7.3 PDF 回归项目")
        upload = upload_files(client, project_id, [("v073.pdf", make_pdf_bytes("图号 建施-073"), "application/pdf")])
        assert client.post(f"/api/files/{upload['files'][0]['id']}/split").status_code == 200
        backup = backup_project(client, project_id)

        verify = client.get(f"/api/backups/{backup['backup_id']}/verify")
        restore = client.post(f"/api/backups/{backup['backup_id']}/restore", json={"restore_mode": "new_project"})
        restored_project_id = restore.json()["new_project_id"]
        restored_project = client.get(f"/api/projects/{restored_project_id}")
        export = client.post(
            f"/api/projects/{restored_project_id}/exports/excel",
            json={"confirm_incomplete": True, "include_issues": True, "filter": None},
        )
        delete_backup = client.delete(f"/api/backups/{backup['backup_id']}")
        original_project = client.get(f"/api/projects/{project_id}")
        restored_project_after_delete = client.get(f"/api/projects/{restored_project_id}")

    assert verify.status_code == 200
    assert verify.json()["valid"] is True
    assert verify.json()["summary"]["has_manifest"] is True
    assert verify.json()["summary"]["has_project_data"] is True
    assert restore.status_code == 200
    assert restore.json()["new_project_id"] != project_id
    assert "恢复" in restore.json()["new_project_name"]
    assert restored_project.status_code == 200
    assert export.status_code == 200
    assert delete_backup.status_code == 204
    assert original_project.status_code == 200
    assert restored_project_after_delete.status_code == 200


def test_v073_dxf_backup_restore_smoke_regression():
    dxf_bytes = title_block_dxf("建施-073", "v0.7.3 DXF 回归")
    with TestClient(app) as client:
        project_id = create_project(client, "v0.7.3 DXF 回归项目")
        upload = upload_files(client, project_id, [("v073.dxf", dxf_bytes, "application/dxf")])
        file_id = upload["files"][0]["id"]
        assert client.post(f"/api/files/{file_id}/prepare-dxf-sheet").status_code == 200
        backup = backup_project(client, project_id)
        restore = client.post(f"/api/backups/{backup['backup_id']}/restore", json={"restore_mode": "new_project"})
        sheets = client.get(f"/api/projects/{restore.json()['new_project_id']}/sheets?page_size=100")

    assert restore.status_code == 200
    assert sheets.status_code == 200
    assert sheets.json()["total"] >= 1


def test_v073_restore_failure_does_not_break_existing_project():
    with TestClient(app) as client:
        project_id = create_project(client, "v0.7.3 恢复失败保护")
        backup = backup_project(client, project_id)
        backup_path = settings.root_dir / backup["file_path"]
        backup_path.write_bytes(b"not a zip")
        failed_restore = client.post(f"/api/backups/{backup['backup_id']}/restore", json={"restore_mode": "new_project"})
        project_after_failure = client.get(f"/api/projects/{project_id}")

    assert failed_restore.status_code == 400
    assert failed_restore.json()["detail"]["error_code"] == "RESTORE_FAILED"
    assert project_after_failure.status_code == 200

