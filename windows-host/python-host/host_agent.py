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


# ─── Input Injector ───────────────────────────────────────────────────────────
class InputInjector:
    def __init__(self):
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(2)
        except Exception:
            try:
                user32.SetProcessDPIAware()
            except Exception:
                pass

    def mouse_move(self, norm_x, norm_y):
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


# ─── Screen Capturer ──────────────────────────────────────────────────────────
class ScreenCapturer:
    def __init__(self):
        self.sct = mss.mss()
        self.monitor = self.sct.monitors[1]

    def capture_jpeg(self, quality=50, max_width=960):
        try:
            raw = self.sct.grab(self.monitor)
            img = Image.frombytes("RGB", raw.size, raw.bgra, "raw", "BGRX")
        except Exception:
            img = Image.new("RGB", (1920, 1080), color=(15, 23, 42))
            from PIL import ImageDraw
            draw = ImageDraw.Draw(img)
            draw.text((100, 100), f"RemoDesk Desktop — {time.strftime('%H:%M:%S')}", fill=(248, 250, 252))

        if img.width > max_width:
            ratio = max_width / float(img.width)
            img = img.resize((max_width, int(img.height * ratio)), Image.Resampling.BILINEAR)

        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=quality, optimize=True)
        return buf.getvalue()


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

    async def _stream_frames(self, ws):
        """Capture desktop and send JPEG frames at ~10 fps."""
        print("[Host] Frame streaming started.")
        try:
            while self.active_session:
                jpeg = self.capturer.capture_jpeg(quality=45, max_width=960)
                b64 = base64.b64encode(jpeg).decode("ascii")
                await ws.send(json.dumps({"type": "desktop_frame", "data": b64}))
                await asyncio.sleep(0.1)   # ~10 fps
        except Exception as e:
            print(f"[Host] Frame stream stopped: {e}")

    def _handle_input(self, data):
        """Process mouse / keyboard / text input messages."""
        t = data.get("type")
        try:
            if t == "mouse_move":
                self.injector.mouse_move(data["x"], data["y"])
            elif t == "mouse_button":
                self.injector.mouse_button(data["button"], data["action"])
            elif t == "mouse_scroll":
                self.injector.mouse_scroll(data.get("dx", 0), data.get("dy", 0))
            elif t == "key_event":
                self.injector.key_event(data["vk"], data["action"], data.get("extended", False))
            elif t == "text_input":
                self.injector.send_text(data["text"])
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

                        # Input messages from Android
                        elif mt in ("mouse_move", "mouse_button", "mouse_scroll",
                                    "mouse_delta", "key_event", "text_input"):
                            self._handle_input(msg)

                        elif mt == "pong":
                            pass

            except Exception as e:
                print(f"[Host] Connection error: {e} - reconnecting in 3 s ...")
                self.active_session = None
                await asyncio.sleep(3)


# ─── Main ─────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    config_path = os.path.join(os.environ.get("APPDATA", ""), "RemoDesk", "host_config.json")
    if not os.path.exists(config_path):
        print(f"ERROR: Config not found at {config_path}")
        print("Run the C# host once first to generate the config, or create it manually.")
        sys.exit(1)

    with open(config_path) as f:
        cfg = json.load(f)

    server = cfg.get("ServerUrl", "http://127.0.0.1:8000")
    dev_id = cfg.get("DeviceId")
    auth   = cfg.get("AuthKey")

    if not dev_id or not auth:
        print("ERROR: DeviceId or AuthKey missing in host_config.json")
        sys.exit(1)

    print(f"RemoDesk Python Host Agent")
    print(f"  Server : {server}")
    print(f"  Device : {dev_id}")
    print(f"  Config : {config_path}")
    print()

    agent = HostAgent(server, dev_id, auth)
    asyncio.run(agent.run())
