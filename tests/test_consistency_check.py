"""跨图一致性校验测试。"""
from __future__ import annotations

from datetime import date
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from backend.core.database import SessionLocal
from backend.main import app
from backend.models.drawing_file import DrawingFile
from backend.models.drawing_issue import DrawingIssue
from backend.models.drawing_sheet import DrawingSheet


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as test_client:
        yield test_client


def _create_project(client: TestClient, name: str) -> tuple[int, int, int]:
    project = client.post("/api/projects", json={"name": f"{name}-{uuid4().hex[:6]}"})
    assert project.status_code == 201, project.text
    project_id = project.json()["id"]
    upload = client.post(
        f"/api/projects/{project_id}/imports",
        files=[("files", ("placeholder.pdf", b"%PDF-1.4\n%%EOF", "application/pdf"))],
    )
    assert upload.status_code == 201, upload.text
    batch_id = upload.json()["id"]
    file_id = upload.json()["files"][0]["id"]
    return project_id, batch_id, file_id


def _add_confirmed_sheet(
    project_id: int,
    batch_id: int,
    file_id: int,
    *,
    drawing_no: str,
    drawing_name: str = "测试图",
    discipline: str | None = None,
    version: str | None = None,
    issue_date: date | None = None,
) -> int:
    with SessionLocal() as db:
        page_no = db.query(DrawingSheet).filter(DrawingSheet.file_id == file_id).count() + 1
        sheet = DrawingSheet(
            project_id=project_id,
            batch_id=batch_id,
            file_id=file_id,
            page_no=page_no,
            sheet_type="unknown",
            drawing_no=drawing_no,
            drawing_name=drawing_name,
            discipline=discipline,
            version=version,
            issue_date=issue_date,
            status="need_review",
            review_status="confirmed",
            trust_level="A",
            confidence_score=90.0,
        )
        db.add(sheet)
        db.flush()
        sheet_id = sheet.id
        db.commit()
    return sheet_id


def _cross_issue_codes(project_id: int) -> set[str]:
    with SessionLocal() as db:
        rows = db.scalars(
            select(DrawingIssue.issue_code)
            .where(DrawingIssue.project_id == project_id)
            .where(DrawingIssue.issue_code.like("CROSS_%"))
            .where(DrawingIssue.status == "open")
        ).all()
    return set(rows)


def test_duplicate_drawing_no_creates_issue(client: TestClient):
    project_id, batch_id, file_id = _create_project(client, "跨图-重复图号")
    _add_confirmed_sheet(project_id, batch_id, file_id, drawing_no="建施-01", discipline="建筑")
    _add_confirmed_sheet(project_id, batch_id, file_id, drawing_no="建施-01", discipline="建筑")

    resp = client.post(f"/api/projects/{project_id}/consistency-check")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["by_code"].get("CROSS_DRAWING_NO_DUPLICATE", 0) >= 2
    assert "CROSS_DRAWING_NO_DUPLICATE" in _cross_issue_codes(project_id)


def test_version_skip_creates_issue(client: TestClient):
    project_id, batch_id, file_id = _create_project(client, "跨图-版本跳号")
    _add_confirmed_sheet(project_id, batch_id, file_id, drawing_no="建施-02", version="A")
    _add_confirmed_sheet(project_id, batch_id, file_id, drawing_no="建施-02", version="C")

    resp = client.post(f"/api/projects/{project_id}/consistency-check")
    assert resp.status_code == 200, resp.text
    assert resp.json()["by_code"].get("CROSS_VERSION_SKIP", 0) >= 2


def test_discipline_prefix_mismatch_creates_issue(client: TestClient):
    project_id, batch_id, file_id = _create_project(client, "跨图-前缀错位")
    _add_confirmed_sheet(
        project_id, batch_id, file_id, drawing_no="电施-05", discipline="建筑"
    )

    resp = client.post(f"/api/projects/{project_id}/consistency-check")
    assert resp.status_code == 200, resp.text
    assert resp.json()["by_code"].get("CROSS_DISCIPLINE_PREFIX_MISMATCH", 0) >= 1


def test_issue_date_inconsistent_creates_issue(client: TestClient):
    project_id, batch_id, file_id = _create_project(client, "跨图-日期不一致")
    _add_confirmed_sheet(
        project_id, batch_id, file_id,
        drawing_no="水施-01", version="A", issue_date=date(2026, 1, 1)
    )
    _add_confirmed_sheet(
        project_id, batch_id, file_id,
        drawing_no="水施-01", version="A", issue_date=date(2026, 2, 1)
    )

    resp = client.post(f"/api/projects/{project_id}/consistency-check")
    assert resp.status_code == 200, resp.text
    assert resp.json()["by_code"].get("CROSS_ISSUE_DATE_INCONSISTENT", 0) >= 2


def test_version_date_regress_creates_issue(client: TestClient):
    project_id, batch_id, file_id = _create_project(client, "跨图-版本日期倒退")
    _add_confirmed_sheet(
        project_id, batch_id, file_id,
        drawing_no="结施-03", version="A", issue_date=date(2026, 3, 1)
    )
    _add_confirmed_sheet(
        project_id, batch_id, file_id,
        drawing_no="结施-03", version="B", issue_date=date(2026, 2, 1)
    )

    resp = client.post(f"/api/projects/{project_id}/consistency-check")
    assert resp.status_code == 200, resp.text
    # B 版本日期早于 A 版本，应触发倒退告警
    assert resp.json()["by_code"].get("CROSS_VERSION_DATE_REGRESS", 0) >= 1


def test_running_check_twice_replaces_old_cross_issues(client: TestClient):
    project_id, batch_id, file_id = _create_project(client, "跨图-去重")
    _add_confirmed_sheet(project_id, batch_id, file_id, drawing_no="建施-09")
    _add_confirmed_sheet(project_id, batch_id, file_id, drawing_no="建施-09")

    client.post(f"/api/projects/{project_id}/consistency-check")
    first_count = len(_cross_issue_codes(project_id))
    # 再跑一次：不应叠加
    client.post(f"/api/projects/{project_id}/consistency-check")
    second_count = len(_cross_issue_codes(project_id))
    assert first_count == second_count
