@echo off
title RemoDesk Desktop Dashboard
echo ========================================================
echo          REMODESK DESKTOP DASHBOARD LAUNCHER
echo ========================================================
echo.

cd /d "%~dp0"
set "PYTHONPATH=%~dp0"

echo [1/2] Verifying Python and PySide6...
python -c "import PySide6" >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [INFO] Installing PySide6 desktop framework...
    python -m pip install PySide6
)

echo [2/2] Launching RemoDesk Commercial Desktop UI...
start "" python desktop_ui\main.py %*

echo.
echo RemoDesk Desktop UI launched successfully!
echo You can close this terminal window.
timeout /t 3 >nul
exit /b 0
