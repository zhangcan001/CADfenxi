"""v1.5 项目交付包导出测试。"""
from __future__ import annotations

import json
import zipfile
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import select

from backend.core.config import settings
from backend.core.database import SessionLocal
from backend.main import app
from backend.models.drawing_issue import DrawingIssue
from backend.models.drawing_sheet import DrawingSheet
from test_project_backup_restore import backup_project, create_project
from test_v143_real_project_stable import test_v143_excel_delivery_and_core_flows_do_not_regress
from test_v14_real_project_trial_guard import _run_realistic_trial_project


VERSION = "v1.5.1-fast-delivery-package-fix"


def _snapshot(project_id: int) -> tuple[dict[int, str], dict[int, str]]:
    with SessionLocal() as db:
        sheets = db.scalars(select(DrawingSheet).where(DrawingSheet.project_id == project_id)).all()
        issues = db.scalars(select(DrawingIssue).where(DrawingIssue.project_id == project_id)).all()
        return (
            {sheet.id: sheet.review_status for sheet in sheets},
            {issue.id: issue.status for issue in issues},
        )


def _create_delivery(client: TestClient, project_id: int, **overrides) -> dict:
    payload = {
        "include_original_files": False,
        "include_cad_previews": True,
        "include_pdf_previews": True,
        "include_latest_excel": True,
    }
    payload.update(overrides)
    response = client.post(f"/api/projects/{project_id}/delivery-package", json=payload)
    assert response.status_code == 200, response.text
    return response.json()


def _zip_names(result: dict, project_id: int) -> tuple[Path, list[str]]:
    package_path = settings.projects_dir / f"project_{project_id}" / "delivery_packages" / result["file_name"]
    assert package_path.is_file()
    with zipfile.ZipFile(package_path) as archive:
        return package_path, archive.namelist()


def test_v15_health_version():
    with TestClient(app) as client:
        response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "version": VERSION, "database": "ok", "storage": "ok"}
    assert settings.version == VERSION


def test_v15_empty_project_delivery_package_has_clear_error():
    with TestClient(app) as client:
        project_id = create_project(client, "v1.5 空项目交付包")
        response = client.post(
            f"/api/projects/{project_id}/delivery-package",
            json={
                "include_original_files": False,
                "include_cad_previews": True,
                "include_pdf_previews": True,
                "include_latest_excel": True,
            },
        )

    assert response.status_code == 409
    assert response.json()["detail"]["error_code"] == "DELIVERY_PACKAGE_EMPTY_PROJECT"
    assert "还没有图纸" in response.json()["detail"]["message"]


def test_v15_delivery_package_with_existing_excel_contains_required_files(tmp_path: Path):
    with TestClient(app) as client:
        result = _run_realistic_trial_project(client, tmp_path)
        project_id = result["project_id"]
        before = _snapshot(project_id)
        delivery = _create_delivery(client, project_id, include_original_files=False)
        after = _snapshot(project_id)
        download = client.get(delivery["download_url"])
        backup = backup_project(client, project_id)

    assert before == after
    assert delivery["package_id"].startswith("delivery_")
    assert delivery["file_name"].startswith(f"project_delivery_{project_id}_")
    assert delivery["file_size"] > 0
    assert download.status_code == 200
    assert download.headers["content-type"] == "application/zip"
    assert backup["backup_id"] > 0

    package_path, names = _zip_names(delivery, project_id)
    assert delivery["file_size"] == package_path.stat().st_size
    assert "交付说明.txt" in names
    assert "project_summary.json" in names
    assert "issue_summary.json" in names
    assert "图纸台账.xlsx" in names
    assert any(name.startswith("cad_previews/") for name in names)
    assert any(name.startswith("pdf_previews/") for name in names)
    assert not any(name.startswith("original_files/") for name in names)

    with zipfile.ZipFile(package_path) as archive:
        readme = archive.read("交付说明.txt").decode("utf-8")
        project_summary = json.loads(archive.read("project_summary.json").decode("utf-8"))
        issue_summary = json.loads(archive.read("issue_summary.json").decode("utf-8"))
    assert "项目交付包" in readme
    assert "如需恢复系统数据，请使用项目备份包" in readme
    assert project_summary["drawing_sheet_count"] >= 4
    assert project_summary["included"]["original_files"] is False
    assert issue_summary["total"] >= 1


def test_v15_delivery_package_auto_generates_excel_and_can_include_original_files(tmp_path: Path):
    with TestClient(app) as client:
        result = _run_realistic_trial_project(client, tmp_path)
        project_id = result["restored_project_id"]
        # 恢复项目已有图纸，但本测试不依赖已有导出记录；服务会确保可用 Excel。
        before = _snapshot(project_id)
        delivery = _create_delivery(client, project_id, include_original_files=True)
        after = _snapshot(project_id)

    assert before == after
    package_path, names = _zip_names(delivery, project_id)
    assert "图纸台账.xlsx" in names
    assert any(name.startswith("original_files/") for name in names)
    with zipfile.ZipFile(package_path) as archive:
        project_summary = json.loads(archive.read("project_summary.json").decode("utf-8"))
    assert project_summary["included"]["original_files"] is True


def test_v15_delivery_package_core_flows_do_not_regress(tmp_path: Path):
    test_v143_excel_delivery_and_core_flows_do_not_regress(tmp_path)
