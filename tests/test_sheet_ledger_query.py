from fastapi.testclient import TestClient

from backend.core.database import SessionLocal
from backend.main import app
from backend.models.drawing_issue import DrawingIssue
from backend.models.drawing_sheet import DrawingSheet


def create_project(client: TestClient, name: str = "台账查询测试") -> int:
    response = client.post("/api/projects", json={"name": name})
    assert response.status_code == 201
    return response.json()["id"]


def create_file(client: TestClient, project_id: int, filename: str, batch_name: str = "台账批次"):
    response = client.post(
        f"/api/projects/{project_id}/imports",
        data={"batch_name": batch_name},
        files=[("files", (filename, b"%PDF-1.4\n%%EOF", "application/pdf"))],
    )
    assert response.status_code == 201
    return response.json()["id"], response.json()["files"][0]["id"]


def add_sheet(
    project_id: int,
    batch_id: int,
    file_id: int,
    page_no: int,
    drawing_no: str,
    drawing_name: str,
    discipline: str,
    status: str,
    trust_level: str,
    confidence_score: float,
) -> int:
    with SessionLocal() as db:
        sheet = DrawingSheet(
            project_id=project_id,
            batch_id=batch_id,
            file_id=file_id,
            page_no=page_no,
            drawing_no=drawing_no,
            drawing_name=drawing_name,
            discipline=discipline,
            version="A",
            status=status,
            review_status="unreviewed",
            trust_level=trust_level,
            confidence_score=confidence_score,
        )
        db.add(sheet)
        db.flush()
        sheet_id = sheet.id
        db.commit()
    return sheet_id


def add_issue(project_id: int, batch_id: int, file_id: int, sheet_id: int, severity: str, code: str):
    with SessionLocal() as db:
        db.add(
            DrawingIssue(
                project_id=project_id,
                batch_id=batch_id,
                file_id=file_id,
                sheet_id=sheet_id,
                issue_code=code,
                severity=severity,
                message=f"{code} message",
                suggestion="请后续复核。",
                status="open",
            )
        )
        db.commit()


def prepare_ledger(client: TestClient):
    project_id = create_project(client)
    batch_id, file_id = create_file(client, project_id, "建施-03_二层平面图.pdf")
    sheet_1 = add_sheet(project_id, batch_id, file_id, 1, "建施-03", "二层平面图", "建筑", "need_review", "B", 86)
    sheet_2 = add_sheet(project_id, batch_id, file_id, 2, "结施-02", "梁配筋图", "结构", "recognized", "A", 94)
    sheet_3 = add_sheet(project_id, batch_id, file_id, 3, "电施-04", "照明平面图", "电气", "failed", "D", 35)
    add_issue(project_id, batch_id, file_id, sheet_1, "warning", "VERSION_EMPTY")
    add_issue(project_id, batch_id, file_id, sheet_3, "error", "DRAWING_NO_EMPTY")
    add_issue(project_id, batch_id, file_id, sheet_3, "info", "OCR_TEXT_EMPTY")
    return project_id, batch_id, file_id, [sheet_1, sheet_2, sheet_3]


def test_sheets_returns_paginated_structure():
    with TestClient(app) as client:
        project_id, *_ = prepare_ledger(client)
        response = client.get(f"/api/projects/{project_id}/sheets")

    assert response.status_code == 200
    assert {"items", "total", "page", "page_size", "total_pages"}.issubset(response.json())


def test_keyword_searches_drawing_no_name_and_file_name():
    with TestClient(app) as client:
        project_id, *_ = prepare_ledger(client)
        by_no = client.get(f"/api/projects/{project_id}/sheets?keyword=电施-04").json()
        by_name = client.get(f"/api/projects/{project_id}/sheets?keyword=梁配筋").json()
        by_file = client.get(f"/api/projects/{project_id}/sheets?keyword=二层平面图.pdf").json()

    assert by_no["total"] == 1
    assert by_name["total"] == 1
    assert by_file["total"] == 3


def test_discipline_status_and_trust_filters_work():
    with TestClient(app) as client:
        project_id, *_ = prepare_ledger(client)
        discipline = client.get(f"/api/projects/{project_id}/sheets?discipline=建筑").json()
        status = client.get(f"/api/projects/{project_id}/sheets?status=recognized").json()
        trust = client.get(f"/api/projects/{project_id}/sheets?trust_level=D").json()

    assert discipline["total"] == 1
    assert status["items"][0]["status"] == "recognized"
    assert trust["items"][0]["trust_level"] == "D"


def test_issue_filters_work():
    with TestClient(app) as client:
        project_id, *_ = prepare_ledger(client)
        has_issue = client.get(f"/api/projects/{project_id}/sheets?has_issue=true").json()
        no_issue = client.get(f"/api/projects/{project_id}/sheets?has_issue=false").json()
        errors = client.get(f"/api/projects/{project_id}/sheets?issue_severity=error").json()

    assert has_issue["total"] == 2
    assert no_issue["total"] == 1
    assert errors["total"] == 1
    assert errors["items"][0]["error_count"] == 1


def test_pagination_works():
    with TestClient(app) as client:
        project_id, *_ = prepare_ledger(client)
        response = client.get(f"/api/projects/{project_id}/sheets?page=2&page_size=2").json()

    assert response["page"] == 2
    assert response["page_size"] == 2
    assert response["total"] == 3
    assert len(response["items"]) == 1


def test_sort_by_confidence_score_and_issue_count():
    with TestClient(app) as client:
        project_id, *_ = prepare_ledger(client)
        confidence = client.get(
            f"/api/projects/{project_id}/sheets?sort_by=confidence_score&sort_order=asc"
        ).json()
        issues = client.get(
            f"/api/projects/{project_id}/sheets?sort_by=issue_count&sort_order=desc"
        ).json()

    assert confidence["items"][0]["confidence_score"] == 35
    assert issues["items"][0]["issue_count"] == 2


def test_issue_counts_are_correct():
    with TestClient(app) as client:
        project_id, *_ = prepare_ledger(client)
        response = client.get(f"/api/projects/{project_id}/sheets?trust_level=D").json()

    item = response["items"][0]
    assert item["issue_count"] == 2
    assert item["error_count"] == 1
    assert item["warning_count"] == 0
    assert item["info_count"] == 1


def test_project_stats_include_ledger_counts():
    with TestClient(app) as client:
        project_id, *_ = prepare_ledger(client)
        response = client.get(f"/api/projects/{project_id}")

    stats = response.json()["stats"]
    assert stats["sheet_count"] == 3
    assert stats["need_review_count"] == 1
    assert stats["failed_count"] == 1
    assert stats["issue_count"] == 3
    assert stats["error_issue_count"] == 1
    assert stats["warning_issue_count"] == 1


def test_project_issues_filters_and_pagination():
    with TestClient(app) as client:
        project_id, *_ = prepare_ledger(client)
        response = client.get(f"/api/projects/{project_id}/issues?severity=error&status=open")

    assert response.status_code == 200
    assert response.json()["total"] == 1
    assert response.json()["items"][0]["severity"] == "error"


def test_no_sheets_returns_empty_items():
    with TestClient(app) as client:
        project_id = create_project(client, "空台账项目")
        response = client.get(f"/api/projects/{project_id}/sheets")

    assert response.status_code == 200
    assert response.json()["items"] == []
    assert response.json()["total"] == 0
