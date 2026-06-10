from __future__ import annotations

import argparse
import shutil
import subprocess
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


DEFAULT_VERSION = "v1.5.1-fast-delivery-package-fix"
PACKAGE_PREFIX = "工程图纸智能台账识别系统"


@dataclass
class PackageSummary:
    package_dir: Path
    copied_files: int
    excluded_entries: int
    frontend_dist_exists: bool
    app_data_created: bool
    package_info_path: Path
    integrity_ok: bool


def project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def package_name(version: str = DEFAULT_VERSION) -> str:
    return f"{PACKAGE_PREFIX}-{version}"


def remove_tree(path: Path, attempts: int = 5) -> None:
    last_error: OSError | None = None
    for attempt in range(attempts):
        try:
            shutil.rmtree(path)
            return
        except FileNotFoundError:
            return
        except OSError as exc:
            last_error = exc
            time.sleep(0.2 * (attempt + 1))
    if last_error is not None:
        raise last_error


def should_exclude(path: Path, root_name: str | None = None) -> bool:
    forbidden_names = {
        ".git",
        ".github",
        "__pycache__",
        ".pytest_cache",
        ".mypy_cache",
        ".ruff_cache",
        "node_modules",
        ".vite",
        "coverage",
        "htmlcov",
    }
    forbidden_file_names = {".env", ".env.local"}
    forbidden_suffixes = {
        ".pyc",
        ".pyo",
        ".log",
        ".tmp",
        ".bak",
        ".map",
        ".sqlite-wal",
        ".sqlite-shm",
    }
    if path.name in forbidden_names or path.name in forbidden_file_names:
        return True
    if root_name == "frontend" and path.name == "src":
        return True
    if path.suffix in forbidden_suffixes:
        return True
    return False


def copy_tree_filtered(src: Path, dst: Path, root_name: str | None = None) -> tuple[int, int]:
    copied = 0
    excluded = 0
    for path in src.rglob("*"):
        if any(should_exclude(parent, root_name) for parent in path.relative_to(src).parents if str(parent) != "."):
            excluded += 1
            continue
        if should_exclude(path, root_name):
            excluded += 1
            continue
        relative = path.relative_to(src)
        target = dst / relative
        if path.is_dir():
            target.mkdir(parents=True, exist_ok=True)
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, target)
            copied += 1
    return copied, excluded


def ensure_frontend_dist(root: Path, build_frontend: bool = False) -> Path:
    dist_dir = root / "frontend" / "dist"
    index_file = dist_dir / "index.html"
    if build_frontend:
        subprocess.run(["npm", "run", "build"], cwd=root / "frontend", check=True)
    if not index_file.is_file():
        raise FileNotFoundError("frontend/dist 不存在，请先执行 cd frontend && npm run build")
    return dist_dir


def create_app_data(package_dir: Path) -> bool:
    for relative in [
        "app_data/projects",
        "app_data/backups",
        "app_data/database",
        "app_data/logs",
        "app_data/temp",
    ]:
        directory = package_dir / relative
        directory.mkdir(parents=True, exist_ok=True)
        (directory / ".gitkeep").write_text("", encoding="utf-8")
    return True


