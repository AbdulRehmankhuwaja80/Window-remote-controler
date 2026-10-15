"""
RemoDesk Native Windows Win32 Host Agent
Uses ctypes to invoke user32.dll SendInput and mss for real-time desktop frame capture.
Connects via WebSocket to the RemoDesk cloud signaling gateway.
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
import httpx
import websockets

# Win32 Constants
INPUT_MOUSE = 0
INPUT_KEYBOARD = 1
INPUT_HARDWARE = 2

MOUSEEVENTF_MOVE = 0x0001
MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004
MOUSEEVENTF_RIGHTDOWN = 0x0008
MOUSEEVENTF_RIGHTUP = 0x0010
MOUSEEVENTF_MIDDLEDOWN = 0x0020
MOUSEEVENTF_MIDDLEUP = 0x0040
MOUSEEVENTF_WHEEL = 0x0800
MOUSEEVENTF_HWHEEL = 0x1000
MOUSEEVENTF_ABSOLUTE = 0x8000
MOUSEEVENTF_VIRTUALDESK = 0x4000

KEYEVENTF_EXTENDEDKEY = 0x0001
KEYEVENTF_KEYUP = 0x0002
KEYEVENTF_UNICODE = 0x0004
KEYEVENTF_SCANCODE = 0x0008

SM_CXVIRTUALSCREEN = 78
SM_CYVIRTUALSCREEN = 79

user32 = ctypes.windll.user32


class MOUSEINPUT(ctypes.Structure):
    _fields_ = [
        ("dx", ctypes.wintypes.LONG),
        ("dy", ctypes.wintypes.LONG),
        ("mouseData", ctypes.wintypes.DWORD),
        ("dwFlags", ctypes.wintypes.DWORD),
        ("time", ctypes.wintypes.DWORD),
        ("dwExtraInfo", ctypes.POINTER(ctypes.wintypes.ULONG)),
    ]


class KEYBDINPUT(ctypes.Structure):
    _fields_ = [
        ("wVk", ctypes.wintypes.WORD),
        ("wScan", ctypes.wintypes.WORD),
        ("dwFlags", ctypes.wintypes.DWORD),
        ("time", ctypes.wintypes.DWORD),
        ("dwExtraInfo", ctypes.POINTER(ctypes.wintypes.ULONG)),
    ]


class HARDWAREINPUT(ctypes.Structure):
    _fields_ = [
        ("uMsg", ctypes.wintypes.DWORD),
        ("wParamL", ctypes.wintypes.WORD),
        ("wParamH", ctypes.wintypes.WORD),
    ]


class INPUT_UNION(ctypes.Union):
    _fields_ = [
        ("mi", MOUSEINPUT),
        ("ki", KEYBDINPUT),
        ("hi", HARDWAREINPUT),
    ]


class INPUT(ctypes.Structure):
    _fields_ = [
        ("type", ctypes.wintypes.DWORD),
        ("u", INPUT_UNION),
    ]


class WindowsInputInjector:
    def __init__(self):
        # Enable Per-Monitor DPI awareness
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(2)
        except Exception:
            try:
                user32.SetProcessDPIAware()
            except Exception:
                pass

    def move_mouse_absolute(self, norm_x: float, norm_y: float):
        norm_x = max(0.0, min(1.0, norm_x))
        norm_y = max(0.0, min(1.0, norm_y))
        x = int(norm_x * 65535.0)
        y = int(norm_y * 65535.0)

        inp = INPUT()
        inp.type = INPUT_MOUSE
        inp.u.mi.dx = x
        inp.u.mi.dy = y
        inp.u.mi.dwFlags = MOUSEEVENTF_MOVE | MOUSEEVENTF_ABSOLUTE | MOUSEEVENTF_VIRTUALDESK
        inp.u.mi.time = 0
        user32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(INPUT))

    def move_mouse_delta(self, dx: int, dy: int):
        inp = INPUT()
        inp.type = INPUT_MOUSE
        inp.u.mi.dx = dx
        inp.u.mi.dy = dy
        inp.u.mi.dwFlags = MOUSEEVENTF_MOVE
        inp.u.mi.time = 0
        user32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(INPUT))

    def mouse_button(self, button: str, action: str):
        flags = 0
        if button.lower() == "left":
            if action == "down": flags = MOUSEEVENTF_LEFTDOWN
            elif action == "up": flags = MOUSEEVENTF_LEFTUP
            elif action == "click":
                self.mouse_button("left", "down")
                time.sleep(0.02)
                self.mouse_button("left", "up")
                return
            elif action == "double_click":
                self.mouse_button("left", "click")
                time.sleep(0.05)
                self.mouse_button("left", "click")
                return
        elif button.lower() == "right":
            if action == "down": flags = MOUSEEVENTF_RIGHTDOWN
            elif action == "up": flags = MOUSEEVENTF_RIGHTUP
            elif action == "click":
                self.mouse_button("right", "down")
                time.sleep(0.02)
                self.mouse_button("right", "up")
                return

        if flags:
            inp = INPUT()
            inp.type = INPUT_MOUSE
            inp.u.mi.dwFlags = flags
            user32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(INPUT))

    def mouse_scroll(self, dx: int, dy: int):
        if dy != 0:
            inp = INPUT()
            inp.type = INPUT_MOUSE
            inp.u.mi.dwFlags = MOUSEEVENTF_WHEEL
            inp.u.mi.mouseData = dy
            user32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(INPUT))
        if dx != 0:
            inp = INPUT()
            inp.type = INPUT_MOUSE
            inp.u.mi.dwFlags = MOUSEEVENTF_HWHEEL
            inp.u.mi.mouseData = dx
            user32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(INPUT))

    def key_event(self, vk: int, action: str, extended: bool = False):
        flags = KEYEVENTF_KEYUP if action == "up" else 0
        if extended:
            flags |= KEYEVENTF_EXTENDEDKEY

        inp = INPUT()
        inp.type = INPUT_KEYBOARD
        inp.u.ki.wVk = vk
        inp.u.ki.wScan = user32.MapVirtualKeyW(vk, 0)
        inp.u.ki.dwFlags = flags
        user32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(INPUT))

    def send_unicode_text(self, text: str):
        for char in text:
            # KeyDown
            inp_down = INPUT()
            inp_down.type = INPUT_KEYBOARD
            inp_down.u.ki.wVk = 0
            inp_down.u.ki.wScan = ord(char)
            inp_down.u.ki.dwFlags = KEYEVENTF_UNICODE
            user32.SendInput(1, ctypes.byref(inp_down), ctypes.sizeof(INPUT))

            # KeyUp
            inp_up = INPUT()
            inp_up.type = INPUT_KEYBOARD
            inp_up.u.ki.wVk = 0
            inp_up.u.ki.wScan = ord(char)
            inp_up.u.ki.dwFlags = KEYEVENTF_UNICODE | KEYEVENTF_KEYUP
            user32.SendInput(1, ctypes.byref(inp_up), ctypes.sizeof(INPUT))


class DesktopScreenCapturer:
    def __init__(self):
        self.sct = mss.mss()
        self.monitor = self.sct.monitors[1]  # Primary display

    def capture_jpeg(self, quality: int = 75, max_width: int = 1280) -> bytes:
        try:
            img_raw = self.sct.grab(self.monitor)
            img = Image.frombytes("RGB", img_raw.size, img_raw.bgra, "raw", "BGRX")
        except Exception:
            # Fallback when running in headless terminal / locked display / session 0
            from PIL import ImageDraw
            img = Image.new("RGB", (1920, 1080), color=(15, 23, 42))
            draw = ImageDraw.Draw(img)
            draw.rectangle([(40, 40), (1880, 1040)], outline=(59, 130, 246), width=4)
            draw.text((100, 100), f"RemoDesk Windows Desktop Stream - {time.strftime('%Y-%m-%d %H:%M:%S')}", fill=(248, 250, 252))

        if img.width > max_width:
            ratio = max_width / float(img.width)
            new_height = int(img.height * ratio)
            img = img.resize((max_width, new_height), Image.Resampling.BILINEAR)

        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=quality, optimize=True)
        return buf.getvalue()


class RemoDeskHostAgent:
    def __init__(self, server_url: str = "http://127.0.0.1:8000"):
        self.server_url = server_url
        self.ws_url = server_url.replace("http://", "ws://").replace("https://", "wss://") + "/ws/signaling"
        self.device_id = None
        self.auth_key = None
        self.injector = WindowsInputInjector()
        self.capturer = DesktopScreenCapturer()
        self.is_running = False
        self.is_paused = False
        self.active_session_id = None

    async def register(self, user_token: str):
        async with httpx.AsyncClient(base_url=self.server_url) as client:
            headers = {"Authorization": f"Bearer {user_token}"}
            payload = {
                "device_name": os.environ.get("COMPUTERNAME", "Windows Laptop"),
                "hostname": os.environ.get("COMPUTERNAME", "WINDOWS-HOST"),
                "os_info": "Windows 11 (Win32 Native Agent)",
                "hardware_id": os.environ.get("COMPUTERNAME", "HOST") + "-" + os.environ.get("USERNAME", "USER"),
            }
            resp = await client.post("/api/devices/register-host", json=payload, headers=headers)
            if resp.status_code == 200:
                data = resp.json()
                self.device_id = data["device"]["id"]
                self.auth_key = data["auth_key"]
                print(f"[HostAgent] Registered with cloud gateway. Device ID: {self.device_id}")
                return self.device_id, self.auth_key
            else:
                raise RuntimeError(f"Registration failed: {resp.text}")

    async def run(self):
        self.is_running = True
        ws_uri = f"{self.ws_url}?role=host&device_id={self.device_id}&auth_key={self.auth_key}"
        print(f"[HostAgent] Connecting to signaling: {ws_uri}")

        while self.is_running:
            try:
                async with websockets.connect(ws_uri) as ws:
                    print("[HostAgent] Connected to gateway! Laptop is ONLINE.")
                    capture_task = None

                    async for message in ws:
                        data = json.loads(message)
                        msg_type = data.get("type")

                        if msg_type == "incoming_session_request":
                            sess_id = data.get("session_id")
                            client_id = data.get("client_id")
                            print(f"[HostAgent] Incoming session request from client: {data.get('client_info')}")
                            # Auto-accept authorized user session
                            await ws.send(json.dumps({
                                "type": "session_response",
                                "session_id": sess_id,
                                "client_id": client_id,
                                "accepted": True,
                            }))
                            self.active_session_id = sess_id

                        elif msg_type == "webrtc_offer":
                            sess_id = data.get("session_id")
                            # Mock or negotiate answer
                            await ws.send(json.dumps({
                                "type": "webrtc_answer",
                                "session_id": sess_id,
                                "sdp": "v=0\r\no=RemoDesk 0 0 IN IP4 127.0.0.1\r\ns=RemoDesk Session\r\nt=0 0\r\n",
                            }))

                        elif msg_type == "session_terminated":
                            print(f"[HostAgent] Session terminated: {data.get('reason')}")
                            self.active_session_id = None

                        # Handle Direct Input Control Messages
                        elif msg_type == "mouse_move" and not self.is_paused:
                            self.injector.move_mouse_absolute(data["x"], data["y"])

                        elif msg_type == "mouse_delta" and not self.is_paused:
                            self.injector.move_mouse_delta(data["dx"], data["dy"])

                        elif msg_type == "mouse_button" and not self.is_paused:
                            self.injector.mouse_button(data["button"], data["action"])

                        elif msg_type == "mouse_scroll" and not self.is_paused:
                            self.injector.mouse_scroll(data.get("dx", 0), data.get("dy", 0))

                        elif msg_type == "key_event" and not self.is_paused:
                            self.injector.key_event(data["vk"], data["action"], data.get("extended", False))

                        elif msg_type == "text_input" and not self.is_paused:
                            self.injector.send_unicode_text(data["text"])

            except Exception as e:
                print(f"[HostAgent] Connection error: {e}. Reconnecting in 3 seconds...")
                await asyncio.sleep(3)


if __name__ == "__main__":
    agent = RemoDeskHostAgent()
    print("RemoDesk Host Agent initialized.")
