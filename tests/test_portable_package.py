from pathlib import Path

from scripts.build_portable_package import DEFAULT_VERSION, build_portable_package, package_name


def test_build_portable_package_creates_expected_structure():
    root = Path(__file__).resolve().parents[1]

    package_dir = build_portable_package(root).package_dir

    assert package_dir == root / "release" / package_name(DEFAULT_VERSION)
    assert package_dir.is_dir()
    assert (package_dir / "start.bat").is_file()
    assert (package_dir / "check_env.bat").is_file()
    assert (package_dir / "stop.bat").is_file()
    assert (package_dir / "README_本地使用说明.md").is_file()
    assert (package_dir / "README.md").is_file()
    assert (package_dir / "package_info.txt").is_file()
    assert (package_dir / "backend" / "main.py").is_file()
    assert (package_dir / "frontend" / "dist" / "index.html").is_file()
    assert (package_dir / "requirements.txt").is_file()
    assert (package_dir / "app_data" / "projects").is_dir()
    assert (package_dir / "app_data" / "database").is_dir()
    assert (package_dir / "app_data" / "logs").is_dir()
    assert (package_dir / "app_data" / "temp").is_dir()


def test_portable_package_excludes_heavy_or_sensitive_content():
    root = Path(__file__).resolve().parents[1]
    package_dir = build_portable_package(root).package_dir

    forbidden_parts = {
        ".git",
        "__pycache__",
        ".pytest_cache",
        ".mypy_cache",
        ".ruff_cache",
        "node_modules",
        "src",
    }
    for path in package_dir.rglob("*"):
        relative_parts = set(path.relative_to(package_dir).parts)
        assert not (relative_parts & forbidden_parts)
        assert path.suffix not in {".pyc", ".pyo", ".log", ".map", ".tmp", ".bak"}
        assert path.name not in {".env", ".env.local"}

    project_entries = list((package_dir / "app_data" / "projects").iterdir())
    assert [entry.name for entry in project_entries] == [".gitkeep"]
    assert not (package_dir / "app_data" / "database" / "app.db").exists()


def test_package_info_contains_portable_version():
    root = Path(__file__).resolve().parents[1]
    package_dir = build_portable_package(root).package_dir

    package_info = (package_dir / "package_info.txt").read_text(encoding="utf-8")

    assert DEFAULT_VERSION in package_info
    assert "启动入口：start.bat" in package_info
    assert "本包不内置 Python、Node、ODA File Converter" in package_info
    assert "Windows 便携版" in package_info
