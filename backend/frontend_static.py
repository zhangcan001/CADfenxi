from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from starlette.status import HTTP_404_NOT_FOUND


def _safe_static_file(dist_dir: Path, request_path: str) -> Path | None:
    candidate = (dist_dir / request_path).resolve()
    try:
        candidate.relative_to(dist_dir.resolve())
    except ValueError:
        return None
    return candidate if candidate.is_file() else None


def mount_frontend_static(app: FastAPI, dist_dir: Path) -> bool:
    """Serve a Vite build when frontend/dist exists, with SPA fallback."""
    dist_dir = dist_dir.resolve()
    index_file = dist_dir / "index.html"
    if not index_file.is_file():
        return False

    @app.get("/", include_in_schema=False)
    def frontend_index() -> FileResponse:
        return FileResponse(index_file)

    @app.get("/{full_path:path}", include_in_schema=False)
    def frontend_spa_fallback(full_path: str) -> FileResponse:
        if full_path == "" or full_path.startswith("api/"):
            raise HTTPException(status_code=HTTP_404_NOT_FOUND)

        static_file = _safe_static_file(dist_dir, full_path)
        if static_file is not None:
            return FileResponse(static_file)
        return FileResponse(index_file)

    return True
