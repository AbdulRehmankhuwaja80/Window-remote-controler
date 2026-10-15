@echo off
title RemoDesk Service Manager
echo ========================================================
echo          REMODESK REMOTE DESKTOP SYSTEM LAUNCHER
echo ========================================================
echo.
cd /d "%~dp0"

echo [1/2] Starting RemoDesk Gateway & Signaling Server...
python scripts\start_services.py

echo.
echo ========================================================
echo RemoDesk is RUNNING and ready for incoming connections!
echo Press any key to close this launcher window (services keep running in background).
echo ========================================================
pause
