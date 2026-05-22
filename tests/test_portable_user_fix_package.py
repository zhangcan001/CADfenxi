from pathlib import Path

import pytest

from scripts.build_portable_package import (
    build_portable_package,
    package_name,
    validate_package_integrity,
)


USER_FIX_VERSION = "v0.4.4-portable-rc-fix"


def test_user_fix_package_version_and_docs_exist():
    root = Path(__file__).resolve().parents[1]

    summary = build_portable_package(root, version=USER_FIX_VERSION)
    package_dir = summary.package_dir

    assert package_dir.name == package_name(USER_FIX_VERSION)
    assert (package_dir / "README_本地使用说明.md").is_file()
    assert (package_dir / "docs" / "PORTABLE_USER_TEST_ISSUES_v0.4.4.md").is_file()
    assert USER_FIX_VERSION in (package_dir / "package_info.txt").read_text(encoding="utf-8")
    assert summary.integrity_ok is True


def test_package_integrity_detects_missing_required_file(tmp_path: Path):
    package_dir = tmp_path / "pkg"
    (package_dir / "backend").mkdir(parents=True)

    missing = validate_package_integrity(package_dir)

    assert package_dir / "start.bat" in missing
    assert package_dir / "frontend" / "dist" / "index.html" in missing


def test_build_package_fails_when_source_frontend_dist_missing(tmp_path: Path):
    (tmp_path / "backend").mkdir()
    (tmp_path / "recognizer").mkdir()
    (tmp_path / "docs").mkdir()
    (tmp_path / "scripts").mkdir()
    for script_name in ["local_launcher.py", "install_backend_deps.bat", "check_env.bat", "stop_local.bat"]:
        (tmp_path / "scripts" / script_name).write_text("", encoding="utf-8")
    for filename in ["requirements.txt", "README.md", "README_本地使用说明.md", "RELEASE_NOTES.md"]:
        (tmp_path / filename).write_text("", encoding="utf-8")

    with pytest.raises(FileNotFoundError):
        build_portable_package(tmp_path, version=USER_FIX_VERSION)
