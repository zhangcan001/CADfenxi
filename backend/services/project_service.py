import logging
import shutil
from datetime import UTC, datetime
from pathlib import Path

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.core.config import settings
from backend.models.export_record import ExportRecord
from backend.models.project import Project
from backend.schemas.project import ProjectCreate, ProjectRead, ProjectStats, ProjectUpdate

logger = logging.getLogger(__name__)


def empty_stats() -> ProjectStats:
    return ProjectStats()


def project_to_read(project: Project, stats: ProjectStats | None = None) -> ProjectRead:
    return ProjectRead.model_validate(
        {
            "id": project.id,
            "name": project.name,
            "description": project.description,
            "status": project.status,
            "created_at": project.created_at,
            "updated_at": project.updated_at,
            "last_opened_at": project.last_opened_at,
            "stats": stats or empty_stats(),
        }
    )


def get_project_or_404(db: Session, project_id: int) -> Project:
    project = db.get(Project, project_id)
    if project is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="项目不存在",
        )
    return project


def create_project(db: Session, payload: ProjectCreate) -> ProjectRead:
    project = Project(name=payload.name, description=payload.description)
    db.add(project)
    db.commit()
    db.refresh(project)
    project_dir(project.id).mkdir(parents=True, exist_ok=True)
    return project_to_read(project)


def list_projects(db: Session) -> list[ProjectRead]:
    projects = db.scalars(select(Project).order_by(Project.updated_at.desc())).all()
    return [project_to_read(project, project_stats(db, project.id)) for project in projects]


def get_project_detail(db: Session, project_id: int) -> ProjectRead:
    project = get_project_or_404(db, project_id)
    project.last_opened_at = datetime.now(UTC)
    db.commit()
    db.refresh(project)
    return project_to_read(project, project_stats(db, project.id))


def update_project(db: Session, project_id: int, payload: ProjectUpdate) -> ProjectRead:
    project = get_project_or_404(db, project_id)
    project.name = payload.name
    project.description = payload.description
    project.updated_at = datetime.now(UTC)
    db.commit()
    db.refresh(project)
    return project_to_read(project, project_stats(db, project.id))


def delete_project(db: Session, project_id: int) -> None:
    project = get_project_or_404(db, project_id)
    if has_related_data(db, project_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="项目已有图纸数据，不能直接删除",
        )

    db.delete(project)
    db.commit()
    remove_project_dir(project_id)


def has_related_data(db: Session, project_id: int) -> bool:
    from backend.services.import_service import project_file_count
    from backend.services.project_stats_service import count_sheets

    has_exports = db.scalar(
        select(ExportRecord.id).where(ExportRecord.project_id == project_id).limit(1)
    )
    return project_file_count(db, project_id) > 0 or count_sheets(db, project_id) > 0 or has_exports is not None


def project_dir(project_id: int) -> Path:
    return settings.projects_dir / f"project_{project_id}"


def project_stats(db: Session, project_id: int) -> ProjectStats:
    from backend.services.project_stats_service import get_project_stats

    return get_project_stats(db, project_id)


def remove_project_dir(project_id: int) -> None:
    path = project_dir(project_id)
    if not path.exists():
        return
    try:
        shutil.rmtree(path)
    except OSError:
        logger.warning("Failed to remove empty project directory: %s", path, exc_info=True)
