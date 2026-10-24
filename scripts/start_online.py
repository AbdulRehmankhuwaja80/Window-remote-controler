import subprocess
import time
import urllib.request
import os
import sys
import re
import json

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
venv_python = os.path.join(repo_root, "backend_venv", "Scripts", "python.exe")
if not os.path.exists(venv_python):
    venv_python = sys.executable

cloudflared_exe = os.path.join(repo_root, "cloudflared.exe")
if not os.path.exists(cloudflared_exe):
    print(f"[ERROR] {cloudflared_exe} not found!", flush=True)
    sys.exit(1)

# 1. Check if backend is already healthy
backend_healthy = False
try:
    with urllib.request.urlopen("http://127.0.0.1:8000/health", timeout=2) as resp:
        backend_healthy = True
except Exception:
    pass

if not backend_healthy:
    print("=== STARTING REMODESK BACKEND ===", flush=True)
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
        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS if os.name == 'nt' else 0,
        close_fds=True
    )
    print(f"Backend process spawned (PID: {proc.pid})", flush=True)
    for i in range(10):
        time.sleep(1)
        try:
            with urllib.request.urlopen("http://127.0.0.1:8000/health", timeout=2) as resp:
                backend_healthy = True
                break
        except Exception:
            pass

# 2. Check if host agent is running (active_hosts >= 1)
try:
    with urllib.request.urlopen("http://127.0.0.1:8000/health", timeout=2) as resp:
        health_data = json.loads(resp.read().decode('utf-8'))
        active_hosts = health_data.get("active_hosts", 0)
except Exception:
    active_hosts = 0

if active_hosts < 1:
    python_host_script = os.path.join(repo_root, "windows-host", "python-host", "host_agent.py")
    if os.path.exists(python_host_script):
        print("=== STARTING PYTHON HOST AGENT ===", flush=True)
        subprocess.Popen(
            [venv_python, python_host_script],
            cwd=repo_root,
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS if os.name == 'nt' else 0,
            close_fds=True
        )
        time.sleep(2)

# Query laptop pairing PIN from remodesk.db
partner_name = "LAPTOP-4A9AUPQS"
partner_pin = "467008"
try:
    import sqlite3
    db_path = os.path.join(repo_root, "remodesk.db")
    if os.path.exists(db_path):
        with sqlite3.connect(db_path) as conn:
            row = conn.execute("SELECT device_name, pairing_code FROM devices WHERE device_name LIKE '%LAPTOP%' ORDER BY last_seen DESC LIMIT 1").fetchone()
            if row:
                partner_name = row[0]
                partner_pin = row[1]
except Exception:
    pass

print("\n=== STARTING CLOUDFLARE SECURE TUNNEL ===", flush=True)
print("Connecting laptop to Cloudflare Edge Network...", flush=True)

tunnel_cmd = [
    cloudflared_exe,
    "tunnel",
    "--url", "http://127.0.0.1:8000"
]

proc = subprocess.Popen(
    tunnel_cmd,
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    text=True,
    bufsize=1
)

tunnel_url = None
url_regex = re.compile(r"https://[a-zA-Z0-9-]+\.trycloudflare\.com")

try:
    for line in iter(proc.stdout.readline, ""):
        m = url_regex.search(line)
        if m and not tunnel_url:
            tunnel_url = m.group(0)
            print("\n" + "=" * 65, flush=True)
            print("        REMODESK TEAMVIEWER-STYLE ONLINE ACCESS", flush=True)
            print("=" * 65, flush=True)
            print(f"  Gateway Server URL  :  {tunnel_url}", flush=True)
            print(f"  Partner Laptop Name :  {partner_name}", flush=True)
            print(f"  One-Time PIN        :  {partner_pin}", flush=True)
            print("=" * 65, flush=True)
            print("  How to connect from your Android phone:", flush=True)
            print("  1. Open the RemoDesk Android app.", flush=True)
            print(f"  2. In Gateway Server URL, enter: {tunnel_url}", flush=True)
            print("  3. Sign in to your account.", flush=True)
            print(f"  4. Tap '+ Link Laptop' and enter PIN: {partner_pin}", flush=True)
            print("  5. Your laptop is now saved as your go-to device. Tap CONNECT!", flush=True)
            print("=" * 65, flush=True)
            print("\nTunnel is streaming live. Keep this window open.", flush=True)
except KeyboardInterrupt:
    print("\nStopping Cloudflare Tunnel...", flush=True)
    proc.terminate()
