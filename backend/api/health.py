from fastapi import APIRouter

from backend.core.config import settings
from backend.core.database import check_database

router = APIRouter(prefix="/api", tags=["health"])


@router.get("/health")
def health_check() -> dict[str, str]:
    return {
        "status": "ok",
        "version": settings.version,
        "database": "ok" if check_database() else "error",
        "storage": "ok" if settings.check_storage() else "error",
    }
