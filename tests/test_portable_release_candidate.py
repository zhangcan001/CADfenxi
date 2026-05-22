from pathlib import Path

from scripts.build_portable_package import build_portable_package, package_name


RC_VERSION = "v0.4.3-portable-rc"


def test_release_candidate_package_structure_and_version():
    root = Path(__file__).resolve().parents[1]

    summary = build_portable_package(root, version=RC_VERSION)
    package_dir = summary.package_dir

    assert package_dir.name == package_name(RC_VERSION)
    assert RC_VERSION in package_dir.name
    assert (package_dir / "package_info.txt").read_text(encoding="utf-8").find(RC_VERSION) >= 0
    assert (package_dir / "start.bat").is_file()
    assert (package_dir / "stop.bat").is_file()
    assert (package_dir / "check_env.bat").is_file()
    assert (package_dir / "README_本地使用说明.md").is_file()
    assert (package_dir / "RELEASE_NOTES.md").is_file()
    assert (package_dir / "docs" / "RELEASE_CHECKLIST_v0.4.3-portable-rc.md").is_file()
    assert (package_dir / "frontend" / "dist" / "index.html").is_file()
    assert (package_dir / "backend" / "main.py").is_file()
    assert (package_dir / "recognizer").is_dir()
    assert (package_dir / "app_data" / "projects").is_dir()
    assert (package_dir / "app_data" / "database").is_dir()
    assert (package_dir / "app_data" / "logs").is_dir()
    assert (package_dir / "app_data" / "temp").is_dir()


def test_release_candidate_package_is_clean():
    root = Path(__file__).resolve().parents[1]
    package_dir = build_portable_package(root, version=RC_VERSION).package_dir

    forbidden_parts = {
        ".git",
        ".github",
        "__pycache__",
        ".pytest_cache",
        ".mypy_cache",
        ".ruff_cache",
        "node_modules",
        "src",
    }
    for path in package_dir.rglob("*"):
        parts = set(path.relative_to(package_dir).parts)
        assert not (parts & forbidden_parts)
        assert path.name not in {".env", ".env.local"}
        assert path.suffix not in {".pyc", ".pyo", ".log", ".tmp", ".bak", ".map"}

    assert [p.name for p in (package_dir / "app_data" / "projects").iterdir()] == [".gitkeep"]
    assert [p.name for p in (package_dir / "app_data" / "database").iterdir()] == [".gitkeep"]
