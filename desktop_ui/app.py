"""
RemoDesk Desktop UI - Main Application Window
Orchestrates sidebar navigation, pages, system tray, background services, and real-time state sync.
"""

import os
import sys
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QStackedWidget,
    QApplication, QMessageBox
)
from PySide6.QtCore import Qt, QTimer, Slot
from PySide6.QtGui import QIcon, QCloseEvent

from desktop_ui.components.sidebar import Sidebar
from desktop_ui.components.header import HeaderBar
from desktop_ui.components.toast import ToastNotification

from desktop_ui.pages.dashboard import DashboardPage
from desktop_ui.pages.my_device import MyDevicePage
from desktop_ui.pages.remote_access import RemoteAccessPage
from desktop_ui.pages.connected_devices import ConnectedDevicesPage
from desktop_ui.pages.file_transfer import FileTransferPage
from desktop_ui.pages.security import SecurityPage
from desktop_ui.pages.settings import SettingsPage
from desktop_ui.pages.about import AboutPage

from desktop_ui.services.backend_client import BackendClient
from desktop_ui.services.host_controller import HostController
from desktop_ui.services.tunnel_controller import TunnelController
from desktop_ui.services.system_tray import SystemTrayManager
from desktop_ui.resources.icons import get_icon


class RemoDeskMainWindow(QMainWindow):
    PAGE_HEADERS = [
        ("Dashboard", "Overview & Remote Access Control"),
        ("My Device", "Hardware Specifications & Network Identity"),
        ("Remote Access", "Direct LAN and Worldwide Cloudflare Tunnel"),
        ("Connected Devices", "Paired Mobile Clients & Active Remote Sessions"),
        ("File Transfer", "Sandboxed File Manager & Transfer Activity"),
        ("Security Guards", "Access Policies, PIN Management & Audit Trail"),
        ("Settings", "Windows Startup, Video Quality & Application Preferences"),
        ("About RemoDesk", "System Architecture & Commercial License"),
    ]

    def __init__(self):
        super().__init__()
        self.setWindowTitle("RemoDesk — Remote Desktop Control System")
        self.resize(1120, 720)
        self.setMinimumSize(960, 640)
        self.setWindowIcon(get_icon("logo", size=32))

        # Core services
        self.backend = BackendClient()
        self.host_ctrl = HostController()
        self.tunnel_ctrl = TunnelController()
        self.tray = SystemTrayManager(self)

        self._force_exit = False

        # Central Layout
        central = QWidget()
        self.setCentralWidget(central)
        root_layout = QHBoxLayout(central)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # 1. Sidebar (Fixed width on left)
        self.sidebar = Sidebar(self)
        self.sidebar.page_selected.connect(self._on_page_selected)
        root_layout.addWidget(self.sidebar)

        # 2. Right Content Area (Header + Stacked Pages)
        content_vbox = QVBoxLayout()
        content_vbox.setContentsMargins(0, 0, 0, 0)
        content_vbox.setSpacing(0)

        self.header = HeaderBar(self)
        self.header.refresh_clicked.connect(self.refresh_all_data)
        content_vbox.addWidget(self.header)

        self.stack = QStackedWidget()
        self.stack.setStyleSheet("background-color: #0A0E17;")

        # Instantiate all 8 pages
        self.page_dashboard = DashboardPage(self.backend, self)
        self.page_my_device = MyDevicePage(self.backend, self)
        self.page_remote_access = RemoteAccessPage(self.backend, self)
        self.page_connected_devices = ConnectedDevicesPage(self.backend, self)
        self.page_file_transfer = FileTransferPage(self.backend, self)
        self.page_security = SecurityPage(self.backend, self)
        self.page_settings = SettingsPage(self.backend, self)
        self.page_about = AboutPage(self.backend, self)

        self.stack.addWidget(self.page_dashboard)
        self.stack.addWidget(self.page_my_device)
        self.stack.addWidget(self.page_remote_access)
        self.stack.addWidget(self.page_connected_devices)
        self.stack.addWidget(self.page_file_transfer)
        self.stack.addWidget(self.page_security)
        self.stack.addWidget(self.page_settings)
        self.stack.addWidget(self.page_about)

        content_vbox.addWidget(self.stack)
        root_layout.addLayout(content_vbox)

        # In-app Toast Banner
        self.toast = ToastNotification(self)

        # Connect inter-page and service signals
        self._wire_signals()

        # Startup check: Ensure backend & host agent are active
        self._startup_services()

        # Real-time state polling timer (every 3.5 seconds)
        self.poll_timer = QTimer(self)
        self.poll_timer.timeout.connect(self.refresh_all_data)
        self.poll_timer.start(3500)

        # Initial refresh
        self.refresh_all_data()

    def _wire_signals(self):
        # Navigation requests from dashboard quick actions
        self.page_dashboard.navigate_requested.connect(self.navigate_to_page)
        self.page_dashboard.remote_access_toggled.connect(self._on_remote_access_toggled)
        self.page_dashboard.restart_host_requested.connect(self._restart_host_agent)
        self.page_dashboard.regenerate_pin_requested.connect(self._regenerate_pin)
        self.page_dashboard.toast_requested.connect(self.show_toast)

        self.page_my_device.toast_requested.connect(self.show_toast)

        # Remote Access Tunnel controls
        self.page_remote_access.start_tunnel_requested.connect(self._start_tunnel)
        self.page_remote_access.stop_tunnel_requested.connect(self._stop_tunnel)
        self.page_remote_access.toast_requested.connect(self.show_toast)
        self.tunnel_ctrl.tunnel_started.connect(self._on_tunnel_started)
        self.tunnel_ctrl.tunnel_stopped.connect(self._on_tunnel_stopped)
        self.tunnel_ctrl.log_line.connect(self.page_remote_access.append_log)

        self.page_connected_devices.toast_requested.connect(self.show_toast)
        self.page_file_transfer.toast_requested.connect(self.show_toast)

        self.page_security.regenerate_pin_requested.connect(self._regenerate_pin)
        self.page_security.toast_requested.connect(self.show_toast)

        self.page_settings.toast_requested.connect(self.show_toast)
        self.page_about.toast_requested.connect(self.show_toast)

        # System Tray actions
        self.tray.show_window_requested.connect(self._restore_from_tray)
        self.tray.toggle_remote_access_requested.connect(lambda: self._on_remote_access_toggled(not self.page_dashboard.is_remote_enabled))
        self.tray.toggle_tunnel_requested.connect(self._toggle_tunnel_from_tray)
        self.tray.copy_partner_id_requested.connect(self.page_dashboard._copy_partner_id)
        self.tray.copy_pin_requested.connect(self.page_dashboard._copy_pin)
        self.tray.exit_requested.connect(self._exit_application)

    def _startup_services(self):
        # Auto-ensure backend is alive
        self.host_ctrl.ensure_backend_running()

    # ─── Page Navigation ──────────────────────────────────────────────────────

    @Slot(int)
    def _on_page_selected(self, index: int):
        if 0 <= index < self.stack.count():
            self.stack.setCurrentIndex(index)
            title, subtitle = self.PAGE_HEADERS[index]
            self.header.set_page_header(title, subtitle)

    def navigate_to_page(self, index: int):
        self.sidebar.set_current_index(index)

    # ─── Service Actions ──────────────────────────────────────────────────────

    def _on_remote_access_toggled(self, enabled: bool):
        self.backend.set_remote_access_enabled(enabled)
        self.page_dashboard.update_remote_button(enabled)
        status_msg = "Remote access is now ENABLED." if enabled else "Remote access is now PAUSED."
        self.show_toast(status_msg)
        self.refresh_all_data()

    def _restart_host_agent(self):
        self.show_toast("Restarting RemoDesk Host Agent...")
        ok = self.host_ctrl.restart_host()
        if ok:
            self.show_toast("Host Agent restarted successfully!")
        else:
            self.show_toast("Host Agent restart failed. Check logs.")
        self.refresh_all_data()

    def _regenerate_pin(self):
        new_pin = self.backend.regenerate_pairing_pin()
        if new_pin:
            self.page_dashboard.lbl_pin.setText(new_pin)
            self.page_security.update_pin(new_pin)
            self.show_toast(f"New One-Time PIN generated: {new_pin}")
            self.tray.show_message("RemoDesk PIN Updated", f"New Pairing PIN is: {new_pin}")
            self.refresh_all_data()

    def _start_tunnel(self):
        self.show_toast("Starting Cloudflare Secure Edge Tunnel...")
        ok = self.tunnel_ctrl.start_tunnel()
        if not ok:
            self.show_toast("Could not start tunnel. Verify cloudflared.exe exists.")

    def _stop_tunnel(self):
        self.tunnel_ctrl.stop_tunnel()
        self.show_toast("Cloudflare Tunnel disconnected.")

    def _toggle_tunnel_from_tray(self):
        if self.tunnel_ctrl.is_tunnel_running():
            self._stop_tunnel()
        else:
            self._start_tunnel()

    def _on_tunnel_started(self, url: str):
        self.page_remote_access.set_tunnel_state(True, url)
        self.show_toast("Worldwide Cloudflare Tunnel is LIVE!")
        self.tray.show_message("Worldwide Access Active", f"Connected to Cloudflare Edge:\n{url}")
        self.refresh_all_data()

    def _on_tunnel_stopped(self):
        self.page_remote_access.set_tunnel_state(False)
        self.refresh_all_data()

    # ─── Live State Polling ───────────────────────────────────────────────────

    def refresh_all_data(self):
        health = self.backend.get_gateway_health()
        dev_info = self.backend.get_device_info()
        net_info = self.backend.get_network_info()
        tunnel_active = self.tunnel_ctrl.is_tunnel_running()
        tunnel_url = self.tunnel_ctrl.get_public_url() or ""

        host_running = health.get("active_hosts", 0) > 0 or self.host_ctrl.is_host_running()
        gateway_online = health.get("online", False)
        remote_enabled = dev_info.get("is_remote_enabled", True)

        # Header Badges
        self.header.update_badges(host_running, gateway_online, remote_enabled)

        # Sidebar indicator
        self.sidebar.update_status(host_running, f"{net_info['lan_ip']}:8000")

        # Dashboard Page
        self.page_dashboard.update_data(dev_info, health, tunnel_active, tunnel_url)

        # My Device Page
        self.page_my_device.update_data(dev_info)

        # Remote Access Page
        self.page_remote_access.update_lan_info(net_info["lan_ip"])

        # Security Page
        self.page_security.update_pin(dev_info.get("pairing_code", "867902"))

        # Tray Icon update
        self.tray.update_status(
            is_online=host_running,
            is_remote_enabled=remote_enabled,
            is_tunnel_active=tunnel_active,
            pin=dev_info.get("pairing_code", "")
        )

    # ─── Window & System Tray Behavior ────────────────────────────────────────

    def show_toast(self, message: str):
        self.toast.show_message(message)

    def _restore_from_tray(self):
        self.show()
        self.setWindowState(self.windowState() & ~Qt.WindowMinimized | Qt.WindowActive)
        self.activateWindow()
        self.raise_()

    def _exit_application(self):
        self._force_exit = True
        self.tunnel_ctrl.stop_tunnel()
        QApplication.quit()

    def closeEvent(self, event: QCloseEvent):
        # If user explicitly clicked Exit from tray or file menu, quit
        if self._force_exit or not self.page_settings.chk_minimize_tray.isChecked():
            self.tunnel_ctrl.stop_tunnel()
            event.accept()
        else:
            # Minimize to tray instead of closing
            event.ignore()
            self.hide()
            self.tray.show_message(
                "RemoDesk Running in Background",
                "The dashboard is minimized to the system tray. Your laptop remains accessible for remote control.",
                timeout=3000
            )

    def resizeEvent(self, event):
        super().resizeEvent(event)
        # Keep toast centered on resize
        if self.toast.isVisible():
            w = max(self.toast.width(), 260)
            self.toast.setGeometry((self.width() - w) // 2, self.height() - 75, w, 44)
