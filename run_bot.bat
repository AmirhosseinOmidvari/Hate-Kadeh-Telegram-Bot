@echo off
setlocal
cd /d "%~dp0"
call env\Scripts\activate.bat
python -m bot.main
