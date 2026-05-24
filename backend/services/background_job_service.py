"""通用后台任务表辅助。

为 CAD 流水线等长任务提供 DB-backed 状态机：
- create_job 启动新 job（带锁防止 scope 重复）
- update_progress 写入进度
- mark_completed / mark_failed 收尾
- reset_orphaned_jobs 进程启动时清理残留 running
"""
from __future__ import annotations

import json
import logging
import threading
from datetime import UTC, datetime
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.core.database import SessionLocal
from backend.models.background_job import BackgroundJob
from backend.schemas.background_job import BackgroundJobStatus

logger = logging.getLogger(__name__)

_job_start_lock = threading.Lock()


def create_job(
    session: Session,
    *,
    job_type: str,
    scope_type: str,
    scope_id: int,
    total: int,
    payload: dict[str, Any] | None = None,
) -> BackgroundJob:
    """检查 scope 上无 running job 后插入新 row；否则抛 409。"""
    with _job_start_lock:
        active = find_active(session, job_type, scope_type, scope_id)
        if active is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "error_code": "BACKGROUND_JOB_RUNNING",
                    "message": f"该 {scope_type} 上已有进行中的 {job_type} 任务",
                },
            )
        job = BackgroundJob(
            job_type=job_type,
            scope_type=scope_type,
            scope_id=scope_id,
            status="running",
            total=total,
            processed=0,
            current_step=None,
            message=None,
            payload_json=json.dumps(payload, ensure_ascii=False) if payload is not None else None,
            result_summary_json=None,
            started_at=datetime.now(UTC),
            finished_at=None,
        )
        session.add(job)
        session.commit()
        session.refresh(job)
        return job


def find_active(
    session: Session, job_type: str, scope_type: str, scope_id: int
) -> BackgroundJob | None:
    return session.scalars(
        select(BackgroundJob)
        .where(BackgroundJob.job_type == job_type)
        .where(BackgroundJob.scope_type == scope_type)
        .where(BackgroundJob.scope_id == scope_id)
        .where(BackgroundJob.status == "running")
        .order_by(BackgroundJob.id.desc())
    ).first()


def find_latest(
    session: Session, job_type: str, scope_type: str, scope_id: int
) -> BackgroundJob | None:
    return session.scalars(
        select(BackgroundJob)
        .where(BackgroundJob.job_type == job_type)
        .where(BackgroundJob.scope_type == scope_type)
        .where(BackgroundJob.scope_id == scope_id)
        .order_by(BackgroundJob.id.desc())
    ).first()


def get_job(session: Session, job_id: int) -> BackgroundJob:
    job = session.get(BackgroundJob, job_id)
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="后台任务不存在")
    return job


def update_progress(
    session: Session,
    job_id: int,
    *,
    processed: int | None = None,
    current_step: str | None = None,
    message: str | None = None,
) -> None:
    try:
        job = session.get(BackgroundJob, job_id)
        if job is None:
            logger.warning("update_progress: job %s vanished", job_id)
            return
        if processed is not None:
            job.processed = processed
        if current_step is not None:
            job.current_step = current_step
        if message is not None:
            job.message = message[:500]
        session.commit()
    except Exception:
        logger.exception("update_progress failed job_id=%s", job_id)
        session.rollback()


def mark_completed(
    session: Session,
    job_id: int,
    *,
    message: str | None = None,
    result_summary: dict[str, Any] | None = None,
) -> None:
    try:
        job = session.get(BackgroundJob, job_id)
        if job is None:
            logger.warning("mark_completed: job %s vanished", job_id)
            return
        job.status = "completed"
        job.finished_at = datetime.now(UTC)
        if message is not None:
            job.message = message[:500]
        if result_summary is not None:
            job.result_summary_json = json.dumps(result_summary, ensure_ascii=False, default=_json_default)
        session.commit()
    except Exception:
        logger.exception("mark_completed failed job_id=%s", job_id)
        session.rollback()


def mark_failed(session: Session, job_id: int, *, message: str) -> None:
    try:
        job = session.get(BackgroundJob, job_id)
        if job is None:
            logger.warning("mark_failed: job %s vanished", job_id)
            return
        job.status = "failed"
        job.finished_at = datetime.now(UTC)
        job.message = message[:500]
        session.commit()
    except Exception:
        logger.exception("mark_failed failed job_id=%s", job_id)
        session.rollback()


def reset_orphaned_jobs() -> None:
    """启动时把残留 running 标记为 failed（进程被强杀后的清理）。"""
    session: Session = SessionLocal()
    try:
        running = session.scalars(
            select(BackgroundJob).where(BackgroundJob.status == "running")
        ).all()
        for job in running:
            job.status = "failed"
            job.finished_at = datetime.now(UTC)
            job.message = "进程重启，任务被中断"
        if running:
            session.commit()
            logger.info("Reset %s orphaned background jobs to failed", len(running))
    except Exception:
        logger.exception("reset_orphaned_jobs failed")
        session.rollback()
    finally:
        session.close()


def to_status(job: BackgroundJob) -> BackgroundJobStatus:
    summary: dict[str, Any] | None = None
    if job.result_summary_json:
        try:
            summary = json.loads(job.result_summary_json)
        except json.JSONDecodeError:
            logger.warning("result_summary_json invalid JSON job_id=%s", job.id)
    return BackgroundJobStatus(
        id=job.id,
        job_type=job.job_type,
        scope_type=job.scope_type,  # type: ignore[arg-type]
        scope_id=job.scope_id,
        status=job.status,  # type: ignore[arg-type]
        total=job.total,
        processed=job.processed,
        current_step=job.current_step,
        message=job.message,
        started_at=job.started_at,
        finished_at=job.finished_at,
        result_summary=summary,
    )


def _json_default(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.isoformat()
    raise TypeError(f"Object of type {type(value).__name__} is not JSON serializable")