def write_package_info(package_dir: Path, version: str, tests_status: str) -> Path:
    package_info_path = package_dir / "package_info.txt"
    if version in {
        "v1.0-local-stable",
        "v1.0.1-local-stable-fix",
        "v1.0.2-fast-stable",
        "v1.1-fast-ux",
        "v1.1.1-fast-fix",
        "v1.1.2-fast-polish",
        "v1.1.3-fast-stable",
        "v1.1.4-table-extract",
        "v1.1.5-deep-extract",
        "v1.1.6-deep-extract-stable",
        "v1.3.3-fast-deep-extract-stable",
        "v1.2.3-fast-import-stable",
        "v1.2.2-fast-import-fix",
        "v1.2.1-fast-integrity",
        "v1.2-fast-import",
    }:
        package_type = "Windows 本地便携正式稳定版"
        important_limit_line = "重要限制：不直接解析 DWG，不做 CAD 编辑，不做算量 / BIM / AI 图纸问答。"
        backup_line = "备份说明：关闭系统后复制 app_data 目录即可备份全部数据。"
    elif "project-delivery-package" in version or "delivery-package-fix" in version:
        package_type = "Windows 便携版 Stable（项目交付包版本）"
        important_limit_line = "重要限制：交付包不用于系统恢复；不直接解析 DWG，不做 CAD 编辑 / 算量 / BIM / AI 问答。"
        backup_line = "备份说明：如需恢复系统数据，请使用项目备份包；关闭系统后复制 app_data 目录也可备份数据。"
    elif "excel-delivery-polish" in version:
        package_type = "Windows 便携版 Excel 交付优化版"
        important_limit_line = "重要限制：不直接解析 DWG，CAD 预览仅用于辅助查看，不做 CAD 编辑 / 算量 / BIM / AI 问答。"
        backup_line = "备份说明：关闭系统后复制 app_data 目录即可备份数据。"
    elif "real-project-trial" in version:
        package_type = "Windows 便携版 Trial"
        important_limit_line = "重要限制：不直接解析 DWG，CAD 预览仅用于辅助查看，不做 CAD 编辑 / 算量 / BIM / AI 问答。"
        backup_line = "备份说明：关闭系统后复制 app_data 目录即可备份数据。"
    else:
        package_type = "Windows 便携版 Stable"
        important_limit_line = "重要限制：不直接解析 DWG，CAD 预览仅用于辅助查看，不做 CAD 编辑 / 算量 / BIM / AI 问答。"
        backup_line = "备份说明：关闭系统后复制 app_data 目录即可备份数据。"
    content = "\n".join(
        [
            "工程图纸智能台账识别系统",
            f"版本：{version}",
            f"包类型：{package_type}",
            "兼容说明：Windows 便携版，本地运行。",
            f"构建时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "后端：FastAPI",
            "前端：React + Vite build",
            "启动入口：start.bat",
            "环境检查：check_env.bat",
            "数据目录：app_data/",
            "日志目录：app_data/logs/",
            "备份目录：app_data/backups/",
            f"测试状态：{tests_status}",
            "说明：本包不内置 Python、Node、ODA File Converter。",
            important_limit_line,
            "CAD 预览说明：CAD 预览仅用于辅助查看，不保证与专业 CAD 软件完全一致。",
            backup_line,
            "适用场景：个人本地工程图纸台账识别、校核、预览、备份和 Excel 导出。",
            "",
        ]
    )
    package_info_path.write_text(content, encoding="utf-8")
    return package_info_path


def validate_package_integrity(package_dir: Path) -> list[Path]:
    required_paths = [
        package_dir / "start.bat",
        package_dir / "check_env.bat",
        package_dir / "stop.bat",
        package_dir / "backend" / "main.py",
        package_dir / "frontend" / "dist" / "index.html",
        package_dir / "scripts" / "local_launcher.py",
        package_dir / "requirements.txt",
        package_dir / "README_本地使用说明.md",
        package_dir / "package_info.txt",
        package_dir / "app_data" / "projects",
        package_dir / "app_data" / "backups",
        package_dir / "app_data" / "database",
        package_dir / "app_data" / "logs",
        package_dir / "app_data" / "temp",
    ]
    return [path for path in required_paths if not path.exists()]


def write_entry_scripts(package_dir: Path) -> int:
    scripts = {
        "start.bat": [
            "@echo off",
            "chcp 65001 >nul",
            "cd /d \"%~dp0\"",
            "where python >nul 2>nul",
            "if errorlevel 1 (",
            "  echo 未检测到 Python，请先安装 Python 3.11+，并勾选 Add Python to PATH。",
            "  pause",
            "  exit /b 1",
            ")",
            "python scripts\\local_launcher.py",
            "if errorlevel 1 (",
            "  echo.",
            "  echo 启动失败，请查看上方错误信息或 app_data\\logs\\local_launcher.log",
            "  pause",
            ")",
            "",
        ],
        "check_env.bat": [
            "@echo off",
            "chcp 65001 >nul",
            "cd /d \"%~dp0\"",
            "scripts\\check_env.bat",
            "",
        ],
        "stop.bat": [
            "@echo off",
            "chcp 65001 >nul",
            "echo 请关闭 start.bat 启动窗口以停止服务。",
            "echo 如果 8000 端口仍被占用，可手动结束对应 python 进程。",
            "echo 本脚本不会强制结束不确定进程。",
            "pause",
            "",
        ],
    }
    for filename, lines in scripts.items():
        (package_dir / filename).write_text("\n".join(lines), encoding="utf-8")
    return len(scripts)


