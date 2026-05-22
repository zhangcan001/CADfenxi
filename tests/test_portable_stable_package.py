from pathlib import Path

from scripts.build_portable_package import build_portable_package, package_name


STABLE_VERSION = "v0.4.5-portable-stable"


def test_stable_package_structure_and_docs():
    root = Path(__file__).resolve().parents[1]

    summary = build_portable_package(root, version=STABLE_VERSION, clean=True)
    package_dir = summary.package_dir

    assert package_dir.name == package_name(STABLE_VERSION)
    assert STABLE_VERSION in package_dir.name
    assert summary.frontend_dist_exists is True
    assert summary.app_data_created is True
    assert summary.integrity_ok is True
    assert (package_dir / "README_本地使用说明.md").is_file()
    assert (package_dir / "README.md").is_file()
    assert (package_dir / "RELEASE_NOTES.md").is_file()
    assert (package_dir / "docs" / "archive" / "RELEASE_CHECKLIST_v0.4.5-portable-stable.md").is_file()
    assert (package_dir / "docs" / "archive" / "FINAL_ACCEPTANCE_v0.4.5-portable-stable.md").is_file()
    assert (package_dir / "start.bat").is_file()
    assert (package_dir / "stop.bat").is_file()
    assert (package_dir / "check_env.bat").is_file()
    assert (package_dir / "scripts" / "local_launcher.py").is_file()
    assert (package_dir / "frontend" / "dist" / "index.html").is_file()
    assert (package_dir / "backend" / "main.py").is_file()
    assert (package_dir / "recognizer").is_dir()
    assert (package_dir / "app_data" / "projects").is_dir()
    assert (package_dir / "app_data" / "database").is_dir()
    assert (package_dir / "app_data" / "logs").is_dir()
    assert (package_dir / "app_data" / "temp").is_dir()


def test_stable_package_info_contains_required_release_metadata():
    root = Path(__file__).resolve().parents[1]
    package_dir = build_portable_package(root, version=STABLE_VERSION).package_dir

    package_info = (package_dir / "package_info.txt").read_text(encoding="utf-8")

    required_lines = [
        "工程图纸智能台账识别系统",
        f"版本：{STABLE_VERSION}",
        "包类型：Windows 便携版 Stable",
        "后端：FastAPI",
        "前端：React + Vite build",
        "启动入口：start.bat",
        "环境检查：check_env.bat",
        "数据目录：app_data/",
        "日志目录：app_data/logs/",
        "测试状态：python -m pytest 通过，npm run build 通过",
        "说明：本包不内置 Python、Node、ODA File Converter。",
        "重要限制：不直接解析 DWG，CAD 预览仅用于辅助查看，不做 CAD 编辑 / 算量 / BIM / AI 问答。",
        "备份说明：关闭系统后复制 app_data 目录即可备份数据。",
    ]
    for line in required_lines:
        assert line in package_info


def test_stable_user_docs_cover_backup_migration_troubleshooting_and_dwg():
    root = Path(__file__).resolve().parents[1]
    package_dir = build_portable_package(root, version=STABLE_VERSION).package_dir

    local_readme = (package_dir / "README_本地使用说明.md").read_text(encoding="utf-8")
    release_notes = (package_dir / "RELEASE_NOTES.md").read_text(encoding="utf-8")
    checklist = (package_dir / "docs" / "archive" / "RELEASE_CHECKLIST_v0.4.5-portable-stable.md").read_text(encoding="utf-8")
    acceptance = (package_dir / "docs" / "archive" / "FINAL_ACCEPTANCE_v0.4.5-portable-stable.md").read_text(encoding="utf-8")

    for keyword in [
        "Windows 10 / Windows 11",
        "Python 3.11+",
        "scripts\\install_backend_deps.bat",
        "app_data/",
        "备份方法",
        "迁移方法",
        "DWG 使用说明",
        "start.bat` 闪退",
        "8000 端口被占用",
        "local_launcher.log",
    ]:
        assert keyword in local_readme

    assert "# v0.4.5-portable-stable 发布说明" in release_notes
    assert "v0.4.5-portable-stable 是 Windows 便携版稳定发布包。" in release_notes
    assert "# v0.4.5-portable-stable 发布检查清单" in checklist
    assert "# v0.4.5-portable-stable 最终验收报告" in acceptance


def test_stable_package_is_clean():
    root = Path(__file__).resolve().parents[1]
    package_dir = build_portable_package(root, version=STABLE_VERSION).package_dir

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
    assert [p.name for p in (package_dir / "app_data" / "logs").iterdir()] == [".gitkeep"]
    assert [p.name for p in (package_dir / "app_data" / "temp").iterdir()] == [".gitkeep"]
    assert not (package_dir / "samples").exists()


def test_stable_release_keeps_portable_and_business_regression_tests_in_suite():
    root = Path(__file__).resolve().parents[1]

    regression_tests = [
        "tests/test_portable_package.py",
        "tests/test_portable_release_candidate.py",
        "tests/test_portable_user_fix_package.py",
        "tests/test_health.py",
        "tests/test_pdf_split.py",
        "tests/test_dxf_parse.py",
        "tests/test_dxf_candidates.py",
        "tests/test_dxf_fusion.py",
        "tests/test_dwg_conversion.py",
        "tests/test_dwg_to_dxf_integration.py",
        "tests/test_cad_pipeline.py",
        "tests/test_exports.py",
    ]
    for relative in regression_tests:
        assert (root / relative).is_file()
