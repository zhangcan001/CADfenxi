from __future__ import annotations

import argparse
import logging
import socket
import subprocess
import sys
import time
import traceback
import urllib.error
import urllib.request
import webbrowser
from dataclasses import dataclass
from pathlib import Path


APP_VERSION = "v1.2-fast-import"
DEFAULT_PORT = 8000
HEALTH_TIMEOUT_SECONDS = 45
MIN_PYTHON_VERSION = (3, 11)


ERROR_MESSAGES = {
    "PYTHON_VERSION_TOO_LOW": "Python 版本过低。请安装 Python 3.11+，并勾选 Add Python to PATH。",
    "BACKEND_ENTRY_NOT_FOUND": "未找到 backend/main.py。请确认便携包完整。",
    "FRONTEND_DIST_NOT_FOUND": "未找到 frontend/dist/index.html。请确认便携包完整，或重新构建 portable 包。",
    "APP_DATA_NOT_WRITABLE": "app_data 目录不可写。请将软件放到有写入权限的目录，例如 D:\\工程图纸系统\\。",
    "DATABASE_DIR_NOT_WRITABLE": "app_data/database 目录不可写。请检查目录权限。",
    "PORT_8000_IN_USE": "启动端口已被占用。请先关闭旧的系统窗口，或结束占用该端口的进程后再启动。",
    "BACKEND_START_FAILED": "后端启动失败。请查看 app_data/logs/local_launcher.log。",
    "HEALTH_CHECK_TIMEOUT": "/api/health 在限定时间内不可访问，后端可能启动失败。",
    "BROWSER_OPEN_FAILED": "浏览器自动打开失败。请手动访问 http://127.0.0.1:8000。",
    "UNKNOWN_STARTUP_ERROR": "启动失败，发生未知错误。请查看 app_data/logs/local_launcher.log。",
}


@dataclass
class CheckResult:
    status: str
    label: str
    detail: str
    error_code: str | None = None


class StartupError(Exception):
    def __init__(self, error_code: str, detail: str | None = None):
        self.error_code = error_code
        self.detail = detail or ERROR_MESSAGES.get(error_code, error_code)
        super().__init__(self.detail)


def project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def write_probe(directory: Path, probe_name: str = ".launcher_write_check") -> None:
    directory.mkdir(parents=True, exist_ok=True)
    probe = directory / probe_name
    probe.write_text("ok", encoding="utf-8")
    probe.unlink(missing_ok=True)


def setup_launcher_logging(root: Path) -> logging.Logger:
    logs_dir = root / "app_data" / "logs"
    logger = logging.getLogger("local_launcher")
    logger.setLevel(logging.INFO)
    logger.handlers.clear()

    formatter = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(logging.Formatter("%(message)s"))
    logger.addHandler(console_handler)

    try:
        logs_dir.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(logs_dir / "local_launcher.log", encoding="utf-8")
    except OSError:
        logger.warning("无法写入 app_data/logs/local_launcher.log，将仅输出到启动窗口。")
    else:
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    return logger


def ensure_app_data(root: Path) -> list[Path]:
    required_dirs = [
        root / "app_data",
        root / "app_data" / "projects",
        root / "app_data" / "backups",
        root / "app_data" / "database",
        root / "app_data" / "logs",
        root / "app_data" / "temp",
    ]
    for directory in required_dirs:
        directory.mkdir(parents=True, exist_ok=True)
    write_probe(root / "app_data" / "temp")
    write_probe(root / "app_data" / "database")
    return required_dirs


def is_port_in_use(port: int, host: str = "127.0.0.1") -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.5)
        return sock.connect_ex((host, port)) == 0


def check_frontend_dist(root: Path) -> Path:
    index_file = root / "frontend" / "dist" / "index.html"
    if not index_file.is_file():
        raise StartupError("FRONTEND_DIST_NOT_FOUND")
    return index_file.parent


def check_startup_requirements(root: Path, port: int = DEFAULT_PORT) -> list[CheckResult]:
    checks: list[CheckResult] = []
    cwd = Path.cwd()
    checks.append(CheckResult("OK", "当前工作目录", str(cwd)))
    checks.append(CheckResult("OK", "项目根目录", str(root)))

    python_version = ".".join(str(part) for part in sys.version_info[:3])
    if sys.version_info >= MIN_PYTHON_VERSION:
        checks.append(CheckResult("OK", "Python", python_version))
    else:
        checks.append(CheckResult("ERROR", "Python", f"{python_version}，需要 3.11+", "PYTHON_VERSION_TOO_LOW"))

    try:
        subprocess.run(
            [sys.executable, "-m", "pip", "--version"],
            cwd=root,
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError):
        checks.append(CheckResult("ERROR", "pip", "不可用", "PYTHON_VERSION_TOO_LOW"))
    else:
        checks.append(CheckResult("OK", "pip", "可用"))

    required_files = [
        ("backend/main.py", root / "backend" / "main.py", "BACKEND_ENTRY_NOT_FOUND"),
        ("frontend/dist/index.html", root / "frontend" / "dist" / "index.html", "FRONTEND_DIST_NOT_FOUND"),
        ("requirements.txt", root / "requirements.txt", "BACKEND_START_FAILED"),
        ("package_info.txt", root / "package_info.txt", None),
    ]
    for label, path, error_code in required_files:
        if path.exists():
            checks.append(CheckResult("OK", label, "存在"))
        elif error_code is None:
            checks.append(CheckResult("WARN", label, "缺失，源码开发目录可忽略；正式便携包应包含该文件"))
        else:
            checks.append(CheckResult("ERROR", label, "缺失", error_code))

    path_text = str(root)
    if " " in path_text:
        checks.append(CheckResult("WARN", "路径空格", "当前路径包含空格，通常可正常运行，如遇问题请移动到 D:\\DrawingLedger\\"))
    if any("\u4e00" <= char <= "\u9fff" for char in path_text):
        checks.append(CheckResult("WARN", "中文路径", "当前路径包含中文，通常可正常运行，如遇问题请移动到较短英文路径"))

    try:
        write_probe(root / "app_data" / "temp")
    except OSError:
        checks.append(CheckResult("ERROR", "app_data", "不可写", "APP_DATA_NOT_WRITABLE"))
    else:
        checks.append(CheckResult("OK", "app_data", "可写"))

    try:
        write_probe(root / "app_data" / "database")
    except OSError:
        checks.append(CheckResult("ERROR", "app_data/database", "不可写", "DATABASE_DIR_NOT_WRITABLE"))
    else:
        checks.append(CheckResult("OK", "app_data/database", "可写"))

    if is_port_in_use(port):
        checks.append(CheckResult("ERROR", f"端口 {port}", f"已被占用，请关闭旧窗口或释放 {port} 端口", "PORT_8000_IN_USE"))
    else:
        checks.append(CheckResult("OK", f"端口 {port}", "空闲"))
    return checks


