from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.models.recognition_run import RecognitionRun
from backend.schemas.recognition_run import RecognitionRunRead


def create_run(
    db: Session,
    *,
    project_id: int,
    batch_id: int,
    file_id: int | None,
    sheet_id: int,
    run_type: str,
    engine_name: str,
    engine_version: str,
    status: str,
    started_at: datetime,
    output_path: str | None = None,
    error_code: str | None = None,
    error_message: str | None = None,
) -> RecognitionRun:
    run = RecognitionRun(
        project_id=project_id,
        batch_id=batch_id,
        file_id=file_id,
        sheet_id=sheet_id,
        run_type=run_type,
        engine_name=engine_name,
        engine_version=engine_version,
        status=status,
        output_path=output_path,
        started_at=started_at,
        finished_at=datetime.now(UTC),
        error_code=error_code,
        error_message=error_message,
    )
    db.add(run)
    db.commit()
    db.refresh(run)
    return run


def list_sheet_runs(db: Session, sheet_id: int) -> list[RecognitionRunRead]:
    runs = db.scalars(
        select(RecognitionRun)
        .where(RecognitionRun.sheet_id == sheet_id)
        .order_by(RecognitionRun.created_at.desc(), RecognitionRun.id.desc())
    ).all()
    return [RecognitionRunRead.model_validate(run) for run in runs]
