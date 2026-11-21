"""
RemoDesk Desktop UI - Cloudflare Tunnel Controller Service
Manages cloudflared.exe tunnel in a background QThread without blocking the UI.
"""

import os
import re
import subprocess
from typing import Optional
from PySide6.QtCore import QObject, QThread, Signal


class TunnelWorker(QThread):
    tunnel_started = Signal(str)
    tunnel_stopped = Signal()
    tunnel_error = Signal(str)
    log_line = Signal(str)

    def __init__(self, cloudflared_path: str, port: int = 8000):
        super().__init__()
        self.cloudflared_path = cloudflared_path
        self.port = port
        self.process: Optional[subprocess.Popen] = None
        self._is_running = True
        self.public_url: Optional[str] = None

    def run(self):
        if not os.path.exists(self.cloudflared_path):
            self.tunnel_error.emit("cloudflared.exe was not found in project folder.")
            return

        cmd = [
            self.cloudflared_path,
            "tunnel",
            "--url", f"http://127.0.0.1:{self.port}"
        ]

        try:
            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
            )

            url_regex = re.compile(r"https://[a-zA-Z0-9-]+\.trycloudflare\.com")
            
            while self._is_running and self.process and self.process.poll() is None:
                line = self.process.stdout.readline()
                if not line:
                    break
                line_str = line.strip()
                if line_str:
                    self.log_line.emit(line_str)

                m = url_regex.search(line_str)
                if m and not self.public_url:
                    self.public_url = m.group(0)
                    self.tunnel_started.emit(self.public_url)

        except Exception as e:
            self.tunnel_error.emit(str(e))
        finally:
            self.stop()
            self.tunnel_stopped.emit()

    def stop(self):
        self._is_running = False
        if self.process and self.process.poll() is None:
            try:
                self.process.terminate()
                self.process.wait(timeout=2)
            except Exception:
                try:
                    self.process.kill()
                except Exception:
                    pass
        self.process = None
        self.public_url = None


class TunnelController(QObject):
    tunnel_started = Signal(str)
    tunnel_stopped = Signal()
    tunnel_error = Signal(str)
    log_line = Signal(str)

    def __init__(self):
        super().__init__()
        self.repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        self.cloudflared_exe = os.path.join(self.repo_root, "cloudflared.exe")
        self.worker: Optional[TunnelWorker] = None
        self.current_url: Optional[str] = None

    def is_tunnel_running(self) -> bool:
        return self.worker is not None and self.worker.isRunning()

    def get_public_url(self) -> Optional[str]:
        return self.current_url

    def start_tunnel(self) -> bool:
        if self.is_tunnel_running():
            return True

        if not os.path.exists(self.cloudflared_exe):
            self.tunnel_error.emit(f"cloudflared.exe not found at {self.cloudflared_exe}")
            return False

        self.worker = TunnelWorker(self.cloudflared_exe, 8000)
        self.worker.tunnel_started.connect(self._on_started)
        self.worker.tunnel_stopped.connect(self._on_stopped)
        self.worker.tunnel_error.connect(self.tunnel_error)
        self.worker.log_line.connect(self.log_line)
        self.worker.start()
        return True

    def _on_started(self, url: str):
        self.current_url = url
        self.tunnel_started.emit(url)

    def _on_stopped(self):
        self.current_url = None
        self.tunnel_stopped.emit()

    def stop_tunnel(self):
        if self.worker:
            self.worker.stop()
            self.worker.quit()
            self.worker.wait(1000)
            self.worker = None
        self.current_url = None
