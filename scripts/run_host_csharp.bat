@echo off
echo ========================================================
echo Starting RemoDesk Windows Host Agent...
echo ========================================================

cd /d "%~dp0\..\windows-host\RemoDesk.Host\bin\Debug\net8.0-windows10.0.19041.0"

if not exist "RemoDesk.Host.exe" (
    echo ERROR: RemoDesk.Host.exe not found!
    echo The C# host has not been compiled yet.
    echo Please build it first using Visual Studio or 'dotnet build'.
    pause
    exit /b 1
)

echo [INFO] Launching RemoDesk.Host.exe...
start "" "RemoDesk.Host.exe"
echo [INFO] RemoDesk Host Agent started successfully!
echo You can close this window. The Host Agent runs independently.
timeout /t 3
