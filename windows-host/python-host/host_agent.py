"""
RemoDesk Python Host Agent — Desktop Frame Streaming + Input Injection
Connects via WebSocket to the signaling gateway, streams live JPEG frames,
and processes mouse/keyboard input messages from the Android client.
"""

import sys
import os
import json
import time
import ctypes
import ctypes.wintypes
import asyncio
import base64
import io
import mss
from PIL import Image
import websockets

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# ─── Win32 Input Constants ────────────────────────────────────────────────────
INPUT_MOUSE = 0
INPUT_KEYBOARD = 1
MOUSEEVENTF_MOVE = 0x0001
MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004
MOUSEEVENTF_RIGHTDOWN = 0x0008
MOUSEEVENTF_RIGHTUP = 0x0010
MOUSEEVENTF_WHEEL = 0x0800
MOUSEEVENTF_ABSOLUTE = 0x8000
MOUSEEVENTF_VIRTUALDESK = 0x4000
KEYEVENTF_KEYUP = 0x0002
KEYEVENTF_UNICODE = 0x0004

user32 = ctypes.windll.user32

class MOUSEINPUT(ctypes.Structure):
    _fields_ = [("dx", ctypes.wintypes.LONG), ("dy", ctypes.wintypes.LONG),
                ("mouseData", ctypes.wintypes.DWORD), ("dwFlags", ctypes.wintypes.DWORD),
                ("time", ctypes.wintypes.DWORD), ("dwExtraInfo", ctypes.POINTER(ctypes.wintypes.ULONG))]

class KEYBDINPUT(ctypes.Structure):
    _fields_ = [("wVk", ctypes.wintypes.WORD), ("wScan", ctypes.wintypes.WORD),
                ("dwFlags", ctypes.wintypes.DWORD), ("time", ctypes.wintypes.DWORD),
                ("dwExtraInfo", ctypes.POINTER(ctypes.wintypes.ULONG))]

class HARDWAREINPUT(ctypes.Structure):
    _fields_ = [("uMsg", ctypes.wintypes.DWORD), ("wParamL", ctypes.wintypes.WORD),
                ("wParamH", ctypes.wintypes.WORD)]

class INPUT_UNION(ctypes.Union):
    _fields_ = [("mi", MOUSEINPUT), ("ki", KEYBDINPUT), ("hi", HARDWAREINPUT)]

class INPUT(ctypes.Structure):
    _fields_ = [("type", ctypes.wintypes.DWORD), ("u", INPUT_UNION)]


def attach_to_input_desktop():
    """Ensure the calling thread is attached to the active interactive input desktop."""
    try:
        h_desk = user32.OpenInputDesktop(0, False, 0x01FF)
        if h_desk:
            user32.SetThreadDesktop(h_desk)
            return h_desk
    except Exception:
        pass
    return None


