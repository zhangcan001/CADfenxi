from fastapi.testclient import TestClient
from sqlalchemy import select

from backend.core.database import SessionLocal
from backend.main import app
from backend.models.field_evidence import FieldEvidence
from backend.models.field_value import FieldValue
from backend.models.recognition_candidate import RecognitionCandidate


def create_project_and_sheet(client: TestClient):
    project = client.post("/api/projects", json={"name": "融合测试项目"})
    assert project.status_code == 201
    project_id = project.json()["id"]
    upload = client.post(
        f"/api/projects/{project_id}/imports",
        data={"batch_name": "融合批次"},
        files=[("files", ("建施-03_二层平面图_A版_20260520.pdf", b"%PDF-1.4\n%%EOF", "application/pdf"))],
    )
    assert upload.status_code == 201
    batch_id = upload.json()["id"]
    with SessionLocal() as db:
        from backend.models.drawing_sheet import DrawingSheet

        sheet = DrawingSheet(
            project_id=project_id,
            batch_id=batch_id,
            file_id=upload.json()["files"][0]["id"],
            page_no=1,
            status="preprocessed",
            review_status="pending",
        )
        db.add(sheet)
        db.flush()
        sheet_id = sheet.id
        db.commit()
    return project_id, batch_id, upload.json()["files"][0]["id"], sheet_id


def add_candidate(
    project_id: int,
    batch_id: int,
    file_id: int,
    sheet_id: int,
    field_name: str,
    candidate_value: str,
    normalized_value: str | None,
    source_type: str,
    confidence: float,
):
    with SessionLocal() as db:
        db.add(
            RecognitionCandidate(
                project_id=project_id,
                batch_id=batch_id,
                file_id=file_id,
                sheet_id=sheet_id,
                field_name=field_name,
                candidate_value=candidate_value,
                normalized_value=normalized_value,
                source_type=source_type,
                confidence=confidence,
                raw_text=candidate_value,
                parser_name="test_parser",
                parser_version="1.0",
            )
        )
        db.commit()


def add_base_candidates(project_id: int, batch_id: int, file_id: int, sheet_id: int):
    add_candidate(project_id, batch_id, file_id, sheet_id, "drawing_no", "建施-03", "建施-03", "pdf_text", 85)
    add_candidate(project_id, batch_id, file_id, sheet_id, "drawing_no", "建施-03", "建施-03", "title_ocr", 75)
    add_candidate(project_id, batch_id, file_id, sheet_id, "drawing_name", "二层平面图", "二层平面图", "pdf_text", 80)
    add_candidate(project_id, batch_id, file_id, sheet_id, "discipline", "建筑", "建筑", "rule", 70)
    add_candidate(project_id, batch_id, file_id, sheet_id, "version", "A版", "A", "filename", 60)
    add_candidate(project_id, batch_id, file_id, sheet_id, "issue_date", "2026-05-20", "2026-05-20", "filename", 65)


def test_fuse_single_sheet_success_and_writes_values():
    with TestClient(app) as client:
        project_id, batch_id, file_id, sheet_id = create_project_and_sheet(client)
        add_base_candidates(project_id, batch_id, file_id, sheet_id)
        response = client.post(f"/api/sheets/{sheet_id}/fuse-fields")
        sheet = client.get(f"/api/sheets/{sheet_id}").json()

    assert response.status_code == 200
    assert len(response.json()["field_values"]) == 5
    assert sheet["drawing_no"] == "建施-03"
    assert sheet["drawing_name"] == "二层平面图"
    assert sheet["discipline"] == "建筑"


def test_field_values_and_evidence_are_written():
    with TestClient(app) as client:
        project_id, batch_id, file_id, sheet_id = create_project_and_sheet(client)
        add_base_candidates(project_id, batch_id, file_id, sheet_id)
        client.post(f"/api/sheets/{sheet_id}/fuse-fields")
        values = client.get(f"/api/sheets/{sheet_id}/field-values")
        evidence = client.get(f"/api/sheets/{sheet_id}/evidence")

    assert values.status_code == 200
    assert evidence.status_code == 200
    assert len(values.json()) == 5
    assert len(evidence.json()) > 0
    assert all(value["is_reviewed"] is False for value in values.json())


def test_confidence_score_and_trust_level_generated():
    with TestClient(app) as client:
        project_id, batch_id, file_id, sheet_id = create_project_and_sheet(client)
        add_base_candidates(project_id, batch_id, file_id, sheet_id)
        response = client.post(f"/api/sheets/{sheet_id}/fuse-fields")

    assert response.json()["confidence_score"] > 70
    assert response.json()["trust_level"] in ["B", "C"]


def test_missing_required_fields_generate_issues():
    with TestClient(app) as client:
        project_id, batch_id, file_id, sheet_id = create_project_and_sheet(client)
        add_candidate(project_id, batch_id, file_id, sheet_id, "discipline", "建筑", "建筑", "rule", 70)
        response = client.post(f"/api/sheets/{sheet_id}/fuse-fields")

    codes = {issue["issue_code"] for issue in response.json()["issues"]}
    assert "DRAWING_NO_EMPTY" in codes
    assert "DRAWING_NAME_EMPTY" in codes
    assert "VERSION_EMPTY" in codes


