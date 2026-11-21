"""
RemoDesk Desktop UI - System Tray Service
Manages Windows taskbar notification area icon, context menu, and balloon notifications.
"""

from PySide6.QtWidgets import QSystemTrayIcon, QMenu
from PySide6.QtGui import QIcon, QAction
from PySide6.QtCore import QObject, Signal
from desktop_ui.resources.icons import get_icon


class SystemTrayManager(QObject):
    show_window_requested = Signal()
    toggle_remote_access_requested = Signal()
    toggle_tunnel_requested = Signal()
    copy_partner_id_requested = Signal()
    copy_pin_requested = Signal()
    exit_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.tray_icon = QSystemTrayIcon(parent)
        self.tray_icon.setIcon(get_icon("logo", size=32))
        self.tray_icon.setToolTip("RemoDesk Remote Desktop")

        self._build_menu()
        self.tray_icon.activated.connect(self._on_activated)
        self.tray_icon.show()

    def _build_menu(self):
        self.menu = QMenu()
        self.menu.setStyleSheet("""
            QMenu {
                background-color: #141D2D;
                border: 1px solid #283953;
                border-radius: 8px;
                padding: 6px;
            }
            QMenu::item {
                color: #F8FAFC;
                padding: 6px 24px 6px 12px;
                border-radius: 4px;
                font-weight: 500;
            }
            QMenu::item:selected {
                background-color: #0066FF;
                color: #FFFFFF;
            }
            QMenu::separator {
                height: 1px;
                background-color: #283953;
                margin: 4px 8px;
            }
        """)

        # Show / Restore Action
        self.action_show = QAction(get_icon("dashboard", "#38BDF8"), "Open RemoDesk Dashboard", self.menu)
        self.action_show.triggered.connect(self.show_window_requested.emit)
        self.menu.addAction(self.action_show)

        self.menu.addSeparator()

        # Remote Access Toggle Action
        self.action_toggle_remote = QAction(get_icon("remote_access", "#10B981"), "Pause Remote Access", self.menu)
        self.action_toggle_remote.triggered.connect(self.toggle_remote_access_requested.emit)
        self.menu.addAction(self.action_toggle_remote)

        # Tunnel Toggle Action
        self.action_toggle_tunnel = QAction(get_icon("cloud", "#38BDF8"), "Start Worldwide Tunnel", self.menu)
        self.action_toggle_tunnel.triggered.connect(self.toggle_tunnel_requested.emit)
        self.menu.addAction(self.action_toggle_tunnel)

        self.menu.addSeparator()

        # Quick Copy Actions
        self.action_copy_id = QAction(get_icon("copy", "#94A3B8"), "Copy Partner ID", self.menu)
        self.action_copy_id.triggered.connect(self.copy_partner_id_requested.emit)
        self.menu.addAction(self.action_copy_id)

        self.action_copy_pin = QAction(get_icon("key", "#94A3B8"), "Copy Pairing PIN", self.menu)
        self.action_copy_pin.triggered.connect(self.copy_pin_requested.emit)
        self.menu.addAction(self.action_copy_pin)

        self.menu.addSeparator()

        # Exit
        self.action_exit = QAction(get_icon("stop", "#EF4444"), "Exit RemoDesk", self.menu)
        self.action_exit.triggered.connect(self.exit_requested.emit)
        self.menu.addAction(self.action_exit)

        self.tray_icon.setContextMenu(self.menu)

    def _on_activated(self, reason):
        if reason in (QSystemTrayIcon.Trigger, QSystemTrayIcon.DoubleClick):
            self.show_window_requested.emit()

    def update_status(self, is_online: bool, is_remote_enabled: bool, is_tunnel_active: bool, pin: str = ""):
        tooltip = f"RemoDesk • {'Online' if is_online else 'Offline'}"
        if pin:
            tooltip += f" (PIN: {pin})"
        self.tray_icon.setToolTip(tooltip)

        if is_remote_enabled:
            self.action_toggle_remote.setText("Pause Remote Access")
            self.action_toggle_remote.setIcon(get_icon("stop", "#F59E0B"))
        else:
            self.action_toggle_remote.setText("Enable Remote Access")
            self.action_toggle_remote.setIcon(get_icon("play", "#10B981"))

        if is_tunnel_active:
            self.action_toggle_tunnel.setText("Stop Worldwide Tunnel")
            self.action_toggle_tunnel.setIcon(get_icon("stop", "#EF4444"))
        else:
            self.action_toggle_tunnel.setText("Start Worldwide Tunnel")
            self.action_toggle_tunnel.setIcon(get_icon("cloud", "#38BDF8"))

    def show_message(self, title: str, message: str, icon=QSystemTrayIcon.Information, timeout: int = 4000):
        if self.tray_icon.isVisible():
            self.tray_icon.showMessage(title, message, icon, timeout)
