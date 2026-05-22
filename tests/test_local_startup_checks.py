import socket
from pathlib import Path

import pytest

from scripts.local_launcher import StartupError, check_frontend_dist, ensure_app_data, is_port_in_use


def test_app_data_directories_are_initialized(tmp_path: Path):
    created = ensure_app_data(tmp_path)

    assert (tmp_path / "app_data").is_dir()
    assert (tmp_path / "app_data" / "projects").is_dir()
    assert (tmp_path / "app_data" / "database").is_dir()
    assert (tmp_path / "app_data" / "logs").is_dir()
    assert (tmp_path / "app_data" / "temp").is_dir()
    assert all(path.exists() for path in created)


def test_check_frontend_dist_requires_index_html(tmp_path: Path):
    with pytest.raises(StartupError) as exc_info:
        check_frontend_dist(tmp_path)

    assert exc_info.value.error_code == "FRONTEND_DIST_NOT_FOUND"


def test_check_frontend_dist_accepts_built_frontend(tmp_path: Path):
    dist = tmp_path / "frontend" / "dist"
    dist.mkdir(parents=True)
    (dist / "index.html").write_text("ok", encoding="utf-8")

    assert check_frontend_dist(tmp_path) == dist


def test_is_port_in_use_detects_bound_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        sock.listen(1)
        port = sock.getsockname()[1]

        assert is_port_in_use(port) is True


def test_is_port_in_use_returns_false_for_free_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]

    assert is_port_in_use(port) is False