def test_invalid_issue_date_generates_issue():
    with TestClient(app) as client:
        project_id, batch_id, file_id, sheet_id = create_project_and_sheet(client)
        add_base_candidates(project_id, batch_id, file_id, sheet_id)
        add_candidate(project_id, batch_id, file_id, sheet_id, "issue_date", "2026-13-40", None, "title_ocr", 70)
        response = client.post(f"/api/sheets/{sheet_id}/fuse-fields")

    codes = {issue["issue_code"] for issue in response.json()["issues"]}
    assert "ISSUE_DATE_INVALID" in codes


def test_duplicate_drawing_no_generates_issue():
    with TestClient(app) as client:
        project_id, batch_id, file_id, sheet_1 = create_project_and_sheet(client)
        upload = client.post(
            f"/api/projects/{project_id}/imports",
            data={"batch_name": "重复图号批次"},
            files=[("files", ("建施-03_三层平面图_A版_20260520.pdf", b"%PDF-1.4\n%%EOF", "application/pdf"))],
        )
        assert upload.status_code == 201
        batch_2 = upload.json()["id"]
        file_2 = upload.json()["files"][0]["id"]
        with SessionLocal() as db:
            from backend.models.drawing_sheet import DrawingSheet

            sheet = DrawingSheet(
                project_id=project_id,
                batch_id=batch_2,
                file_id=file_2,
                page_no=1,
                status="preprocessed",
                review_status="pending",
            )
            db.add(sheet)
            db.flush()
            sheet_2 = sheet.id
            db.commit()
        add_base_candidates(project_id, batch_id, file_id, sheet_1)
        add_base_candidates(project_id, batch_2, file_2, sheet_2)
        client.post(f"/api/sheets/{sheet_1}/fuse-fields")
        response = client.post(f"/api/sheets/{sheet_2}/fuse-fields")

    codes = {issue["issue_code"] for issue in response.json()["issues"]}
    assert "DRAWING_NO_DUPLICATE" in codes


def test_candidate_conflict_generates_warning():
    with TestClient(app) as client:
        project_id, batch_id, file_id, sheet_id = create_project_and_sheet(client)
        add_base_candidates(project_id, batch_id, file_id, sheet_id)
        add_candidate(project_id, batch_id, file_id, sheet_id, "drawing_no", "结施-09", "结施-09", "filename", 70)
        response = client.post(f"/api/sheets/{sheet_id}/fuse-fields")

    codes = {issue["issue_code"] for issue in response.json()["issues"]}
    assert "FILENAME_PDFTEXT_CONFLICT" in codes


def test_project_issues_endpoint_and_filters():
    with TestClient(app) as client:
        project_id, batch_id, file_id, sheet_id = create_project_and_sheet(client)
        add_candidate(project_id, batch_id, file_id, sheet_id, "discipline", "建筑", "建筑", "rule", 70)
        client.post(f"/api/sheets/{sheet_id}/fuse-fields")
        response = client.get(f"/api/projects/{project_id}/issues?severity=error")

    assert response.status_code == 200
    assert all(issue["severity"] == "error" for issue in response.json()["items"])


def test_batch_fuse_fields_success():
    with TestClient(app) as client:
        project_id, batch_id, file_id, sheet_id = create_project_and_sheet(client)
        add_base_candidates(project_id, batch_id, file_id, sheet_id)
        response = client.post(f"/api/imports/{batch_id}/fuse-fields")

    assert response.status_code == 200
    assert response.json()["total_count"] >= 1
    assert response.json()["success_count"] >= 1


def test_repeated_fuse_does_not_stack_open_issues():
    with TestClient(app) as client:
        project_id, batch_id, file_id, sheet_id = create_project_and_sheet(client)
        add_candidate(project_id, batch_id, file_id, sheet_id, "discipline", "建筑", "建筑", "rule", 70)
        client.post(f"/api/sheets/{sheet_id}/fuse-fields")
        client.post(f"/api/sheets/{sheet_id}/fuse-fields")
        issues = client.get(f"/api/projects/{project_id}/issues?status=open").json()["items"]

    codes = [issue["issue_code"] for issue in issues if issue["sheet_id"] == sheet_id]
    assert codes.count("DRAWING_NO_EMPTY") == 1


def test_reviewed_field_value_is_not_overwritten():
    with TestClient(app) as client:
        project_id, batch_id, file_id, sheet_id = create_project_and_sheet(client)
        add_base_candidates(project_id, batch_id, file_id, sheet_id)
        with SessionLocal() as db:
            db.add(
                FieldValue(
                    project_id=project_id,
                    batch_id=batch_id,
                    file_id=file_id,
                    sheet_id=sheet_id,
                    field_name="drawing_no",
                    raw_value="人工图号",
                    normalized_value="人工图号",
                    display_value="人工图号",
                    final_source="manual",
                    confidence=100,
                    is_reviewed=True,
                )
            )
            db.commit()
        client.post(f"/api/sheets/{sheet_id}/fuse-fields")
        values = client.get(f"/api/sheets/{sheet_id}/field-values").json()

    reviewed = [value for value in values if value["field_name"] == "drawing_no" and value["is_reviewed"]]
    assert reviewed[0]["display_value"] == "人工图号"


def test_field_evidence_table_has_rows():
    with TestClient(app) as client:
        project_id, batch_id, file_id, sheet_id = create_project_and_sheet(client)
        add_base_candidates(project_id, batch_id, file_id, sheet_id)
        client.post(f"/api/sheets/{sheet_id}/fuse-fields")

    with SessionLocal() as db:
        assert db.scalar(select(FieldEvidence.id)) is not None
