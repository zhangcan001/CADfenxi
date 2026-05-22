from pathlib import Path

from fastapi import APIRouter, FastAPI
from fastapi.testclient import TestClient

from backend.frontend_static import mount_frontend_static


def build_test_app(dist_dir: Path) -> FastAPI:
    app = FastAPI()
    router = APIRouter(prefix="/api")

    @router.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    app.include_router(router)
    mount_frontend_static(app, dist_dir)
    return app


def test_frontend_dist_root_returns_index_html(tmp_path: Path):
    dist = tmp_path / "dist"
    dist.mkdir()
    (dist / "index.html").write_text("<div id=\"root\">local app</div>", encoding="utf-8")
    client = TestClient(build_test_app(dist))

    response = client.get("/")

    assert response.status_code == 200
    assert "local app" in response.text


def test_api_health_is_not_affected_by_static_fallback(tmp_path: Path):
    dist = tmp_path / "dist"
    dist.mkdir()
    (dist / "index.html").write_text("index", encoding="utf-8")
    client = TestClient(build_test_app(dist))

    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_frontend_route_falls_back_to_index_html(tmp_path: Path):
    dist = tmp_path / "dist"
    dist.mkdir()
    (dist / "index.html").write_text("spa index", encoding="utf-8")
    client = TestClient(build_test_app(dist))

    response = client.get("/projects/123/review")

    assert response.status_code == 200
    assert response.text == "spa index"


def test_static_asset_path_returns_file(tmp_path: Path):
    dist = tmp_path / "dist"
    assets = dist / "assets"
    assets.mkdir(parents=True)
    (dist / "index.html").write_text("index", encoding="utf-8")
    (assets / "app.js").write_text("console.log('ok');", encoding="utf-8")
    client = TestClient(build_test_app(dist))

    response = client.get("/assets/app.js")

    assert response.status_code == 200
    assert "console.log" in response.text


def test_unknown_api_path_does_not_return_index_html(tmp_path: Path):
    dist = tmp_path / "dist"
    dist.mkdir()
    (dist / "index.html").write_text("index", encoding="utf-8")
    client = TestClient(build_test_app(dist))

    response = client.get("/api/not-found")

    assert response.status_code == 404
