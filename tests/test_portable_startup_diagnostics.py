import logging
import socket
from pathlib import Path

import pytest

from scripts.local_launcher import (
    check_startup_requirements,
    is_port_in_use,
    setup_launcher_logging,
)


def test_startup_checks_detect_missing_frontend_dist(tmp_path: Path):
    (tmp_path / "backend").mkdir()
    (tmp_path / "backend" / "main.py").write_text("", encoding="utf-8")
    (tmp_path / "requirements.txt").write_text("", encoding="utf-8")

    checks = check_startup_requirements(tmp_path)

    assert any(check.error_code == "FRONTEND_DIST_NOT_FOUND" for check in checks)


def test_startup_checks_detect_bound_port(tmp_path: Path):
    (tmp_path / "backend").mkdir()
    (tmp_path / "backend" / "main.py").write_text("", encoding="utf-8")
    dist = tmp_path / "frontend" / "dist"
    dist.mkdir(parents=True)
    (dist / "index.html").write_text("", encoding="utf-8")
    (tmp_path / "requirements.txt").write_text("", encoding="utf-8")

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        try:
            sock.bind(("127.0.0.1", 0))
        except OSError as exc:
            if getattr(exc, "winerror", None) == 10055:
                pytest.skip("Windows socket buffer temporarily exhausted while reserving a probe port")
            raise
        sock.listen(1)
        port = sock.getsockname()[1]

        checks = check_startup_requirements(tmp_path, port=port)

    assert any(check.error_code == "PORT_8000_IN_USE" for check in checks)
    assert is_port_in_use(port) is False


def test_launcher_log_file_can_be_written(tmp_path: Path):
    logger = setup_launcher_logging(tmp_path)

    logger.info("diagnostic log probe")
    for handler in logger.handlers:
        handler.flush()

    log_path = tmp_path / "app_data" / "logs" / "local_launcher.log"
    assert log_path.is_file()
    assert "diagnostic log probe" in log_path.read_text(encoding="utf-8")


def test_check_environment_returns_structured_results(tmp_path: Path):
    checks = check_startup_requirements(tmp_path)

    assert checks
    assert all(hasattr(check, "status") for check in checks)
    assert any(check.label == "当前工作目录" for check in checks)
    assert any(check.label == "项目根目录" for check in checks)


def test_startup_checks_can_report_app_data_unwritable(monkeypatch, tmp_path: Path):
    import scripts.local_launcher as launcher

    def fail_probe(directory: Path, probe_name: str = ".launcher_write_check") -> None:
        if "temp" in directory.parts:
            raise OSError("denied")

    monkeypatch.setattr(launcher, "write_probe", fail_probe)

    checks = launcher.check_startup_requirements(tmp_path)

    assert any(check.error_code == "APP_DATA_NOT_WRITABLE" for check in checks)
