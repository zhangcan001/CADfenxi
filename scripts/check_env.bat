@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0.."

echo 工程图纸智能台账识别系统 v1.5.1-fast-delivery-package-fix 环境检查
echo.

where python >nul 2>nul
if errorlevel 1 (
  echo [ERROR] Python not found
  echo 未检测到 Python，请先安装 Python 3.11+，并勾选 Add Python to PATH。
  pause
  exit /b 1
)

python scripts\local_launcher.py --check

pause

