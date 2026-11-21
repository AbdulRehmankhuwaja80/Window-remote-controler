"""
RemoDesk Desktop UI - Backend & Database Client Service
Communicates with the FastAPI Gateway (http://127.0.0.1:8000) and SQLite database (remodesk.db).
"""

import os
import json
import socket
import platform
import sqlite3
import urllib.request
import urllib.error
import urllib.parse
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone


class BackendClient:
    def __init__(self, base_url: str = "http://127.0.0.1:8000"):
        self.base_url = base_url.rstrip("/")
        self.repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        self.db_path = os.path.join(self.repo_root, "remodesk.db")
        self.config_dir = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), "RemoDesk")
        self.config_path = os.path.join(self.config_dir, "host_config.json")

    # ─── Host Configuration ───────────────────────────────────────────────────

    def get_host_config(self) -> Dict[str, Any]:
        """Load local host configuration from APPDATA."""
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {}

    def save_host_config(self, config: Dict[str, Any]) -> bool:
        """Save local host configuration to APPDATA."""
        try:
            os.makedirs(self.config_dir, exist_ok=True)
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(config, f, indent=2)
            return True
        except Exception:
            return False

    # ─── Gateway Health & Status ──────────────────────────────────────────────

    def get_gateway_health(self) -> Dict[str, Any]:
        """Query /health endpoint to check server & host connectivity."""
        try:
            req = urllib.request.Request(f"{self.base_url}/health", method="GET")
            with urllib.request.urlopen(req, timeout=2) as resp:
                if resp.status == 200:
                    data = json.loads(resp.read().decode("utf-8"))
                    return {
                        "online": True,
                        "status": data.get("status", "healthy"),
                        "active_hosts": data.get("active_hosts", 0),
                        "active_clients": data.get("active_clients", 0),
                        "active_sessions": data.get("active_sessions", 0),
                        "version": data.get("version", "1.0.0"),
                    }
        except Exception:
            pass
        return {
            "online": False,
            "status": "offline",
            "active_hosts": 0,
            "active_clients": 0,
            "active_sessions": 0,
            "version": "1.0.0",
        }

    # ─── Device & Pairing Management ──────────────────────────────────────────

    def get_device_info(self) -> Dict[str, Any]:
        """Fetch primary registered host device information from DB or config."""
        cfg = self.get_host_config()
        dev_id = cfg.get("DeviceId", "")

        info = {
            "device_id": dev_id,
            "device_name": cfg.get("DeviceName", socket.gethostname()),
            "pairing_code": cfg.get("PairingCode", "867902"),
            "status": "OFFLINE",
            "is_remote_enabled": cfg.get("IsRemoteAccessEnabled", True),
            "auth_key": cfg.get("AuthKey", ""),
            "hostname": socket.gethostname(),
            "os_info": f"{platform.system()} {platform.release()}",
            "last_seen": None,
        }

        # Query live database for accurate state
        if os.path.exists(self.db_path):
            try:
                with sqlite3.connect(self.db_path) as conn:
                    conn.row_factory = sqlite3.Row
                    if dev_id:
                        cur = conn.execute("SELECT * FROM devices WHERE id = ?", (dev_id,))
                        row = cur.fetchone()
                    else:
                        cur = conn.execute("SELECT * FROM devices ORDER BY last_seen DESC LIMIT 1")
                        row = cur.fetchone()

                    if row:
                        info["device_id"] = row["id"]
                        info["device_name"] = row["device_name"] or info["device_name"]
                        info["pairing_code"] = row["pairing_code"] or info["pairing_code"]
                        info["status"] = row["status"] or "OFFLINE"
                        info["is_remote_enabled"] = bool(row["is_remote_enabled"])
                        info["auth_key"] = row["auth_key"] or info["auth_key"]
                        info["last_seen"] = row["last_seen"]
            except Exception:
                pass

        return info

    def regenerate_pairing_pin(self) -> Optional[str]:
        """Regenerate a new 6-digit pairing PIN via API or direct DB update."""
        cfg = self.get_host_config()
        dev_id = cfg.get("DeviceId")
        auth_key = cfg.get("AuthKey", "")

        # Try API first
        if dev_id:
            try:
                url = f"{self.base_url}/api/devices/{dev_id}/regenerate-pin"
                if auth_key:
                    url += f"?auth_key={urllib.parse.quote(auth_key)}"
                req = urllib.request.Request(url, data=b"", method="POST")
                with urllib.request.urlopen(req, timeout=3) as resp:
                    if resp.status == 200:
                        data = json.loads(resp.read().decode("utf-8"))
                        new_pin = data.get("pairing_code")
                        if new_pin:
                            cfg["PairingCode"] = new_pin
                            self.save_host_config(cfg)
                            return new_pin
            except Exception:
                pass

        # Fallback to direct SQLite update
        import random
        new_pin = f"{random.randint(100000, 999999)}"
        if os.path.exists(self.db_path) and dev_id:
            try:
                with sqlite3.connect(self.db_path) as conn:
                    conn.execute("UPDATE devices SET pairing_code = ? WHERE id = ?", (new_pin, dev_id))
                    conn.execute(
                        "INSERT INTO audit_logs (user_id, device_id, action, details, created_at) "
                        "VALUES ((SELECT user_id FROM devices WHERE id = ?), ?, 'PIN_REGENERATED', ?, ?)",
                        (dev_id, dev_id, f"PIN regenerated via Desktop UI to {new_pin}", datetime.now(timezone.utc).isoformat())
                    )
                    conn.commit()
            except Exception:
                pass

        cfg["PairingCode"] = new_pin
        self.save_host_config(cfg)
        return new_pin

    def set_remote_access_enabled(self, enabled: bool) -> bool:
        """Toggle remote access permission."""
        cfg = self.get_host_config()
        cfg["IsRemoteAccessEnabled"] = enabled
        self.save_host_config(cfg)

        dev_id = cfg.get("DeviceId")
        if dev_id and os.path.exists(self.db_path):
            try:
                with sqlite3.connect(self.db_path) as conn:
                    conn.execute("UPDATE devices SET is_remote_enabled = ? WHERE id = ?", (1 if enabled else 0, dev_id))
                    conn.execute(
                        "INSERT INTO audit_logs (user_id, device_id, action, details, created_at) "
                        "VALUES ((SELECT user_id FROM devices WHERE id = ?), ?, 'REMOTE_ACCESS_TOGGLED', ?, ?)",
                        (dev_id, dev_id, f"Remote access {'ENABLED' if enabled else 'DISABLED'} via Desktop UI", datetime.now(timezone.utc).isoformat())
                    )
                    conn.commit()
                return True
            except Exception:
                pass
        return True

    # ─── Connected Devices & Active Sessions ──────────────────────────────────

    def get_connected_devices(self) -> List[Dict[str, Any]]:
        """Fetch list of paired and active client devices."""
        devices = []
        if os.path.exists(self.db_path):
            try:
                with sqlite3.connect(self.db_path) as conn:
                    conn.row_factory = sqlite3.Row
                    # Query recent sessions to list clients
                    cur = conn.execute("""
                        SELECT s.id, s.device_id, s.client_info, s.status, s.started_at, s.ended_at
                        FROM session_logs s
                        ORDER BY s.started_at DESC
                        LIMIT 15
                    """)
                    for row in cur.fetchall():
                        devices.append({
                            "session_id": row["id"],
                            "client_info": row["client_info"] or "Android Device",
                            "status": row["status"],
                            "started_at": row["started_at"],
                            "ended_at": row["ended_at"],
                        })
            except Exception:
                pass
        return devices

    # ─── Audit & Security Logs ────────────────────────────────────────────────

    def get_audit_logs(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Fetch security audit logs."""
        logs = []
        if os.path.exists(self.db_path):
            try:
                with sqlite3.connect(self.db_path) as conn:
                    conn.row_factory = sqlite3.Row
                    cur = conn.execute("""
                        SELECT id, action, details, ip_address, created_at
                        FROM audit_logs
                        ORDER BY id DESC
                        LIMIT ?
                    """, (limit,))
                    for row in cur.fetchall():
                        logs.append({
                            "id": row["id"],
                            "action": row["action"],
                            "details": row["details"] or "",
                            "ip_address": row["ip_address"] or "127.0.0.1",
                            "created_at": row["created_at"],
                        })
            except Exception:
                pass
        return logs

    # ─── System & Network Information ─────────────────────────────────────────

    def get_network_info(self) -> Dict[str, str]:
        """Detect local IP and active network configuration."""
        lan_ip = "127.0.0.1"
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            lan_ip = s.getsockname()[0]
            s.close()
        except Exception:
            lan_ip = "192.168.0.43"

        return {
            "lan_ip": lan_ip,
            "port": "8000",
            "lan_url": f"http://{lan_ip}:8000",
            "download_url": f"http://{lan_ip}:8000/download",
            "hostname": socket.gethostname(),
            "os_name": f"{platform.system()} {platform.release()} (Build {platform.version().split('.')[2] if len(platform.version().split('.')) > 2 else 'N/A'})",
        }
