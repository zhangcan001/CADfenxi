import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.api.cad import router as cad_router
from backend.api.cad_pipeline import router as cad_pipeline_router
from backend.api.backups import router as backups_router
from backend.api.candidates import router as candidates_router
from backend.api.data_health import router as data_health_router
from backend.api.exports import router as exports_router
from backend.api.fusion import router as fusion_router
from backend.api.health import router as health_router
from backend.api.imports import router as imports_router
from backend.api.issues import router as issues_router
from backend.api.projects import router as projects_router
from backend.api.recognition import router as recognition_router
from backend.api.review import router as review_router
from backend.api.sheets import router as sheets_router
from backend.api.title_crops import router as title_crops_router
from backend.core.config import settings
from backend.core.database import init_database
from backend.core.logging import setup_logging
from backend.frontend_static import mount_frontend_static


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings.ensure_storage()
    setup_logging()
    init_database()
    logging.getLogger(__name__).info("Application started")
    yield


app = FastAPI(title=settings.app_name, version=settings.version, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router)
app.include_router(projects_router)
app.include_router(backups_router)
app.include_router(data_health_router)
app.include_router(imports_router)
app.include_router(sheets_router)
app.include_router(cad_router)
app.include_router(cad_pipeline_router)
app.include_router(title_crops_router)
app.include_router(recognition_router)
app.include_router(candidates_router)
app.include_router(fusion_router)
app.include_router(issues_router)
app.include_router(review_router)
app.include_router(exports_router)

mount_frontend_static(app, settings.frontend_dist_dir)
