"""
Test suite for RemoDesk Host Screen Capture & Win32 Input Injection
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    import pytest
except ImportError:
    pytest = None

from host_agent import DesktopScreenCapturer, WindowsInputInjector



def test_screen_capture_live():
    capturer = DesktopScreenCapturer()
    jpeg_bytes = capturer.capture_jpeg(quality=70, max_width=800)
    
    assert jpeg_bytes is not None
    assert len(jpeg_bytes) > 500, f"Captured JPEG should have meaningful payload, got {len(jpeg_bytes)} bytes"
    # Verify JPEG magic bytes FF D8
    assert jpeg_bytes[:2] == b"\xff\xd8", "Payload must be a valid JPEG image"

    print(f"\n[Test] Live screen capture succeeded! Captured frame size: {len(jpeg_bytes)} bytes")


def test_win32_input_injection():
    injector = WindowsInputInjector()

    # 1. Test Mouse Absolute Move
    injector.move_mouse_absolute(0.5, 0.5)

    # 2. Test Mouse Relative Delta Move
    injector.move_mouse_delta(5, -5)

    # 3. Test Mouse Left Click
    injector.mouse_button("left", "click")

    # 4. Test Mouse Wheel Scroll
    injector.mouse_scroll(0, -120)

    # 5. Test Key Event (Shift key down and up)
    injector.key_event(16, "down")
    injector.key_event(16, "up")

    # 6. Test Unicode Text typing
    injector.send_unicode_text("RemoDesk")

    print("[Test] Win32 SendInput execution passed without errors!")


if __name__ == "__main__":
    test_screen_capture_live()
    test_win32_input_injection()
    print("All live host tests passed successfully!")
