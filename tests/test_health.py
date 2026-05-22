from pathlib import Path

from fastapi.testclient import TestClient

from backend.core.config import settings
from backend.core.database import init_database
from backend.main import app


def test_app_can_be_imported():
    assert app.title == settings.app_name


def test_health_returns_200():
    with TestClient(app) as client:
        response = client.get("/api/health")

    assert response.status_code == 200


def test_health_status_is_ok():
    with TestClient(app) as client:
        response = client.get("/api/health")

    assert response.json() == {
        "status": "ok",
        "version": settings.version,
        "database": "ok",
        "storage": "ok",
    }


def test_sqlite_database_file_can_be_created():
    init_database()

    assert Path(settings.database_path).exists()


def test_app_data_directories_can_be_created():
    settings.ensure_storage()

    for directory in settings.storage_dirs:
        assert directory.exists()
        assert directory.is_dir()
