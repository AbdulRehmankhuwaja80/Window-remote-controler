"""
RemoDesk Desktop UI - Main Application Entrypoint
Initializes Qt application, high-DPI scaling, QSS stylesheet, and main window.
"""

import sys
import os

# Ensure repository root is in sys.path
repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon

from desktop_ui.app import RemoDeskMainWindow
from desktop_ui.resources.icons import get_icon


def load_stylesheet(app: QApplication) -> None:
    """Load and apply the dark theme QSS stylesheet."""
    qss_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "styles", "dark_theme.qss")
    if os.path.exists(qss_path):
        with open(qss_path, "r", encoding="utf-8") as f:
            app.setStyleSheet(f.read())


def main():
    # Set Windows App User Model ID so taskbar grouping and notifications display RemoDesk correctly
    if os.name == "nt":
        try:
            import ctypes
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("RemoDesk.RemoteControl.Desktop.1.2")
        except Exception:
            pass

    app = QApplication(sys.argv)
    app.setApplicationName("RemoDesk")
    app.setOrganizationName("RemoDesk")
    app.setWindowIcon(get_icon("logo", size=32))

    load_stylesheet(app)

    window = RemoDeskMainWindow()

    # If --minimized or -m passed in arguments, start in tray
    if "--minimized" in sys.argv or "-m" in sys.argv:
        window.hide()
    else:
        window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
