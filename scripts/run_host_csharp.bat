@echo off
echo ========================================================
echo Starting RemoDesk Windows Host Agent (.NET 8)...
echo ========================================================

cd /d "%~dp0\..\windows-host\RemoDesk.Host"

if exist "%USERPROFILE%\.dotnet\dotnet.exe" (
    set "DOTNET_CMD=%USERPROFILE%\.dotnet\dotnet.exe"
) else (
    set "DOTNET_CMD=dotnet"
)

echo [INFO] Running C# Host Agent...
"%DOTNET_CMD%" run --project RemoDesk.Host.csproj
pause
