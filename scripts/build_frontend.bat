@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0..\frontend"

where npm >nul 2>nul
if errorlevel 1 (
  echo [ERROR] 未找到 npm。请先安装 Node.js。
  pause
  exit /b 1
)

call npm install
if errorlevel 1 (
  echo [ERROR] npm install 失败。
  pause
  exit /b 1
)

call npm run build
if errorlevel 1 (
  echo [ERROR] 前端构建失败。
  pause
  exit /b 1
)

echo 前端构建完成，可以运行 start_local.bat。
pause
