@echo off
setlocal
cd /d "%~dp0"
call env\Scripts\activate.bat
uvicorn admin_panel.main:app --host 127.0.0.1 --port 8000 --reload --reload-dir admin_panel
