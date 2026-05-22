from fastapi.testclient import TestClient
from sqlalchemy import select

from backend.core.database import SessionLocal
from backend.main import app
from backend.models.drawing_issue import DrawingIssue
from backend.models.drawing_sheet import DrawingSheet
from backend.models.field_value import FieldValue
from backend.models.recognition_candidate import RecognitionCandidate
from backend.models.review_audit_log import ReviewAuditLog


def prepare_sheet(client: TestClient):
    project = client.post("/api/projects", json={"name": "校核测试项目"})
    assert project.status_code == 201
    project_id = project.json()["id"]
    upload = client.post(
        f"/api/projects/{project_id}/imports",
        data={"batch_name": "校核批次"},
        files=[("files", ("review.pdf", b"%PDF-1.4\n%%EOF", "application/pdf"))],
    )
    assert upload.status_code == 201
    batch_id = upload.json()["id"]
    file_id = upload.json()["files"][0]["id"]
    with SessionLocal() as db:
        sheet = DrawingSheet(
            project_id=project_id,
            batch_id=batch_id,
            file_id=file_id,
            page_no=1,
            status="need_review",
            review_status="unreviewed",
            trust_level="A",
            confidence_score=90,
        )
        db.add(sheet)
        db.flush()
        sheet_id = sheet.id
        db.commit()
    return project_id, batch_id, file_id, sheet_id


def add_field(project_id: int, batch_id: int, file_id: int, sheet_id: int, field_name: str, value: str, reviewed: bool = False):
    with SessionLocal() as db:
        db.add(
            FieldValue(
                project_id=project_id,
                batch_id=batch_id,
                file_id=file_id,
                sheet_id=sheet_id,
                field_name=field_name,
                raw_value=value,
                normalized_value=value,
                display_value=value,
                final_source="manual" if reviewed else "pdf_text",
                confidence=100 if reviewed else 80,
                is_reviewed=reviewed,
            )
        )
        sheet = db.get(DrawingSheet, sheet_id)
        setattr(sheet, field_name, value)
        db.commit()


def add_core_fields(project_id: int, batch_id: int, file_id: int, sheet_id: int):
    add_field(project_id, batch_id, file_id, sheet_id, "drawing_no", "建施-03")
    add_field(project_id, batch_id, file_id, sheet_id, "drawing_name", "二层平面图")
    add_field(project_id, batch_id, file_id, sheet_id, "discipline", "建筑")


def add_candidate(project_id: int, batch_id: int, file_id: int, sheet_id: int):
    with SessionLocal() as db:
        candidate = RecognitionCandidate(
            project_id=project_id,
            batch_id=batch_id,
            file_id=file_id,
            sheet_id=sheet_id,
            field_name="drawing_no",
            candidate_value="建施-08",
            normalized_value="建施-08",
            source_type="title_ocr",
            confidence=75,
            raw_text="图号：建施-08",
            parser_name="test",
            parser_version="1.0",
        )
        db.add(candidate)
        db.flush()
        candidate_id = candidate.id
        db.commit()
    return candidate_id


def add_issue(project_id: int, batch_id: int, file_id: int, sheet_id: int, severity: str = "error"):
    with SessionLocal() as db:
        issue = DrawingIssue(
            project_id=project_id,
            batch_id=batch_id,
            file_id=file_id,
            sheet_id=sheet_id,
            issue_code="DRAWING_NO_EMPTY" if severity == "error" else "VERSION_EMPTY",
            severity=severity,
            message="测试问题",
            suggestion="请处理",
            status="open",
        )
        db.add(issue)
        db.flush()
        issue_id = issue.id
        db.commit()
    return issue_id


def test_update_sheet_fields_manual_drawing_no():
    with TestClient(app) as client:
        _, _, _, sheet_id = prepare_sheet(client)
        response = client.patch(
            f"/api/sheets/{sheet_id}/fields",
            json={"fields": {"drawing_no": "建施-03"}, "note": "人工校核修正"},
        )
        detail = client.get(f"/api/sheets/{sheet_id}").json()
        logs = client.get(f"/api/sheets/{sheet_id}/audit-logs").json()

    assert response.status_code == 200
    field = response.json()["updated_fields"][0]
    assert field["final_source"] == "manual"
    assert field["is_reviewed"] is True
    assert detail["drawing_no"] == "建施-03"
    assert any(log["action_type"] == "field_edit" for log in logs)


def test_adopt_candidate_success_and_audit():
    with TestClient(app) as client:
        project_id, batch_id, file_id, sheet_id = prepare_sheet(client)
        candidate_id = add_candidate(project_id, batch_id, file_id, sheet_id)
        response = client.post(
            f"/api/sheets/{sheet_id}/adopt-candidate",
            json={"candidate_id": candidate_id, "note": "采用 OCR 候选值"},
        )
        logs = client.get(f"/api/sheets/{sheet_id}/audit-logs").json()

    assert response.status_code == 200
    assert response.json()["field_value"]["display_value"] == "建施-08"
    assert response.json()["field_value"]["is_reviewed"] is True
    assert any(log["action_type"] == "candidate_adopted" for log in logs)


