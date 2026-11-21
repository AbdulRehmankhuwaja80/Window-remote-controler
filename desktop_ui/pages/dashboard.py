"""
RemoDesk Desktop UI - Main Dashboard Page
Displays connection overview, Hero device pairing card, quick actions, and active session status.
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame,
    QGridLayout, QApplication
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QClipboard
from desktop_ui.components.status_card import StatusCard
from desktop_ui.resources.icons import get_icon, get_pixmap


class DashboardPage(QWidget):
    navigate_requested = Signal(int)
    remote_access_toggled = Signal(bool)
    restart_host_requested = Signal()
    regenerate_pin_requested = Signal()
    toast_requested = Signal(str)

    def __init__(self, backend_client, parent=None):
        super().__init__(parent)
        self.backend = backend_client

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(28, 24, 28, 24)
        main_layout.setSpacing(20)

        # ─── 1. Connection Overview Cards (4 Grid) ────────────────────────────
        grid = QGridLayout()
        grid.setSpacing(16)

        self.card_host = StatusCard(
            "dashboard", "Host Agent", "RUNNING", "Port 8000 • Low Latency", "#10B981"
        )
        self.card_remote = StatusCard(
            "remote_access", "Remote Access", "ENABLED", "Ready for connections", "#00D4FF"
        )
        self.card_tunnel = StatusCard(
            "cloud", "Cloudflare Tunnel", "OFFLINE", "Local LAN only", "#94A3B8"
        )
        self.card_lan = StatusCard(
            "wifi", "LAN Address", "192.168.0.43:8000", "Local Wi-Fi Subnet", "#38BDF8"
        )

        grid.addWidget(self.card_host, 0, 0)
        grid.addWidget(self.card_remote, 0, 1)
        grid.addWidget(self.card_tunnel, 1, 0)
        grid.addWidget(self.card_lan, 1, 1)
        main_layout.addLayout(grid)

        # ─── 2. My Device Hero Card (TeamViewer / AnyDesk Style) ──────────────
        self.hero_card = QFrame()
        self.hero_card.setObjectName("heroCard")
        self.hero_card.setStyleSheet("""
            QFrame#heroCard {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #111A2D, stop:1 #14223A);
                border: 1px solid #1E3A8A;
                border-radius: 14px;
                padding: 16px;
            }
        """)

        hero_layout = QVBoxLayout(self.hero_card)
        hero_layout.setContentsMargins(22, 20, 22, 20)
        hero_layout.setSpacing(16)

        header_row = QHBoxLayout()
        lbl_hero_badge = QLabel("THIS COMPUTER (PARTNER DEVICE)")
        lbl_hero_badge.setStyleSheet("font-size: 11px; font-weight: 800; color: #38BDF8; letter-spacing: 1px;")

        self.lbl_device_status_pill = QLabel("● ONLINE")
        self.lbl_device_status_pill.setStyleSheet("""
            background: rgba(16, 185, 129, 0.15);
            color: #10B981;
            border: 1px solid #059669;
            border-radius: 10px;
            padding: 3px 10px;
            font-size: 11px;
            font-weight: 700;
        """)

        header_row.addWidget(lbl_hero_badge)
        header_row.addStretch()
        header_row.addWidget(self.lbl_device_status_pill)
        hero_layout.addLayout(header_row)

        # Partner ID & One-Time PIN Rows
        credentials_row = QHBoxLayout()
        credentials_row.setSpacing(24)

        # Partner ID box
        id_box = QVBoxLayout()
        id_box.setSpacing(4)
        lbl_id_title = QLabel("PARTNER ID (OR LAPTOP NAME)")
        lbl_id_title.setStyleSheet("font-size: 11px; font-weight: 700; color: #94A3B8;")
        self.lbl_partner_id = QLabel("AbdulRehman")
        self.lbl_partner_id.setStyleSheet("font-size: 24px; font-weight: 800; color: #FFFFFF; font-family: monospace;")
        
        btn_copy_id = QPushButton(" Copy Partner ID")
        btn_copy_id.setObjectName("copyButton")
        btn_copy_id.setIcon(get_icon("copy", "#38BDF8", size=14))
        btn_copy_id.clicked.connect(self._copy_partner_id)

        id_box.addWidget(lbl_id_title)
        id_box.addWidget(self.lbl_partner_id)
        id_box.addWidget(btn_copy_id, alignment=Qt.AlignLeft)
        credentials_row.addLayout(id_box)

        # Vertical separator
        sep = QFrame()
        sep.setFrameShape(QFrame.VLine)
        sep.setStyleSheet("color: #283953;")
        credentials_row.addWidget(sep)

        # Six-digit PIN box
        pin_box = QVBoxLayout()
        pin_box.setSpacing(4)
        lbl_pin_title = QLabel("ONE-TIME PAIRING PIN")
        lbl_pin_title.setStyleSheet("font-size: 11px; font-weight: 700; color: #94A3B8;")
        self.lbl_pin = QLabel("867902")
        self.lbl_pin.setStyleSheet("font-size: 26px; font-weight: 900; color: #00D4FF; letter-spacing: 4px; font-family: monospace;")

        pin_actions = QHBoxLayout()
        pin_actions.setSpacing(8)
        
        btn_copy_pin = QPushButton(" Copy PIN")
        btn_copy_pin.setObjectName("copyButton")
        btn_copy_pin.setIcon(get_icon("copy", "#38BDF8", size=14))
        btn_copy_pin.clicked.connect(self._copy_pin)

        btn_regen_pin = QPushButton(" Regenerate PIN")
        btn_regen_pin.setObjectName("copyButton")
        btn_regen_pin.setIcon(get_icon("refresh", "#38BDF8", size=14))
        btn_regen_pin.clicked.connect(self.regenerate_pin_requested.emit)

        pin_actions.addWidget(btn_copy_pin)
        pin_actions.addWidget(btn_regen_pin)

        pin_box.addWidget(lbl_pin_title)
        pin_box.addWidget(self.lbl_pin)
        pin_box.addLayout(pin_actions)
        credentials_row.addLayout(pin_box)

        hero_layout.addLayout(credentials_row)

        lbl_notice = QLabel("🔒 Share this Partner ID and PIN only with trusted people or your personal Android phone.")
        lbl_notice.setStyleSheet("font-size: 11.5px; color: #64748B; margin-top: 4px;")
        hero_layout.addWidget(lbl_notice)

        main_layout.addWidget(self.hero_card)

        # ─── 3. Quick Actions Bar ─────────────────────────────────────────────
        actions_frame = QFrame()
        actions_frame.setObjectName("card")
        actions_frame.setStyleSheet("""
            QFrame#card {
                background-color: #141D2D;
                border: 1px solid #202D42;
                border-radius: 12px;
                padding: 14px;
            }
        """)
        actions_layout = QVBoxLayout(actions_frame)
        actions_layout.setContentsMargins(16, 12, 16, 12)
        actions_layout.setSpacing(10)

        lbl_actions_title = QLabel("QUICK ACTIONS")
        lbl_actions_title.setStyleSheet("font-size: 11px; font-weight: 700; color: #94A3B8; letter-spacing: 0.5px;")
        actions_layout.addWidget(lbl_actions_title)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(12)

        self.btn_toggle_remote = QPushButton(" Pause Remote Access")
        self.btn_toggle_remote.setObjectName("primaryButton")
        self.btn_toggle_remote.setIcon(get_icon("stop", "#FFFFFF", size=16))
        self.btn_toggle_remote.clicked.connect(self._toggle_remote_access)

        self.btn_restart_host = QPushButton(" Restart Host Agent")
        self.btn_restart_host.setIcon(get_icon("refresh", "#E2E8F0", size=16))
        self.btn_restart_host.clicked.connect(self.restart_host_requested.emit)

        self.btn_open_files = QPushButton(" Open File Manager")
        self.btn_open_files.setIcon(get_icon("folder", "#E2E8F0", size=16))
        self.btn_open_files.clicked.connect(lambda: self.navigate_requested.emit(4))  # Index 4 is File Transfer

        self.btn_view_logs = QPushButton(" View Security Logs")
        self.btn_view_logs.setIcon(get_icon("security", "#E2E8F0", size=16))
        self.btn_view_logs.clicked.connect(lambda: self.navigate_requested.emit(5))  # Index 5 is Security

        btn_row.addWidget(self.btn_toggle_remote)
        btn_row.addWidget(self.btn_restart_host)
        btn_row.addWidget(self.btn_open_files)
        btn_row.addWidget(self.btn_view_logs)
        actions_layout.addLayout(btn_row)

        main_layout.addWidget(actions_frame)
        main_layout.addStretch()

        self.is_remote_enabled = True

    # ─── Action Handlers ──────────────────────────────────────────────────────

    def _copy_partner_id(self):
        text = self.lbl_partner_id.text().strip()
        QApplication.clipboard().setText(text)
        self.toast_requested.emit(f"Partner ID '{text}' copied to clipboard!")

    def _copy_pin(self):
        text = self.lbl_pin.text().strip()
        QApplication.clipboard().setText(text)
        self.toast_requested.emit(f"Pairing PIN '{text}' copied to clipboard!")

    def _toggle_remote_access(self):
        self.is_remote_enabled = not self.is_remote_enabled
        self.remote_access_toggled.emit(self.is_remote_enabled)
        self.update_remote_button(self.is_remote_enabled)

    def update_remote_button(self, enabled: bool):
        self.is_remote_enabled = enabled
        if enabled:
            self.btn_toggle_remote.setText(" Pause Remote Access")
            self.btn_toggle_remote.setIcon(get_icon("stop", "#FFFFFF", size=16))
            self.card_remote.update_card("ENABLED", "Ready for connections", "#00D4FF")
        else:
            self.btn_toggle_remote.setText(" Enable Remote Access")
            self.btn_toggle_remote.setIcon(get_icon("play", "#FFFFFF", size=16))
            self.card_remote.update_card("PAUSED", "Incoming connections blocked", "#F59E0B")

    def update_data(self, device_info: dict, health_info: dict, tunnel_active: bool, tunnel_url: str = ""):
        # Partner ID & PIN
        name = device_info.get("device_name") or device_info.get("hostname", "AbdulRehman")
        pin = device_info.get("pairing_code", "867902")
        self.lbl_partner_id.setText(name)
        self.lbl_pin.setText(pin)

        # Host Agent Status
        active_hosts = health_info.get("active_hosts", 0)
        if active_hosts > 0:
            self.card_host.update_card("RUNNING", f"Host Agent Online • 0 active sessions", "#10B981")
            self.lbl_device_status_pill.setText("● ONLINE")
            self.lbl_device_status_pill.setStyleSheet("""
                background: rgba(16, 185, 129, 0.15); color: #10B981; border: 1px solid #059669; border-radius: 10px; padding: 3px 10px; font-size: 11px; font-weight: 700;
            """)
        else:
            self.card_host.update_card("STOPPED", "Host Agent process not connected", "#EF4444")
            self.lbl_device_status_pill.setText("○ OFFLINE")
            self.lbl_device_status_pill.setStyleSheet("""
                background: rgba(239, 68, 68, 0.15); color: #EF4444; border: 1px solid #DC2626; border-radius: 10px; padding: 3px 10px; font-size: 11px; font-weight: 700;
            """)

        # Tunnel Status
        if tunnel_active and tunnel_url:
            self.card_tunnel.update_card("ACTIVE", "Worldwide Edge Connected", "#10B981")
        else:
            self.card_tunnel.update_card("OFFLINE", "Local LAN connection only", "#94A3B8")

        # LAN status
        net_info = self.backend.get_network_info()
        self.card_lan.update_card(f"{net_info['lan_ip']}:8000", "Local Wi-Fi Subnet", "#38BDF8")

        # Remote toggle
        enabled = device_info.get("is_remote_enabled", True)
        self.update_remote_button(enabled)
