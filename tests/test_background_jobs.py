import pytest
from fastapi import HTTPException

from backend.core.database import SessionLocal, init_database
from backend.models.background_job import BackgroundJob
from backend.services import background_job_service


def _wipe_jobs() -> None:
    init_database()
    with SessionLocal() as session:
        session.query(BackgroundJob).delete()
        session.commit()


def test_create_job_inserts_running_row():
    _wipe_jobs()
    with SessionLocal() as session:
        job = background_job_service.create_job(
            session,
            job_type="cad_pipeline",
            scope_type="batch",
            scope_id=101,
            total=6,
            payload={"steps": ["convert_dwg"]},
        )

        assert job.id is not None
        assert job.status == "running"
        assert job.total == 6
        assert job.processed == 0
        assert job.finished_at is None
        assert job.payload_json is not None
        assert "convert_dwg" in job.payload_json


def test_create_job_duplicate_scope_returns_409():
    _wipe_jobs()
    with SessionLocal() as session:
        background_job_service.create_job(
            session,
            job_type="cad_pipeline",
            scope_type="batch",
            scope_id=202,
            total=6,
        )

        with pytest.raises(HTTPException) as excinfo:
            background_job_service.create_job(
                session,
                job_type="cad_pipeline",
                scope_type="batch",
                scope_id=202,
                total=6,
            )

    assert excinfo.value.status_code == 409
    assert excinfo.value.detail["error_code"] == "BACKGROUND_JOB_RUNNING"


def test_update_progress_increments_processed():
    _wipe_jobs()
    with SessionLocal() as session:
        job = background_job_service.create_job(
            session,
            job_type="cad_pipeline",
            scope_type="batch",
            scope_id=303,
            total=6,
        )
        background_job_service.update_progress(
            session, job.id, processed=3, current_step="parse_dxf", message="步骤 3/6：解析 DXF"
        )
        reloaded = session.get(BackgroundJob, job.id)

        assert reloaded.processed == 3
        assert reloaded.current_step == "parse_dxf"
        assert reloaded.message == "步骤 3/6：解析 DXF"
        assert reloaded.status == "running"


def test_mark_completed_sets_finished_at_and_summary():
    _wipe_jobs()
    with SessionLocal() as session:
        job = background_job_service.create_job(
            session,
            job_type="cad_pipeline",
            scope_type="batch",
            scope_id=404,
            total=6,
        )
        background_job_service.mark_completed(
            session,
            job.id,
            message="done",
            result_summary={"status": "success", "summary": {"parse_success": 2}},
        )
        reloaded = session.get(BackgroundJob, job.id)

        assert reloaded.status == "completed"
        assert reloaded.finished_at is not None
        assert reloaded.message == "done"
        assert reloaded.result_summary_json is not None

    status = background_job_service.to_status(reloaded)
    assert status.status == "completed"
    assert status.result_summary == {"status": "success", "summary": {"parse_success": 2}}


def test_mark_failed_sets_message():
    _wipe_jobs()
    with SessionLocal() as session:
        job = background_job_service.create_job(
            session,
            job_type="cad_pipeline",
            scope_type="batch",
            scope_id=505,
            total=6,
        )
        long_message = "x" * 1000
        background_job_service.mark_failed(session, job.id, message=long_message)
        reloaded = session.get(BackgroundJob, job.id)

        assert reloaded.status == "failed"
        assert reloaded.finished_at is not None
        assert reloaded.message is not None
        assert len(reloaded.message) == 500


def test_reset_orphaned_jobs_flips_running_to_failed():
    _wipe_jobs()
    with SessionLocal() as session:
        background_job_service.create_job(
            session,
            job_type="cad_pipeline",
            scope_type="batch",
            scope_id=606,
            total=6,
        )

    background_job_service.reset_orphaned_jobs()

    with SessionLocal() as session:
        job = session.query(BackgroundJob).filter(BackgroundJob.scope_id == 606).one()
        assert job.status == "failed"
        assert job.finished_at is not None
        assert job.message == "进程重启，任务被中断"


def test_find_active_scoped_by_job_type():
    _wipe_jobs()
    with SessionLocal() as session:
        background_job_service.create_job(
            session,
            job_type="cad_pipeline",
            scope_type="batch",
            scope_id=707,
            total=6,
        )

        same_scope_other_type = background_job_service.find_active(
            session, "ocr_titles", "batch", 707
        )
        same_type_other_scope = background_job_service.find_active(
            session, "cad_pipeline", "batch", 708
        )
        same_type_same_scope = background_job_service.find_active(
            session, "cad_pipeline", "batch", 707
        )

        assert same_scope_other_type is None
        assert same_type_other_scope is None
        assert same_type_same_scope is not None
        assert same_type_same_scope.scope_id == 707
