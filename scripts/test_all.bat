@echo off
echo ========================================================
echo Running Full RemoDesk Test Suite...
echo ========================================================

cd /d "%~dp0\.."

echo.
echo [1/3] Running Backend and E2E Signaling Tests (Pytest)...
backend_venv\Scripts\python.exe -m pytest -o asyncio_mode=auto backend\tests
if %errorlevel% neq 0 (
    echo [ERROR] Backend tests failed.
    exit /b %errorlevel%
)

echo.
echo [2/3] Running Live Win32 SendInput and Desktop Capture Tests...
backend_venv\Scripts\python.exe windows-host\python-host\test_host_live.py
if %errorlevel% neq 0 (
    echo [ERROR] Live Host tests failed.
    exit /b %errorlevel%
)

echo.
echo [3/3] Compiling C# Windows Host Agent (.NET 8)...
if exist "%USERPROFILE%\.dotnet\dotnet.exe" (
    "%USERPROFILE%\.dotnet\dotnet.exe" build windows-host\RemoDesk.Host\RemoDesk.Host.csproj
) else (
    dotnet build windows-host\RemoDesk.Host\RemoDesk.Host.csproj
)
if %errorlevel% neq 0 (
    echo [ERROR] C# Host build failed.
    exit /b %errorlevel%
)

echo.
echo ========================================================
echo ALL REMODESK SYSTEM TESTS COMPLETED SUCCESSFULLY!
echo ========================================================
