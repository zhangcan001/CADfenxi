"""v1.1.6 深度抽取稳定收口测试。"""
from __future__ import annotations

from datetime import date
from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import select

from backend.core.config import settings
from backend.core.database import SessionLocal
from backend.main import app
from backend.models.drawing_file import DrawingFile
from backend.models.drawing_issue import DrawingIssue
from backend.models.drawing_sheet import DrawingSheet
from backend.models.import_batch import ImportBatch
from backend.models.project import Project
from scripts.build_portable_package import DEFAULT_VERSION, build_portable_package, package_name


VERSION = "v1.1.6-deep-extract-stable"


def _create_project_graph(name: str = "v1.1.6 深度抽取稳定") -> tuple[int, int, int]:
    with SessionLocal() as db:
        project = Project(name=f"{name}-{uuid4().hex[:6]}")
        db.add(project)
        db.flush()
        batch = ImportBatch(
            project_id=project.id,
            batch_name="v1.1.6 测试批次",
            file_count=1,
        )
        db.add(batch)
        db.flush()
        drawing_file = DrawingFile(
            project_id=project.id,
            batch_id=batch.id,
            original_name="v116.dxf",
            file_ext=".dxf",
            source_format="dxf",
            file_size=10,
            file_hash=uuid4().hex,
            storage_path=f"app_data/temp/{uuid4().hex}.dxf",
            status="preprocessed",
            parse_status="success",
        )
        db.add(drawing_file)
        db.flush()
        project_id = project.id
        batch_id = batch.id
        file_id = drawing_file.id
        db.commit()
    return project_id, batch_id, file_id


def _add_sheet(
    project_id: int,
    batch_id: int,
    file_id: int,
    *,
    drawing_no: str | None = "建施-116",
    drawing_name: str | None = "深度抽取稳定",
    discipline: str | None = "建筑",
    version: str | None = "A",
    issue_date: date | None = date(2026, 5, 27),
    review_status: str = "confirmed",
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
            confidence_score=95,
            trust_level="A",
            status="confirmed",
            review_status=review_status,
        )
        db.add(sheet)
        db.flush()
        sheet_id = sheet.id
        db.commit()
    return sheet_id


def test_v116_health_version_and_package_default():
    with TestClient(app) as client:
        response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "version": VERSION, "database": "ok", "storage": "ok"}
    assert settings.version == VERSION
    assert DEFAULT_VERSION == VERSION


def test_v116_empty_project_deep_extract_queries_are_safe():
    with TestClient(app) as client:
        project = client.post("/api/projects", json={"name": f"v1.1.6 空项目-{uuid4().hex[:6]}"})
        assert project.status_code == 201, project.text
        project_id = project.json()["id"]

        tables = client.get(f"/api/projects/{project_id}/tables")
        blocks = client.get(f"/api/projects/{project_id}/block-stats")
        consistency = client.post(f"/api/projects/{project_id}/consistency-check")

    assert tables.status_code == 200
    assert tables.json() == []
    assert blocks.status_code == 200
    assert blocks.json() == []
    assert consistency.status_code == 200
    assert consistency.json() == {
        "project_id": project_id,
        "checked_sheets": 0,
        "issues_created": 0,
        "by_code": {},
    }


def test_v116_missing_cad_parse_result_returns_clear_errors():
    project_id, batch_id, file_id = _create_project_graph("v1.1.6 缺 CAD JSON")
    sheet_id = _add_sheet(project_id, batch_id, file_id)

    with TestClient(app) as client:
        table_resp = client.post(f"/api/sheets/{sheet_id}/extract-tables", json={})
        block_resp = client.post(f"/api/sheets/{sheet_id}/extract-blocks", json={})

    assert table_resp.status_code == 404
    assert table_resp.json()["detail"]["error_code"] == "CAD_PARSE_NOT_FOUND"
    assert block_resp.status_code == 404
    assert block_resp.json()["detail"]["error_code"] == "CAD_PARSE_NOT_FOUND"


def test_v116_consistency_ignores_unconfirmed_sheets():
    project_id, batch_id, file_id = _create_project_graph("v1.1.6 未确认不参与")
    _add_sheet(
        project_id,
        batch_id,
        file_id,
        drawing_no="建施-116-未确认",
        review_status="unreviewed",
    )
    _add_sheet(
        project_id,
        batch_id,
        file_id,
        drawing_no="建施-116-未确认",
        review_status="pending",
    )

    with TestClient(app) as client:
        response = client.post(f"/api/projects/{project_id}/consistency-check")

    assert response.status_code == 200
    body = response.json()
    assert body["checked_sheets"] == 0
    assert body["issues_created"] == 0
    with SessionLocal() as db:
        cross_count = db.scalars(
            select(DrawingIssue).where(DrawingIssue.project_id == project_id)
        ).all()
    assert cross_count == []


def test_v116_consistency_confirmed_clean_project_has_no_issues():
    project_id, batch_id, file_id = _create_project_graph("v1.1.6 已确认干净")
    _add_sheet(project_id, batch_id, file_id, drawing_no="建施-116-A", version="A")
    _add_sheet(project_id, batch_id, file_id, drawing_no="建施-117-A", version="A")

    with TestClient(app) as client:
        response = client.post(f"/api/projects/{project_id}/consistency-check")

    assert response.status_code == 200
    assert response.json()["checked_sheets"] == 2
    assert response.json()["issues_created"] == 0


def test_v116_portable_package_info_uses_formal_stable_label(tmp_path: Path):
    dist = settings.root_dir / "frontend" / "dist"
    dist.mkdir(parents=True, exist_ok=True)
    (dist / "index.html").write_text("<!doctype html><html></html>", encoding="utf-8")

    summary = build_portable_package(
        version=VERSION,
        clean=True,
        skip_tests=True,
    )
    package_dir = settings.root_dir / "release" / package_name(VERSION)
    package_info = summary.package_info_path.read_text(encoding="utf-8")

    assert summary.integrity_ok is True
    assert summary.package_dir == package_dir
    assert f"版本：{VERSION}" in package_info
    assert "包类型：Windows 本地便携正式稳定版" in package_info
    assert (package_dir / "frontend" / "dist" / "index.html").is_file()
