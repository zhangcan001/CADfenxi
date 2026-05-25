from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from backend.core.database import get_db
from backend.schemas.project import ProjectCreate, ProjectRead, ProjectUpdate, ProjectWorkbenchSummary
from backend.services import project_service, project_workbench_service

router = APIRouter(prefix="/api/projects", tags=["projects"])


@router.post("", response_model=ProjectRead, status_code=status.HTTP_201_CREATED)
def create_project(payload: ProjectCreate, db: Session = Depends(get_db)) -> ProjectRead:
    return project_service.create_project(db, payload)


@router.get("", response_model=list[ProjectRead])
def list_projects(db: Session = Depends(get_db)) -> list[ProjectRead]:
    return project_service.list_projects(db)


@router.get("/{project_id}", response_model=ProjectRead)
def get_project(project_id: int, db: Session = Depends(get_db)) -> ProjectRead:
    return project_service.get_project_detail(db, project_id)


@router.get("/{project_id}/workbench-summary", response_model=ProjectWorkbenchSummary)
def get_project_workbench_summary(
    project_id: int,
    db: Session = Depends(get_db),
) -> ProjectWorkbenchSummary:
    return project_workbench_service.get_workbench_summary(db, project_id)


@router.patch("/{project_id}", response_model=ProjectRead)
def update_project(
    project_id: int,
    payload: ProjectUpdate,
    db: Session = Depends(get_db),
) -> ProjectRead:
    return project_service.update_project(db, project_id, payload)


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_project(project_id: int, db: Session = Depends(get_db)) -> Response:
    project_service.delete_project(db, project_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
