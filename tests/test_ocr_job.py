"""批量 OCR 任务状态机 + 超时保护单测。

直接调用 ocr_service 内部函数（同步部分），跳过线程化避免抖动；
对于多线程行为只验证：start 后 status=running 或 completed，再调度 worker 完成 → completed。
"""
from __future__ import annotations

import time

from fastapi import HTTPException
from fastapi.testclient import TestClient

from backend.core.database import SessionLocal
from backend.main import app
from backend.models.import_batch import ImportBatch
from backend.services import ocr_service
from tests.test_recognition_raw import _wait_for_ocr_job, prepare_sheet


def _prepare_batch_with_crops(client: TestClient, page_count: int = 2):
    _, batch_id, _ = prepare_sheet(client, page_count=page_count)
    crop = client.post(f"/api/imports/{batch_id}/title-crops")
    assert crop.status_code == 200, crop.text
    return batch_id


def test_start_ocr_batch_job_running_then_completed():
    with TestClient(app) as client:
        batch_id = _prepare_batch_with_crops(client, page_count=2)
        response = client.post(f"/api/imports/{batch_id}/ocr-titles")
        assert response.status_code == 200
        job = response.json()
        assert job["total"] == 2
        assert job["status"] in {"running", "completed"}

        final = _wait_for_ocr_job(client, batch_id)
        assert final["status"] == "completed"
        assert final["processed"] == 2
        assert final["success_count"] == 2
        assert final["failed_count"] == 0
        assert final["finished_at"] is not None


def test_get_ocr_batch_job_idle_when_no_run():
    with TestClient(app) as client:
        _, batch_id, _ = prepare_sheet(client, page_count=1)
        response = client.get(f"/api/imports/{batch_id}/ocr-job")
    assert response.status_code == 200
    job = response.json()
    assert job["status"] == "idle"
    assert job["total"] == 0
    assert job["processed"] == 0


def test_start_ocr_batch_returns_409_when_running():
    """同一 batch 在 running 时再次启动应返回 409。"""
    with TestClient(app) as client:
        batch_id = _prepare_batch_with_crops(client, page_count=2)
        # 手动把状态置成 running 模拟竞态
        with SessionLocal() as db:
            batch = db.get(ImportBatch, batch_id)
            assert batch is not None
            batch.ocr_job_status = "running"
            batch.ocr_job_total = 2
            batch.ocr_job_processed = 0
            db.commit()

        response = client.post(f"/api/imports/{batch_id}/ocr-titles")
        assert response.status_code == 409
        assert response.json()["detail"]["error_code"] == "OCR_JOB_RUNNING"


def test_start_ocr_batch_without_sheets_returns_400():
    with TestClient(app) as client:
        _, batch_id, _ = prepare_sheet(client, page_count=1)
        # 这个 batch 没生成 title_crop
        response = client.post(f"/api/imports/{batch_id}/ocr-titles")
    assert response.status_code == 400
    assert response.json()["detail"]["error_code"] == "NO_SHEETS_TO_OCR"


def test_reset_orphaned_ocr_jobs_marks_running_as_failed():
    with TestClient(app) as client:
        _, batch_id, _ = prepare_sheet(client, page_count=1)
        with SessionLocal() as db:
            batch = db.get(ImportBatch, batch_id)
            assert batch is not None
            batch.ocr_job_status = "running"
            batch.ocr_job_total = 5
            batch.ocr_job_processed = 2
            db.commit()

    ocr_service.reset_orphaned_ocr_jobs()

    with SessionLocal() as db:
        batch = db.get(ImportBatch, batch_id)
        assert batch is not None
        assert batch.ocr_job_status == "failed"
        assert batch.ocr_job_message == "进程重启，任务被中断"
        assert batch.ocr_job_finished_at is not None


def test_recognize_with_timeout_raises_runtimeerror():
    """单页 OCR 超时保护：mock 一个 sleep 长于 timeout 的 engine。"""
    class SlowEngine:
        engine_name = "slow"
        engine_version = "1.0"

        def recognize(self, image_path: str):  # noqa: ARG002
            time.sleep(2.0)
            return None

    original = ocr_service.OCR_PAGE_TIMEOUT_SECONDS
    ocr_service.OCR_PAGE_TIMEOUT_SECONDS = 1
    try:
        engine = SlowEngine()
        try:
            ocr_service._recognize_with_timeout(engine, "/tmp/nope.png")
        except RuntimeError as exc:
            assert "OCR_TIMEOUT" in str(exc)
        else:
            raise AssertionError("expected RuntimeError")
    finally:
        ocr_service.OCR_PAGE_TIMEOUT_SECONDS = original


def test_start_then_complete_increments_processed():
    """确认 worker 跑完后 processed == total。"""
    with TestClient(app) as client:
        batch_id = _prepare_batch_with_crops(client, page_count=3)
        client.post(f"/api/imports/{batch_id}/ocr-titles")
        final = _wait_for_ocr_job(client, batch_id)
    assert final["total"] == 3
    assert final["processed"] == 3
    assert final["status"] == "completed"


def test_409_does_not_include_http_exception_bubble():
    """HTTPException 路径不应让 _job_start_lock 死锁后续请求。"""
    with TestClient(app) as client:
        batch_id = _prepare_batch_with_crops(client, page_count=1)
        # 第一次成功
        first = client.post(f"/api/imports/{batch_id}/ocr-titles")
        assert first.status_code == 200
        # 立即第二次，多半还在 running
        second = client.post(f"/api/imports/{batch_id}/ocr-titles")
        if second.status_code == 409:
            assert second.json()["detail"]["error_code"] == "OCR_JOB_RUNNING"
        else:
            # 极快完成的话允许 200 + 新一轮 running
            assert second.status_code == 200

        # 等任意一轮 job 收尾
        _wait_for_ocr_job(client, batch_id)
