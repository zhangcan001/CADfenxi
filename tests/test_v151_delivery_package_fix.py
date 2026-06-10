"""v1.5.1 项目交付包真实使用问题修复测试。"""
from __future__ import annotations

import zipfile
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import func, select

from backend.core.config import settings
from backend.core.database import SessionLocal
from backend.main import app
from backend.models.backup_record import BackupRecord
from backend.models.drawing_issue import DrawingIssue
from backend.models.drawing_sheet import DrawingSheet
from backend.models.export_record import ExportRecord
from test_project_backup_restore import backup_project, create_project
from test_v143_real_project_stable import test_v143_excel_delivery_and_core_flows_do_not_regress
from test_v15_delivery_package import _create_delivery, _zip_names
from test_v15_delivery_package import _snapshot as delivery_snapshot
from test_v15_delivery_package import _run_realistic_trial_project


VERSION = "v1.5.1-fast-delivery-package-fix"


def _export_count(project_id: int) -> int:
    with SessionLocal() as db:
        return db.scalar(
            select(func.count()).select_from(ExportRecord).where(ExportRecord.project_id == project_id)
        ) or 0


def _backup_count(project_id: int) -> int:
    with SessionLocal() as db:
        return db.scalar(
            select(func.count()).select_from(BackupRecord).where(BackupRecord.project_id == project_id)
        ) or 0


def test_v151_health_version():
    with TestClient(app) as client:
        response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "version": VERSION, "database": "ok", "storage": "ok"}
    assert settings.version == VERSION


def test_v151_delivery_auto_generates_excel_without_export_history_or_state_change(tmp_path: Path):
    with TestClient(app) as client:
        result = _run_realistic_trial_project(client, tmp_path)
        project_id = result["project_id"]
        before_state = delivery_snapshot(project_id)
        before_exports = _export_count(project_id)
        with SessionLocal() as db:
            db.query(ExportRecord).filter(ExportRecord.project_id == project_id).delete(synchronize_session=False)
            db.commit()

        delivery = _create_delivery(client, project_id, include_original_files=False)
        after_state = delivery_snapshot(project_id)
        after_exports = _export_count(project_id)

    assert before_state == after_state
    assert before_exports >= 1
    assert after_exports == 0
    assert delivery["included"]["excel"] is True
    assert any("自动生成" in warning for warning in delivery["warnings"])
    assert any("未写入导出历史" in warning for warning in delivery["warnings"])

    package_path, names = _zip_names(delivery, project_id)
    assert "图纸台账.xlsx" in names
    assert not any(name.startswith("exported_files/") for name in names)
    with zipfile.ZipFile(package_path) as archive:
        readme = archive.read("交付说明.txt").decode("utf-8")
    assert "不用于恢复系统数据" in readme
    assert "原始图纸默认不包含" in readme


def test_v151_original_files_option_and_package_size_warning(tmp_path: Path):
    with TestClient(app) as client:
        result = _run_realistic_trial_project(client, tmp_path)
        project_id = result["project_id"]
        without_originals = _create_delivery(client, project_id, include_original_files=False)
        with_originals = _create_delivery(client, project_id, include_original_files=True)

    _, without_names = _zip_names(without_originals, project_id)
    _, with_names = _zip_names(with_originals, project_id)

    assert without_originals["included"]["original_files"] is False
    assert not any(name.startswith("original_files/") for name in without_names)
    assert any("默认未包含原始图纸" in warning for warning in without_originals["warnings"])
    assert with_originals["included"]["original_files"] is True
    assert any(name.startswith("original_files/") for name in with_names)
    assert any("交付包可能较大" in warning for warning in with_originals["warnings"])


def test_v151_delivery_failure_and_download_errors_do_not_break_project(tmp_path: Path):
    with TestClient(app) as client:
        empty_project_id = create_project(client, "v1.5.1 空项目交付包失败保护")
        empty_before = delivery_snapshot(empty_project_id)
        empty_response = client.post(
            f"/api/projects/{empty_project_id}/delivery-package",
            json={
                "include_original_files": False,
                "include_cad_previews": True,
                "include_pdf_previews": True,
                "include_latest_excel": True,
            },
        )
        empty_after = delivery_snapshot(empty_project_id)

        result = _run_realistic_trial_project(client, tmp_path)
        project_id = result["project_id"]
        before = delivery_snapshot(project_id)
        delivery = _create_delivery(client, project_id)
        bad_download = client.get(
            f"/api/projects/{project_id}/delivery-package/download?package_id=delivery_missing_000000"
        )
        wrong_project_download = client.get(
            f"/api/projects/999999999/delivery-package/download?package_id={delivery['package_id']}"
        )
        after = delivery_snapshot(project_id)

    assert empty_response.status_code == 409
    assert empty_response.json()["detail"]["error_code"] == "DELIVERY_PACKAGE_EMPTY_PROJECT"
    assert empty_before == empty_after
    assert before == after
    assert bad_download.status_code == 404
    assert bad_download.json()["detail"]["error_code"] == "DELIVERY_PACKAGE_NOT_FOUND"
    assert wrong_project_download.status_code == 404
    assert wrong_project_download.json()["detail"]["error_code"] == "PROJECT_NOT_FOUND"


def test_v151_delivery_and_backup_packages_do_not_affect_each_other(tmp_path: Path):
    with TestClient(app) as client:
        result = _run_realistic_trial_project(client, tmp_path)
        project_id = result["project_id"]
        before_state = delivery_snapshot(project_id)
        before_backups = _backup_count(project_id)
        delivery = _create_delivery(client, project_id)
        backup = backup_project(client, project_id)
        backup_download = client.get(backup["download_url"])
        delivery_download = client.get(delivery["download_url"])
        after_state = delivery_snapshot(project_id)
        after_backups = _backup_count(project_id)

    assert before_state == after_state
    assert after_backups == before_backups + 1
    assert backup_download.status_code == 200
    assert delivery_download.status_code == 200
    assert backup["file_name"].startswith("project_backup_")
    assert delivery["file_name"].startswith("project_delivery_")


def test_v151_delivery_core_flows_do_not_regress(tmp_path: Path):
    test_v143_excel_delivery_and_core_flows_do_not_regress(tmp_path)
