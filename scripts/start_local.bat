@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0.."

echo 工程图纸智能台账识别系统 v1.5.1-fast-delivery-package-fix 本地启动
echo.

where python >nul 2>nul
if errorlevel 1 (
  echo [ERROR] 未找到 Python。请先安装 Python，并确认 python 已加入 PATH。
  pause
  exit /b 1
)

if not exist "frontend\dist\index.html" (
  echo [ERROR] frontend\dist 不存在或未构建。
  echo 请先运行 scripts\build_frontend.bat。
  pause
  exit /b 1
)

python -c "import socket; s=socket.socket(); s.settimeout(0.5); raise SystemExit(0 if s.connect_ex(('127.0.0.1', 8000)) else 1)"
if errorlevel 1 (
  echo [ERROR] 端口 8000 已被占用。
  echo 请关闭旧服务后重新启动，或手动修改启动脚本端口。
  pause
  exit /b 1
)

python scripts\local_launcher.py --port 8000
if errorlevel 1 (
  echo.
  echo [ERROR] 本地服务启动失败，请查看 app_data\logs\local_launcher.log。
)
pause