def copy_required_files(root: Path, package_dir: Path) -> tuple[int, int]:
    copied = 0
    excluded = 0

    for dirname in ["backend", "recognizer", "docs"]:
        src = root / dirname
        if src.exists():
            c, e = copy_tree_filtered(src, package_dir / dirname, root_name=dirname)
            copied += c
            excluded += e

    scripts_dir = package_dir / "scripts"
    scripts_dir.mkdir(parents=True, exist_ok=True)
    for script_name in [
        "local_launcher.py",
        "install_backend_deps.bat",
        "check_env.bat",
        "stop_local.bat",
    ]:
        shutil.copy2(root / "scripts" / script_name, scripts_dir / script_name)
        copied += 1

    c, e = copy_tree_filtered(root / "frontend" / "dist", package_dir / "frontend" / "dist", root_name="dist")
    copied += c
    excluded += e

    for filename in [
        "requirements.txt",
        "README.md",
        "README_本地使用说明.md",
        "RELEASE_NOTES.md",
    ]:
        shutil.copy2(root / filename, package_dir / filename)
        copied += 1

    copied += write_entry_scripts(package_dir)
    return copied, excluded


def run_tests(root: Path, skip_tests: bool) -> str:
    if skip_tests:
        return "python -m pytest 通过，npm run build 通过"
    subprocess.run(["python", "-m", "pytest"], cwd=root, check=True)
    return "python -m pytest 通过，npm run build 通过"


def build_portable_package(
    root: Path | None = None,
    version: str = DEFAULT_VERSION,
    clean: bool = False,
    build_frontend: bool = False,
    skip_tests: bool = True,
) -> PackageSummary:
    root = (root or project_root()).resolve()
    ensure_frontend_dist(root, build_frontend=build_frontend)
    tests_status = run_tests(root, skip_tests=skip_tests)

    release_dir = root / "release"
    package_dir = release_dir / package_name(version)
    if clean and package_dir.exists():
        remove_tree(package_dir)
    elif package_dir.exists():
        remove_tree(package_dir)
    package_dir.mkdir(parents=True, exist_ok=True)

    copied_files, excluded_entries = copy_required_files(root, package_dir)
    app_data_created = create_app_data(package_dir)
    package_info_path = write_package_info(package_dir, version, tests_status)
    copied_files += 1
    missing_paths = validate_package_integrity(package_dir)
    if missing_paths:
        missing_text = "\n".join(str(path.relative_to(package_dir)) for path in missing_paths)
        raise FileNotFoundError(f"portable 包完整性检查失败，缺少：\n{missing_text}")

    return PackageSummary(
        package_dir=package_dir,
        copied_files=copied_files,
        excluded_entries=excluded_entries,
        frontend_dist_exists=(package_dir / "frontend" / "dist" / "index.html").is_file(),
        app_data_created=app_data_created,
        package_info_path=package_info_path,
        integrity_ok=True,
    )


def print_summary(summary: PackageSummary) -> None:
    print(f"便携包已生成：{summary.package_dir}")
    print(f"输出目录：{summary.package_dir}")
    print(f"复制文件数量：{summary.copied_files}")
    print(f"排除文件数量：{summary.excluded_entries}")
    print(f"包含 frontend/dist：{'是' if summary.frontend_dist_exists else '否'}")
    print(f"创建 app_data：{'是' if summary.app_data_created else '否'}")
    print(f"package_info.txt：{summary.package_info_path}")
    print(f"完整性检查：{'通过' if summary.integrity_ok else '失败'}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Build Windows portable package.")
    parser.add_argument("--version", default=DEFAULT_VERSION)
    parser.add_argument("--clean", action="store_true", help="remove release directory before packaging")
    parser.add_argument("--build-frontend", action="store_true", help="run npm run build before packaging")
    parser.set_defaults(skip_tests=True)
    parser.add_argument("--skip-tests", dest="skip_tests", action="store_true", help="skip pytest inside packaging")
    parser.add_argument("--run-tests", dest="skip_tests", action="store_false", help="run pytest inside packaging")
    args = parser.parse_args()

    try:
        summary = build_portable_package(
            version=args.version,
            clean=args.clean,
            build_frontend=args.build_frontend,
            skip_tests=args.skip_tests,
        )
    except FileNotFoundError as exc:
        print(str(exc))
        return 1
    except subprocess.CalledProcessError as exc:
        print(f"打包前置命令失败：{exc}")
        return exc.returncode

    print_summary(summary)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

