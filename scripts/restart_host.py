import subprocess
import os
import sys
import time
import urllib.request
import json

repo_root = r"D:\Antigravity\Window-remote-controler-main"
venv_python = os.path.join(repo_root, "backend_venv", "Scripts", "python.exe")
if not os.path.exists(venv_python):
    venv_python = sys.executable

# 1. Kill any existing host_agent.py
cmd = 'wmic process where "commandline like \'%host_agent.py%\'" get processid'
try:
    out = subprocess.check_output(cmd, shell=True, text=True)
    pids = [line.strip() for line in out.splitlines() if line.strip().isdigit()]
    for pid in pids:
        print(f"Stopping old host_agent (PID {pid})...")
        subprocess.run(f"taskkill /F /PID {pid}", shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
except Exception as e:
    print(f"Note: {e}")

time.sleep(1)

# 2. Start fresh host_agent.py
script = os.path.join(repo_root, "windows-host", "python-host", "host_agent.py")
print(f"Starting updated Host Agent: {script}")
proc = subprocess.Popen(
    [venv_python, script],
    cwd=repo_root,
    creationflags=subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS if os.name == 'nt' else 0,
    close_fds=True
)
print(f"Host Agent spawned with PID: {proc.pid}")

# 3. Wait and check health
time.sleep(3)
try:
    with urllib.request.urlopen("http://127.0.0.1:8000/health", timeout=3) as resp:
        print("Backend Health Status:", resp.read().decode('utf-8'))
except Exception as e:
    print("Health check status:", e)
