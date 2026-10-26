@echo off
title RemoDesk — 1-Click Master Launcher
echo ========================================================
echo          REMODESK REMOTE DESKTOP SYSTEM LAUNCHER
echo ========================================================
echo.
cd /d "%~dp0"

:: 1. Start Services via python helper
python scripts\start_services.py

:: 2. Detect local Wi-Fi IP
set "LAN_IP=192.168.0.37"
for /f "tokens=4" %%a in ('route print ^| findstr 0.0.0.0 ^| findstr /v "127.0.0.1"') do (
    if not "%%a"=="" set "LAN_IP=%%a"
)

echo.
echo ========================================================
echo           REMODESK IS RUNNING AND READY!
echo ========================================================
echo.
echo   * Laptop Wi-Fi IP Address : http://%LAN_IP%:8000
echo   * Phone Download Page     : http://%LAN_IP%:8000/download
echo   * REST API Documentation  : http://127.0.0.1:8000/docs
echo.
echo ========================================================
echo   HOW DO YOU WANT TO USE THE PHONE UI?
echo ========================================================
echo   [1] Open Download Page in PC Browser (to view or download APK)
echo   [2] Launch Virtual Android Phone on PC Screen (no phone needed!)
echo   [3] Install directly to USB-connected Android phone
echo   [4] Keep services running in background and exit launcher
echo ========================================================
echo.

set /p choice="Select an option [1-4] (default: 4): "

if "%choice%"=="1" (
    start http://%LAN_IP%:8000/download
    goto end
)
if "%choice%"=="2" (
    call Launch_Phone_Emulator.bat
    goto end
)
if "%choice%"=="3" (
    call Install_To_Connected_Phone.bat
    goto end
)

:end
echo.
echo RemoDesk backend and host agent are running in the background.
timeout /t 5
