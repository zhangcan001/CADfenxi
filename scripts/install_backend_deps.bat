@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0.."

where python >nul 2>nul
if errorlevel 1 (
  echo [ERROR] 未找到 Python。请先安装 Python 3.11+，并勾选 Add Python to PATH。
  pause
  exit /b 1
)

python -m pip --version >nul 2>nul
if errorlevel 1 (
  echo [ERROR] pip 不可用。请确认 Python / pip 是否正常。
  pause
  exit /b 1
)

if not exist "requirements.txt" (
  echo [ERROR] 未找到 requirements.txt。请确认便携包完整。
  pause
  exit /b 1
)

python -m pip install -r requirements.txt
if errorlevel 1 (
  echo [ERROR] 依赖安装失败，请检查网络连接，或确认 Python / pip 是否正常。
  pause
  exit /b 1
)

echo 依赖安装完成，可以运行 start.bat。
pause
