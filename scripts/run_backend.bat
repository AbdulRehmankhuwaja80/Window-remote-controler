@echo off
echo ========================================================
echo Starting RemoDesk Signaling & Auth Gateway...
echo ========================================================

cd /d "%~dp0\.."

if not exist "backend_venv\Scripts\python.exe" (
    echo [INFO] Creating Python virtual environment...
    python -m venv backend_venv
    backend_venv\Scripts\python.exe -m pip install -r backend\requirements.txt
)

echo [INFO] Running Uvicorn server on http://0.0.0.0:8000
backend_venv\Scripts\python.exe -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload
pause
