@echo off
chcp 65001 >nul
title ChatBackup TUI Console

cd /d "%~dp0"

if not exist "desktop\.venv\Scripts\python.exe" (
    echo [*] 正在初始化 Python 虚拟环境...
    python -m venv desktop\.venv
    desktop\.venv\Scripts\pip install -r desktop\requirements.txt
)

echo [*] 启动 ChatBackup 电脑端终端控制台...
desktop\.venv\Scripts\python desktop\main.py
pause
