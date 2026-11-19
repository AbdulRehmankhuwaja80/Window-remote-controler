import subprocess
import time
import urllib.request
import os
import sys
import json

repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
venv_python = os.path.join(repo_root, "backend_venv", "Scripts", "python.exe")
if not os.path.exists(venv_python):
    venv_python = sys.executable

print("=== CHECKING REMODESK SERVICES ===")

# Check if backend is already running
backend_healthy = False
active_hosts = 0
try:
    with urllib.request.urlopen("http://127.0.0.1:8000/health", timeout=1) as resp:
        raw = resp.read().decode('utf-8')
        print(f"Backend is already running and healthy! ({raw})")
        backend_healthy = True
        data = json.loads(raw)
        active_hosts = data.get("active_hosts", 0)
except Exception:
    pass

# Ensure repo_root is on PYTHONPATH
env = dict(os.environ)
env["PYTHONPATH"] = repo_root + (os.pathsep + env["PYTHONPATH"] if "PYTHONPATH" in env else "")

logs_dir = os.path.join(repo_root, "logs")
os.makedirs(logs_dir, exist_ok=True)
backend_log = open(os.path.join(logs_dir, "backend.log"), "a", encoding="utf-8")

if not backend_healthy:
    print("=== STARTING REMODESK BACKEND ===")
    backend_cmd = [
        venv_python,
        "-m", "uvicorn",
        "backend.app.main:app",
        "--host", "0.0.0.0",
        "--port", "8000"
    ]

    proc = subprocess.Popen(
        backend_cmd,
        cwd=repo_root,
        env=env,
        stdout=backend_log,
        stderr=backend_log,
        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS if os.name == 'nt' else 0,
    )
    print(f"Backend process spawned (PID: {proc.pid})")

    # Wait up to 10 seconds for backend to be healthy
    for i in range(10):
        time.sleep(1)
        try:
            with urllib.request.urlopen("http://127.0.0.1:8000/health", timeout=2) as resp:
                data = json.loads(resp.read().decode('utf-8'))
                print(f"Backend is UP and HEALTHY! Response: {data}")
                backend_healthy = True
                active_hosts = data.get("active_hosts", 0)
                break
        except Exception as e:
            print(f"Waiting for backend... ({i+1}/10): {e}")

    if not backend_healthy:
        print("ERROR: Backend did not start in time!")
        sys.exit(1)

# Start Host Agent if not already connected
if active_hosts == 0:
    python_host_script = os.path.join(repo_root, "windows-host", "python-host", "host_agent.py")
    if os.path.exists(python_host_script):
        print(f"\n=== STARTING HOST AGENT: {python_host_script} ===")
        host_log = open(os.path.join(logs_dir, "host_agent.log"), "a", encoding="utf-8")
        host_proc = subprocess.Popen(
            [venv_python, python_host_script],
            cwd=repo_root,
            env=env,
            stdout=host_log,
            stderr=host_log,
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS if os.name == 'nt' else 0,
        )
        print(f"Host Agent spawned (PID: {host_proc.pid})")
        time.sleep(2)
else:
    print(f"Host agent is already connected (active_hosts: {active_hosts}).")

# Check backend health again to see active_hosts
time.sleep(3)
try:
    with urllib.request.urlopen("http://127.0.0.1:8000/health", timeout=2) as resp:
        print("\nFinal Health Status:", resp.read().decode('utf-8'))
except Exception as e:
    print("Health check error:", e)
