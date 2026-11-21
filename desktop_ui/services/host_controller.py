"""
RemoDesk Desktop UI - Host Agent & Backend Process Controller
Starts, stops, monitors, and restarts the Windows Host Agent and FastAPI Gateway.
"""

import os
import sys
import time
import subprocess
from typing import Optional, Dict, Any


class HostController:
    def __init__(self):
        self.repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        self.python_exe = sys.executable
        self.host_script = os.path.join(self.repo_root, "windows-host", "python-host", "host_agent.py")
        self.logs_dir = os.path.join(self.repo_root, "logs")
        os.makedirs(self.logs_dir, exist_ok=True)
        self.host_process: Optional[subprocess.Popen] = None

    def _get_env(self) -> Dict[str, str]:
        env = dict(os.environ)
        env["PYTHONPATH"] = self.repo_root + (os.pathsep + env["PYTHONPATH"] if "PYTHONPATH" in env else "")
        return env

    # ─── Process Inspection ───────────────────────────────────────────────────

    def is_host_running(self) -> bool:
        """Check if Python Host Agent is currently running."""
        try:
            # Check using tasklist or wmic on Windows
            output = subprocess.check_output(
                ["wmic", "process", "where", "name='python.exe'", "get", "CommandLine,ProcessId"],
                text=True,
                stderr=subprocess.DEVNULL
            )
            for line in output.splitlines():
                if "host_agent.py" in line:
                    return True
        except Exception:
            pass
        return self.host_process is not None and self.host_process.poll() is None

    def get_host_pid(self) -> Optional[int]:
        """Get PID of running host agent."""
        try:
            output = subprocess.check_output(
                ["wmic", "process", "where", "name='python.exe'", "get", "CommandLine,ProcessId"],
                text=True,
                stderr=subprocess.DEVNULL
            )
            for line in output.splitlines():
                if "host_agent.py" in line:
                    parts = line.strip().split()
                    if parts and parts[-1].isdigit():
                        return int(parts[-1])
        except Exception:
            pass
        if self.host_process and self.host_process.poll() is None:
            return self.host_process.pid
        return None

    # ─── Process Control ──────────────────────────────────────────────────────

    def start_host(self) -> bool:
        """Start the Python Host Agent in background."""
        if self.is_host_running():
            return True

        if not os.path.exists(self.host_script):
            return False

        try:
            log_path = os.path.join(self.logs_dir, "host_agent.log")
            log_file = open(log_path, "a", encoding="utf-8")
            
            flags = subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS if os.name == "nt" else 0
            self.host_process = subprocess.Popen(
                [self.python_exe, self.host_script],
                cwd=self.repo_root,
                env=self._get_env(),
                stdout=log_file,
                stderr=log_file,
                creationflags=flags,
            )
            time.sleep(1.5)
            return self.is_host_running()
        except Exception:
            return False

    def stop_host(self) -> bool:
        """Stop the running Host Agent."""
        stopped = False
        pid = self.get_host_pid()
        if pid:
            try:
                subprocess.call(["taskkill", "/F", "/PID", str(pid)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                stopped = True
            except Exception:
                pass

        if self.host_process and self.host_process.poll() is None:
            try:
                self.host_process.terminate()
                self.host_process = None
                stopped = True
            except Exception:
                pass

        time.sleep(0.5)
        return stopped or not self.is_host_running()

    def restart_host(self) -> bool:
        """Restart the Host Agent cleanly."""
        self.stop_host()
        time.sleep(1.0)
        return self.start_host()

    # ─── Backend Service Verification ─────────────────────────────────────────

    def ensure_backend_running(self) -> bool:
        """Ensure Uvicorn backend gateway is running, or spawn it."""
        import urllib.request
        try:
            with urllib.request.urlopen("http://127.0.0.1:8000/health", timeout=1) as resp:
                if resp.status == 200:
                    return True
        except Exception:
            pass

        try:
            log_path = os.path.join(self.logs_dir, "backend.log")
            log_file = open(log_path, "a", encoding="utf-8")
            backend_cmd = [
                self.python_exe,
                "-m", "uvicorn",
                "backend.app.main:app",
                "--host", "0.0.0.0",
                "--port", "8000"
            ]
            flags = subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS if os.name == "nt" else 0
            proc = subprocess.Popen(
                backend_cmd,
                cwd=self.repo_root,
                env=self._get_env(),
                stdout=log_file,
                stderr=log_file,
                creationflags=flags,
            )
            # Wait up to 5 seconds
            for _ in range(5):
                time.sleep(1)
                try:
                    with urllib.request.urlopen("http://127.0.0.1:8000/health", timeout=1) as resp:
                        if resp.status == 200:
                            return True
                except Exception:
                    pass
        except Exception:
            pass
        return False