def test_confirm_sheet_success():
    with TestClient(app) as client:
        project_id, batch_id, file_id, sheet_id = prepare_sheet(client)
        add_core_fields(project_id, batch_id, file_id, sheet_id)
        response = client.post(f"/api/sheets/{sheet_id}/confirm", json={"force": False, "note": "确认"})
        detail = client.get(f"/api/sheets/{sheet_id}").json()

    assert response.status_code == 200
    assert detail["status"] == "confirmed"
    assert detail["review_status"] == "confirmed"
    with SessionLocal() as db:
        values = db.scalars(select(FieldValue).where(FieldValue.sheet_id == sheet_id)).all()
        assert all(value.is_reviewed for value in values)


def test_confirm_sheet_fails_with_open_error():
    with TestClient(app) as client:
        project_id, batch_id, file_id, sheet_id = prepare_sheet(client)
        add_core_fields(project_id, batch_id, file_id, sheet_id)
        add_issue(project_id, batch_id, file_id, sheet_id, "error")
        response = client.post(f"/api/sheets/{sheet_id}/confirm", json={"force": False})

    assert response.status_code == 400


def test_update_issue_status_resolved_ignored_and_audit():
    with TestClient(app) as client:
        project_id, batch_id, file_id, sheet_id = prepare_sheet(client)
        issue_id = add_issue(project_id, batch_id, file_id, sheet_id, "warning")
        resolved = client.patch(f"/api/issues/{issue_id}", json={"status": "resolved", "note": "已处理"})
        ignored = client.patch(f"/api/issues/{issue_id}", json={"status": "ignored", "note": "忽略"})
        logs = client.get(f"/api/sheets/{sheet_id}/audit-logs").json()

    assert resolved.status_code == 200
    assert resolved.json()["status"] == "resolved"
    assert ignored.json()["status"] == "ignored"
    assert any(log["action_type"] == "issue_resolved" for log in logs)
    assert any(log["action_type"] == "issue_ignored" for log in logs)


def test_audit_logs_endpoint_returns_records():
    with TestClient(app) as client:
        _, _, _, sheet_id = prepare_sheet(client)
        client.patch(f"/api/sheets/{sheet_id}/fields", json={"fields": {"drawing_no": "建施-03"}})
        response = client.get(f"/api/sheets/{sheet_id}/audit-logs")

    assert response.status_code == 200
    assert len(response.json()) >= 1


def test_batch_confirm_only_a_without_error():
    with TestClient(app) as client:
        project_id, batch_id, file_id, sheet_ok = prepare_sheet(client)
        add_core_fields(project_id, batch_id, file_id, sheet_ok)
        _, _, _, sheet_skip = prepare_sheet(client)
        with SessionLocal() as db:
            skip = db.get(DrawingSheet, sheet_skip)
            skip.project_id = project_id
            skip.trust_level = "C"
            db.commit()
        response = client.post(
            f"/api/projects/{project_id}/batch-confirm",
            json={"sheet_ids": [sheet_ok, sheet_skip], "note": "批量确认"},
        )

    assert response.status_code == 200
    assert response.json()["confirmed_count"] == 1
    assert response.json()["skipped"][0]["sheet_id"] == sheet_skip


def test_machine_fusion_does_not_overwrite_reviewed_field():
    with TestClient(app) as client:
        project_id, batch_id, file_id, sheet_id = prepare_sheet(client)
        add_field(project_id, batch_id, file_id, sheet_id, "drawing_no", "人工图号", reviewed=True)
        with SessionLocal() as db:
            db.add(
                RecognitionCandidate(
                    project_id=project_id,
                    batch_id=batch_id,
                    file_id=file_id,
                    sheet_id=sheet_id,
                    field_name="drawing_no",
                    candidate_value="建施-99",
                    normalized_value="建施-99",
                    source_type="pdf_text",
                    confidence=95,
                    raw_text="建施-99",
                    parser_name="test",
                    parser_version="1.0",
                )
            )
            db.commit()
        client.post(f"/api/sheets/{sheet_id}/fuse-fields")
        values = client.get(f"/api/sheets/{sheet_id}/field-values").json()

    reviewed = [value for value in values if value["field_name"] == "drawing_no" and value["is_reviewed"]]
    assert reviewed[0]["display_value"] == "人工图号"


def test_review_audit_log_table_written():
    with TestClient(app) as client:
        _, _, _, sheet_id = prepare_sheet(client)
        client.patch(f"/api/sheets/{sheet_id}/fields", json={"fields": {"drawing_no": "建施-03"}})

    with SessionLocal() as db:
        assert db.scalar(select(ReviewAuditLog.id).where(ReviewAuditLog.sheet_id == sheet_id)) is not None
