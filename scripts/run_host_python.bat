@echo off
echo ========================================================
echo Starting RemoDesk Native Win32 Host Agent (Python)...
echo ========================================================

cd /d "%~dp0\..\windows-host\python-host"

if exist "..\..\backend_venv\Scripts\python.exe" (
    ..\..\backend_venv\Scripts\python.exe host_agent.py
) else (
    python host_agent.py
)
pause

