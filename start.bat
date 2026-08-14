@echo off
setlocal
cd /d "%~dp0"

set PY=E:\python\python.exe

if not exist "%PY%" (
    echo [ERROR] Python not found: %PY%
    echo         Edit start.bat and set PY to your Python path.
    pause
    exit /b 1
)

"%PY%" main.py
if errorlevel 1 pause
endlocal
