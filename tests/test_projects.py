from fastapi.testclient import TestClient

from backend.main import app


def test_create_project_success():
    with TestClient(app) as client:
        response = client.post(
            "/api/projects",
            json={"name": " 某住宅项目 ", "description": "一期施工图台账识别"},
        )

    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "某住宅项目"
    assert data["description"] == "一期施工图台账识别"
    assert data["status"] == "active"
    assert data["stats"]["sheet_count"] == 0


def test_create_project_blank_name_returns_validation_error():
    with TestClient(app) as client:
        response = client.post("/api/projects", json={"name": "   "})

    assert response.status_code == 422


def test_list_projects_success():
    with TestClient(app) as client:
        client.post("/api/projects", json={"name": "列表测试项目"})
        response = client.get("/api/projects")

    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_get_project_detail_success():
    with TestClient(app) as client:
        create_response = client.post("/api/projects", json={"name": "详情测试项目"})
        project_id = create_response.json()["id"]
        response = client.get(f"/api/projects/{project_id}")

    assert response.status_code == 200
    assert response.json()["id"] == project_id
    assert response.json()["last_opened_at"] is not None


def test_get_missing_project_returns_404():
    with TestClient(app) as client:
        response = client.get("/api/projects/999999")

    assert response.status_code == 404


def test_update_project_success():
    with TestClient(app) as client:
        create_response = client.post("/api/projects", json={"name": "更新前"})
        project_id = create_response.json()["id"]
        response = client.patch(
            f"/api/projects/{project_id}",
            json={"name": "更新后", "description": "说明已更新"},
        )

    assert response.status_code == 200
    assert response.json()["name"] == "更新后"
    assert response.json()["description"] == "说明已更新"


def test_delete_empty_project_success():
    with TestClient(app) as client:
        create_response = client.post("/api/projects", json={"name": "删除测试项目"})
        project_id = create_response.json()["id"]
        response = client.delete(f"/api/projects/{project_id}")
        detail_response = client.get(f"/api/projects/{project_id}")

    assert response.status_code == 204
    assert detail_response.status_code == 404


def test_delete_missing_project_returns_404():
    with TestClient(app) as client:
        response = client.delete("/api/projects/999999")

    assert response.status_code == 404