# ─── Input Injector ───────────────────────────────────────────────────────────
class InputInjector:
    def __init__(self):
        attach_to_input_desktop()
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(2)
        except Exception:
            try:
                user32.SetProcessDPIAware()
            except Exception:
                pass
        self.screen_w = user32.GetSystemMetrics(0) or 1920
        self.screen_h = user32.GetSystemMetrics(1) or 1080
        self.last_cursor_x = self.screen_w // 2
        self.last_cursor_y = self.screen_h // 2

    def get_cursor_position(self):
        pt = ctypes.wintypes.POINT()
        if user32.GetCursorPos(ctypes.byref(pt)):
            self.last_cursor_x = pt.x
            self.last_cursor_y = pt.y
            return (pt.x, pt.y)
        attach_to_input_desktop()
        if user32.GetCursorPos(ctypes.byref(pt)):
            self.last_cursor_x = pt.x
            self.last_cursor_y = pt.y
            return (pt.x, pt.y)
        return (self.last_cursor_x, self.last_cursor_y)

    def mouse_move(self, norm_x, norm_y):
        self.last_cursor_x = int(norm_x * self.screen_w)
        self.last_cursor_y = int(norm_y * self.screen_h)
        x = int(max(0.0, min(1.0, norm_x)) * 65535)
        y = int(max(0.0, min(1.0, norm_y)) * 65535)
        inp = INPUT()
        inp.type = INPUT_MOUSE
        inp.u.mi.dx = x
        inp.u.mi.dy = y
        inp.u.mi.dwFlags = MOUSEEVENTF_MOVE | MOUSEEVENTF_ABSOLUTE | MOUSEEVENTF_VIRTUALDESK
        user32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(INPUT))

    def mouse_button(self, button, action):
        flags = 0
        if button == "left":
            if action == "down":
                flags = MOUSEEVENTF_LEFTDOWN
            elif action == "up":
                flags = MOUSEEVENTF_LEFTUP
            elif action == "click":
                self.mouse_button("left", "down"); time.sleep(0.02); self.mouse_button("left", "up"); return
            elif action == "double_click":
                self.mouse_button("left", "click"); time.sleep(0.05); self.mouse_button("left", "click"); return
        elif button == "right":
            if action == "down":
                flags = MOUSEEVENTF_RIGHTDOWN
            elif action == "up":
                flags = MOUSEEVENTF_RIGHTUP
            elif action == "click":
                self.mouse_button("right", "down"); time.sleep(0.02); self.mouse_button("right", "up"); return
        if flags:
            inp = INPUT(); inp.type = INPUT_MOUSE; inp.u.mi.dwFlags = flags
            user32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(INPUT))

    def mouse_scroll(self, dx, dy):
        if dy != 0:
            inp = INPUT(); inp.type = INPUT_MOUSE; inp.u.mi.dwFlags = MOUSEEVENTF_WHEEL; inp.u.mi.mouseData = dy
            user32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(INPUT))

    def mouse_delta(self, dx, dy):
        self.last_cursor_x = max(0, min(self.screen_w, self.last_cursor_x + int(dx)))
        self.last_cursor_y = max(0, min(self.screen_h, self.last_cursor_y + int(dy)))
        inp = INPUT()
        inp.type = INPUT_MOUSE
        inp.u.mi.dx = int(dx)
        inp.u.mi.dy = int(dy)
        inp.u.mi.dwFlags = MOUSEEVENTF_MOVE
        user32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(INPUT))

    def key_event(self, vk, action, extended=False):
        flags = KEYEVENTF_KEYUP if action == "up" else 0
        if extended:
            flags |= 0x0001
        inp = INPUT(); inp.type = INPUT_KEYBOARD; inp.u.ki.wVk = vk
        inp.u.ki.wScan = user32.MapVirtualKeyW(vk, 0); inp.u.ki.dwFlags = flags
        user32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(INPUT))

    def send_text(self, text):
        for char in text:
            for flags in [KEYEVENTF_UNICODE, KEYEVENTF_UNICODE | KEYEVENTF_KEYUP]:
                inp = INPUT(); inp.type = INPUT_KEYBOARD; inp.u.ki.wVk = 0
                inp.u.ki.wScan = ord(char); inp.u.ki.dwFlags = flags
                user32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(INPUT))

    def set_clipboard(self, text):
        try:
            kernel32 = ctypes.windll.kernel32
            GMEM_MOVEABLE = 0x0002
            CF_UNICODETEXT = 13
            if not user32.OpenClipboard(None):
                return
            user32.EmptyClipboard()
            text_bytes = (text + "\0").encode("utf-16le")
            h_mem = kernel32.GlobalAlloc(GMEM_MOVEABLE, len(text_bytes))
            p_mem = kernel32.GlobalLock(h_mem)
            ctypes.memmove(p_mem, text_bytes, len(text_bytes))
            kernel32.GlobalUnlock(h_mem)
            user32.SetClipboardData(CF_UNICODETEXT, h_mem)
            user32.CloseClipboard()
        except Exception as e:
            print(f"[Host] Clipboard error: {e}")

    # Aliases for live tests and legacy compatibility
    move_mouse_absolute = mouse_move
    move_mouse_delta = mouse_delta
    send_unicode_text = send_text


# Aliases for test suite
WindowsInputInjector = InputInjector



# ─── Screen Capturer ──────────────────────────────────────────────────────────
class ScreenCapturer:
    def __init__(self):
        attach_to_input_desktop()
        self.sct = mss.mss()
        self.monitor = self.sct.monitors[1]
        self.screen_width = self.monitor.get("width", 1920)
        self.screen_height = self.monitor.get("height", 1080)

    def capture_jpeg(self, quality=80, max_width=1920, cursor_pos=None):
        try:
            raw = self.sct.grab(self.monitor)
            img = Image.frombytes("RGB", raw.size, raw.bgra, "raw", "BGRX")
        except Exception:
            attach_to_input_desktop()
            try:
                raw = self.sct.grab(self.monitor)
                img = Image.frombytes("RGB", raw.size, raw.bgra, "raw", "BGRX")
            except Exception:
                img = Image.new("RGB", (self.screen_width, self.screen_height), color=(15, 23, 42))
                from PIL import ImageDraw
                draw = ImageDraw.Draw(img)
                draw.text((100, 100), f"RemoDesk Desktop — {time.strftime('%H:%M:%S')}", fill=(248, 250, 252))

        orig_w = img.width
        orig_h = img.height

        # Rescale if needed (preserving aspect ratio)
        scale = 1.0
        if orig_w > max_width:
            scale = max_width / float(orig_w)
            target_h = int(orig_h * scale)
            img = img.resize((max_width, target_h), Image.Resampling.LANCZOS)

        # Draw mouse cursor
        if cursor_pos:
            cx = int(cursor_pos[0] * scale)
            cy = int(cursor_pos[1] * scale)
            if 0 <= cx < img.width and 0 <= cy < img.height:
                from PIL import ImageDraw
                draw = ImageDraw.Draw(img)
                pts = [
                    (cx, cy),
                    (cx, cy + 18),
                    (cx + 4, cy + 14),
                    (cx + 8, cy + 22),
                    (cx + 11, cy + 21),
                    (cx + 7, cy + 13),
                    (cx + 13, cy + 13),
                ]
                draw.polygon(pts, fill=(255, 255, 255), outline=(0, 0, 0), width=2)

        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=quality, optimize=True)
        return buf.getvalue()


