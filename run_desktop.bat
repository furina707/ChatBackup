@echo off
chcp 65001 >nul
title ChatBackup TUI Console

cd /d "%~dp0"

if exist "desktop\.venv\Scripts\python.exe" (
    set "PY_EXE=desktop\.venv\Scripts\python.exe"
) else (
    set "PY_EXE=python"
)

echo [*] 启动 ChatBackup 电脑端终端控制台...
"%PY_EXE%" run_desktop.py
if errorlevel 1 pause