def check_environment(root: Path, port: int = DEFAULT_PORT) -> list[tuple[str, str, str]]:
    return [(check.status, check.label, check.detail) for check in check_startup_requirements(root, port)]


def print_environment_check(root: Path, port: int = DEFAULT_PORT) -> int:
    has_error = False
    for check in check_startup_requirements(root, port):
        error_part = f" error_code={check.error_code}" if check.error_code else ""
        print(f"[{check.status}] {check.label}: {check.detail}{error_part}")
        if check.status == "ERROR":
            has_error = True
    return 1 if has_error else 0


def first_startup_error(checks: list[CheckResult]) -> StartupError | None:
    for check in checks:
        if check.status == "ERROR" and check.error_code:
            return StartupError(check.error_code, check.detail)
    return None


def log_checks(logger: logging.Logger, checks: list[CheckResult]) -> None:
    for check in checks:
        message = "[%s] %s: %s" % (check.status, check.label, check.detail)
        if check.status == "ERROR":
            logger.error(message)
        elif check.status == "WARN":
            logger.warning(message)
        else:
            logger.info(message)


def wait_for_health(url: str, timeout_seconds: int = HEALTH_TIMEOUT_SECONDS) -> bool:
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=2) as response:
                if response.status == 200:
                    return True
        except (urllib.error.URLError, TimeoutError, OSError):
            time.sleep(1)
    return False


def start_backend(root: Path, port: int) -> subprocess.Popen:
    try:
        return subprocess.Popen(
            [
                sys.executable,
                "-m",
                "uvicorn",
                "backend.main:app",
                "--host",
                "127.0.0.1",
                "--port",
                str(port),
            ],
            cwd=root,
        )
    except OSError as exc:
        raise StartupError("BACKEND_START_FAILED", str(exc)) from exc


def log_startup_error(logger: logging.Logger, error: StartupError) -> None:
    logger.error("error_code=%s", error.error_code)
    logger.error(ERROR_MESSAGES.get(error.error_code, error.detail))
    if error.detail:
        logger.error("detail=%s", error.detail)


def run(port: int = DEFAULT_PORT) -> int:
    root = project_root()
    logger = setup_launcher_logging(root)
    logger.info("工程图纸智能台账识别系统 %s 本地启动器", APP_VERSION)
    logger.info("当前工作目录：%s", Path.cwd())
    logger.info("项目根目录：%s", root)

    process: subprocess.Popen | None = None
    try:
        checks = check_startup_requirements(root, port)
        log_checks(logger, checks)
        startup_error = first_startup_error(checks)
        if startup_error is not None:
            raise startup_error

        process = start_backend(root, port)
        health_url = f"http://127.0.0.1:{port}/api/health"
        app_url = f"http://127.0.0.1:{port}"

        logger.info("正在等待后端启动：%s", health_url)
        if not wait_for_health(health_url):
            raise StartupError("HEALTH_CHECK_TIMEOUT")
        logger.info("/api/health 启动成功。")

        try:
            browser_opened = webbrowser.open(app_url)
        except Exception as exc:
            logger.error("浏览器自动打开异常。")
            logger.error(traceback.format_exc())
            raise StartupError("BROWSER_OPEN_FAILED", str(exc)) from exc
        if not browser_opened:
            logger.warning("浏览器未确认打开，请手动访问：%s", app_url)
        else:
            logger.info("浏览器已尝试打开：%s", app_url)

        logger.info("系统已启动。")
        logger.info("请不要关闭此窗口。")
        logger.info("关闭窗口将停止本地服务。")
        return process.wait()
    except StartupError as exc:
        log_startup_error(logger, exc)
        return 1
    except KeyboardInterrupt:
        logger.info("收到停止请求，正在关闭本地服务。")
        return 0
    except Exception:
        logger.error("error_code=UNKNOWN_STARTUP_ERROR")
        logger.error(ERROR_MESSAGES["UNKNOWN_STARTUP_ERROR"])
        logger.error(traceback.format_exc())
        return 1
    finally:
        if process is not None and process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)


def main() -> int:
    parser = argparse.ArgumentParser(description=f"{APP_VERSION} local launcher")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--check", action="store_true", help="check portable runtime environment")
    args = parser.parse_args()
    if args.check:
        return print_environment_check(project_root(), args.port)
    return run(args.port)


if __name__ == "__main__":
    raise SystemExit(main())