# Alias for test suite
DesktopScreenCapturer = ScreenCapturer


# ─── Host Agent ───────────────────────────────────────────────────────────────
class HostAgent:
    def __init__(self, server_url, device_id, auth_key):
        self.server_url = server_url
        self.ws_url = server_url.replace("http://", "ws://").replace("https://", "wss://") + "/ws/signaling"
        self.device_id = device_id
        self.auth_key = auth_key
        self.injector = InputInjector()
        self.capturer = ScreenCapturer()
        self.active_session = None
        self._frame_task = None

        # Dynamic stream configuration (Synced with phone)
        self.stream_width = 1920
        self.stream_quality = 80
        self.stream_interval = 0.05  # ~20 fps

    def update_quality_profile(self, preset_or_quality, width=None):
        if width and int(width) > 0:
            self.stream_width = min(int(width), 2560)

        if isinstance(preset_or_quality, str):
            p = preset_or_quality.lower()
            if "low" in p or "720" in p:
                self.stream_width = min(self.stream_width, 1280)
                self.stream_quality = 65
                self.stream_interval = 0.035
            elif "high" in p or "60" in p:
                self.stream_width = min(self.stream_width, 1920)
                self.stream_quality = 85
                self.stream_interval = 0.04
            else:  # Balanced 1080p
                self.stream_width = min(self.stream_width, 1920)
                self.stream_quality = 80
                self.stream_interval = 0.05
        elif isinstance(preset_or_quality, (int, float)):
            self.stream_quality = max(30, min(100, int(preset_or_quality)))

        print(f"[Host] Synced with phone: {self.stream_width}px max width, quality {self.stream_quality}%")

    async def _stream_frames(self, ws):
        """Capture desktop and send JPEG frames synced with phone."""
        attach_to_input_desktop()
        print(f"[Host] Frame streaming started ({self.stream_width}px, quality={self.stream_quality}).")
        try:
            while self.active_session:
                cur_pos = self.injector.get_cursor_position()
                jpeg = self.capturer.capture_jpeg(
                    quality=self.stream_quality,
                    max_width=self.stream_width,
                    cursor_pos=cur_pos
                )
                b64 = base64.b64encode(jpeg).decode("ascii")
                await ws.send(json.dumps({"type": "desktop_frame", "data": b64}))
                await asyncio.sleep(self.stream_interval)
        except Exception as e:
            print(f"[Host] Frame stream stopped: {e}")

    def _handle_input(self, data):
        """Process mouse / keyboard / text input messages."""
        t = data.get("type")
        try:
            if t == "mouse_move":
                self.injector.mouse_move(data["x"], data["y"])
            elif t == "mouse_delta":
                self.injector.mouse_delta(data.get("dx", 0), data.get("dy", 0))
            elif t == "mouse_button":
                self.injector.mouse_button(data["button"], data["action"])
            elif t == "mouse_scroll":
                self.injector.mouse_scroll(data.get("dx", 0), data.get("dy", 0))
            elif t == "key_event":
                self.injector.key_event(data["vk"], data["action"], data.get("extended", False))
            elif t == "text_input":
                self.injector.send_text(data["text"])
            elif t == "clipboard_sync":
                self.injector.set_clipboard(data.get("content", ""))
            elif t == "set_quality":
                self.update_quality_profile(data.get("quality"), data.get("width"))
        except Exception as e:
            print(f"[Host] Input error: {e}")

    async def run(self):
        ws_uri = f"{self.ws_url}?role=host&device_id={self.device_id}&auth_key={self.auth_key}"
        print(f"[Host] Connecting to {self.server_url} ...")

        while True:
            try:
                async with websockets.connect(ws_uri, max_size=2**22, ping_interval=20) as ws:
                    print("[Host] [OK] Connected - laptop is ONLINE and ready.")

                    async for raw in ws:
                        msg = json.loads(raw)
                        mt = msg.get("type")

                        if mt == "registered":
                            print(f"[Host] Registered as device {msg.get('device_id')}")

                        elif mt == "incoming_session_request":
                            sid = msg.get("session_id")
                            cid = msg.get("client_id")
                            info = msg.get("client_info", "Android")

                            # Read phone resolution & quality preset
                            phone_width = msg.get("width")
                            quality_preset = msg.get("quality", "Balanced (1080p / 30fps)")
                            self.update_quality_profile(quality_preset, phone_width)

                            print(f"[Host] Session request from {info} - auto-accepting.")
                            await ws.send(json.dumps({
                                "type": "session_response",
                                "session_id": sid, "client_id": cid, "accepted": True,
                            }))
                            self.active_session = sid
                            # Start frame streaming
                            self._frame_task = asyncio.create_task(self._stream_frames(ws))

                        elif mt == "session_terminated":
                            print(f"[Host] Session ended: {msg.get('reason')}")
                            self.active_session = None
                            if self._frame_task:
                                self._frame_task.cancel()

                        elif mt == "set_quality":
                            self.update_quality_profile(msg.get("quality"), msg.get("width"))

                        # Input messages from Android
                        elif mt in ("mouse_move", "mouse_button", "mouse_scroll",
                                    "mouse_delta", "key_event", "text_input", "clipboard_sync"):
                            self._handle_input(msg)

                        elif mt == "pong":
                            pass

            except Exception as e:
                print(f"[Host] Connection error: {e} - reconnecting in 3 s ...")
                self.active_session = None
                await asyncio.sleep(3)


# ─── Main ─────────────────────────────────────────────────────────────────────
def ensure_host_registration(server_url: str, config_path: str) -> dict:
    import urllib.request
    import socket
    import platform

    cfg = {}
    if os.path.exists(config_path):
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                cfg = json.load(f)
        except Exception:
            cfg = {}

    if not cfg.get("DeviceId") or not cfg.get("AuthKey"):
        print(f"[Host] Device not configured. Auto-registering with gateway at {server_url}...")
        hostname = socket.gethostname()
        username = os.environ.get("USERNAME", "user")
        payload = {
            "device_name": hostname,
            "hostname": hostname,
            "os_info": f"{platform.system()} {platform.release()}",
            "hardware_id": f"{hostname}-{username}",
        }
        try:
            req = urllib.request.Request(
                f"{server_url.rstrip('/')}/api/devices/register-host",
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=8) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                cfg["ServerUrl"] = server_url
                cfg["DeviceId"] = data["device"]["id"]
                cfg["AuthKey"] = data["auth_key"]
                cfg["DeviceName"] = hostname
                cfg["PairingCode"] = data.get("pairing_code", "")

                os.makedirs(os.path.dirname(config_path), exist_ok=True)
                with open(config_path, "w", encoding="utf-8") as f:
                    json.dump(cfg, f, indent=2)
                print(f"[Host] Successfully registered! Device ID: {cfg['DeviceId']}")
                print(f"[Host] Pairing Code: {cfg['PairingCode']}")
        except Exception as e:
            print(f"[Host] Warning: Auto-registration failed ({e}). Checking local config fallback...")

    return cfg


if __name__ == "__main__":
    default_server = os.environ.get("REMODESK_SERVER", "http://127.0.0.1:8000")
    config_dir = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), "RemoDesk")
    config_path = os.path.join(config_dir, "host_config.json")

    cfg = ensure_host_registration(default_server, config_path)
    server = cfg.get("ServerUrl", default_server)
    dev_id = cfg.get("DeviceId")
    auth   = cfg.get("AuthKey")

    if not dev_id or not auth:
        print(f"ERROR: Could not obtain DeviceId or AuthKey from {config_path}")
        print("Ensure the RemoDesk backend gateway is running and try again.")
        sys.exit(1)

    print("=" * 60)
    print("           REMODESK PYTHON HOST AGENT")
    print("=" * 60)
    print(f"  Server       : {server}")
    print(f"  Device ID    : {dev_id}")
    print(f"  Pairing Code : {cfg.get('PairingCode', 'N/A')}")
    print(f"  Config File  : {config_path}")
    print("=" * 60)
    print()

    agent = HostAgent(server, dev_id, auth)
    asyncio.run(agent.run())

