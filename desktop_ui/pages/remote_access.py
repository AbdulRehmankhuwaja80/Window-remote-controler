"""
RemoDesk Desktop UI - Remote Access Configuration Page
Displays Local LAN and Worldwide Cloudflare Tunnel connectivity with start/stop controls.
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame,
    QGridLayout, QApplication, QTextEdit
)
from PySide6.QtCore import Qt, Signal
from desktop_ui.resources.icons import get_icon


class RemoteAccessPage(QWidget):
    start_tunnel_requested = Signal()
    stop_tunnel_requested = Signal()
    toast_requested = Signal(str)

    def __init__(self, backend_client, parent=None):
        super().__init__(parent)
        self.backend = backend_client

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(28, 24, 28, 24)
        main_layout.setSpacing(20)

        # ─── Two-Column Connection Cards ──────────────────────────────────────
        cards_row = QHBoxLayout()
        cards_row.setSpacing(20)

        # 1. LAN Connection Card
        lan_card = QFrame()
        lan_card.setObjectName("card")
        lan_layout = QVBoxLayout(lan_card)
        lan_layout.setContentsMargins(22, 20, 22, 20)
        lan_layout.setSpacing(14)

        lan_header = QHBoxLayout()
        icon_wifi = QLabel()
        icon_wifi.setPixmap(get_icon("wifi", "#38BDF8", size=24).pixmap(24, 24))
        lbl_lan_title = QLabel("LOCAL WI-FI (LAN)")
        lbl_lan_title.setStyleSheet("font-size: 14px; font-weight: 800; color: #FFFFFF;")
        
        self.badge_lan = QLabel("● ACTIVE")
        self.badge_lan.setStyleSheet("""
            background: rgba(16, 185, 129, 0.15);
            color: #10B981;
            border: 1px solid #059669;
            border-radius: 10px;
            padding: 3px 10px;
            font-size: 11px;
            font-weight: 700;
        """)

        lan_header.addWidget(icon_wifi)
        lan_header.addWidget(lbl_lan_title)
        lan_header.addStretch()
        lan_header.addWidget(self.badge_lan)
        lan_layout.addLayout(lan_header)

        lbl_lan_desc = QLabel(
            "Direct ultra low-latency connection when your Android smartphone and laptop are connected "
            "to the same home or office Wi-Fi router."
        )
        lbl_lan_desc.setStyleSheet("font-size: 12px; color: #94A3B8; line-height: 1.4;")
        lbl_lan_desc.setWordWrap(True)
        lan_layout.addWidget(lbl_lan_desc)

        # LAN URL Box
        lan_url_frame = QFrame()
        lan_url_frame.setStyleSheet("""
            background-color: #0E1626;
            border: 1px dashed #2E466E;
            border-radius: 8px;
            padding: 10px;
        """)
        url_vbox = QVBoxLayout(lan_url_frame)
        url_vbox.setSpacing(2)
        lbl_box_title = QLabel("GATEWAY SERVER URL FOR PHONE APP:")
        lbl_box_title.setStyleSheet("font-size: 10px; font-weight: 700; color: #64748B;")
        
        self.lbl_lan_url = QLabel("http://192.168.0.43:8000")
        self.lbl_lan_url.setStyleSheet("font-size: 16px; font-weight: 800; color: #38BDF8; font-family: monospace;")
        
        url_vbox.addWidget(lbl_box_title)
        url_vbox.addWidget(self.lbl_lan_url)
        lan_layout.addWidget(lan_url_frame)

        btn_copy_lan = QPushButton(" Copy LAN Gateway URL")
        btn_copy_lan.setObjectName("copyButton")
        btn_copy_lan.setIcon(get_icon("copy", "#38BDF8", size=14))
        btn_copy_lan.clicked.connect(self._copy_lan_url)
        lan_layout.addWidget(btn_copy_lan)

        lan_layout.addStretch()
        cards_row.addWidget(lan_card)

        # 2. Worldwide Cloudflare Tunnel Card
        tunnel_card = QFrame()
        tunnel_card.setObjectName("cardElevated")
        tunnel_layout = QVBoxLayout(tunnel_card)
        tunnel_layout.setContentsMargins(22, 20, 22, 20)
        tunnel_layout.setSpacing(14)

        tunnel_header = QHBoxLayout()
        icon_cloud = QLabel()
        icon_cloud.setPixmap(get_icon("cloud", "#00D4FF", size=24).pixmap(24, 24))
        lbl_tunnel_title = QLabel("WORLDWIDE ACCESS (INTERNET)")
        lbl_tunnel_title.setStyleSheet("font-size: 14px; font-weight: 800; color: #FFFFFF;")

        self.badge_tunnel = QLabel("○ OFFLINE")
        self.badge_tunnel.setStyleSheet("""
            background: rgba(148, 163, 184, 0.15);
            color: #94A3B8;
            border: 1px solid #475569;
            border-radius: 10px;
            padding: 3px 10px;
            font-size: 11px;
            font-weight: 700;
        """)

        tunnel_header.addWidget(icon_cloud)
        tunnel_header.addWidget(lbl_tunnel_title)
        tunnel_header.addStretch()
        tunnel_header.addWidget(self.badge_tunnel)
        tunnel_layout.addLayout(tunnel_header)

        lbl_tunnel_desc = QLabel(
            "Connect from outside networks, office Wi-Fi, or cellular mobile data (4G/5G) from anywhere "
            "in the world via secure encrypted Cloudflare Edge Tunnel. No port forwarding required."
        )
        lbl_tunnel_desc.setStyleSheet("font-size: 12px; color: #94A3B8; line-height: 1.4;")
        lbl_tunnel_desc.setWordWrap(True)
        tunnel_layout.addWidget(lbl_tunnel_desc)

        # Public Tunnel URL Box
        tunnel_url_frame = QFrame()
        tunnel_url_frame.setStyleSheet("""
            background-color: #0E1626;
            border: 1px dashed #0284C7;
            border-radius: 8px;
            padding: 10px;
        """)
        t_url_vbox = QVBoxLayout(tunnel_url_frame)
        t_url_vbox.setSpacing(2)
        lbl_tbox_title = QLabel("PUBLIC WORLDWIDE TUNNEL URL:")
        lbl_tbox_title.setStyleSheet("font-size: 10px; font-weight: 700; color: #64748B;")

        self.lbl_tunnel_url = QLabel("Tunnel inactive (Click Start below)")
        self.lbl_tunnel_url.setStyleSheet("font-size: 14px; font-weight: 700; color: #00D4FF; font-family: monospace;")

        t_url_vbox.addWidget(lbl_tbox_title)
        t_url_vbox.addWidget(self.lbl_tunnel_url)
        tunnel_layout.addWidget(tunnel_url_frame)

        # Tunnel control buttons
        btn_tunnel_row = QHBoxLayout()
        btn_tunnel_row.setSpacing(10)

        self.btn_toggle_tunnel = QPushButton(" Start Worldwide Tunnel")
        self.btn_toggle_tunnel.setObjectName("primaryButton")
        self.btn_toggle_tunnel.setIcon(get_icon("play", "#FFFFFF", size=15))
        self.btn_toggle_tunnel.clicked.connect(self._toggle_tunnel)

        self.btn_copy_tunnel = QPushButton(" Copy URL")
        self.btn_copy_tunnel.setObjectName("copyButton")
        self.btn_copy_tunnel.setIcon(get_icon("copy", "#38BDF8", size=14))
        self.btn_copy_tunnel.setEnabled(False)
        self.btn_copy_tunnel.clicked.connect(self._copy_tunnel_url)

        btn_tunnel_row.addWidget(self.btn_toggle_tunnel)
        btn_tunnel_row.addWidget(self.btn_copy_tunnel)
        tunnel_layout.addLayout(btn_tunnel_row)

        tunnel_layout.addStretch()
        cards_row.addWidget(tunnel_card)

        main_layout.addLayout(cards_row)

        # ─── Live Tunnel Logs Console ─────────────────────────────────────────
        logs_frame = QFrame()
        logs_frame.setObjectName("card")
        logs_layout = QVBoxLayout(logs_frame)
        logs_layout.setContentsMargins(18, 14, 18, 14)
        logs_layout.setSpacing(8)

        lbl_console_title = QLabel("NETWORK & TUNNEL LOG CONSOLE")
        lbl_console_title.setStyleSheet("font-size: 11px; font-weight: 700; color: #94A3B8; letter-spacing: 0.5px;")
        logs_layout.addWidget(lbl_console_title)

        self.console = QTextEdit()
        self.console.setReadOnly(True)
        self.console.setStyleSheet("""
            QTextEdit {
                background-color: #0A0E17;
                border: 1px solid #1A263B;
                border-radius: 6px;
                color: #A5B4FC;
                font-family: monospace;
                font-size: 11.5px;
            }
        """)
        self.console.setFixedHeight(120)
        self.console.append("[System] RemoDesk Gateway is listening on 0.0.0.0:8000")
        logs_layout.addWidget(self.console)

        main_layout.addWidget(logs_frame)
        self.is_tunnel_active = False

    def _copy_lan_url(self):
        url = self.lbl_lan_url.text().strip()
        QApplication.clipboard().setText(url)
        self.toast_requested.emit(f"LAN URL '{url}' copied to clipboard!")

    def _copy_tunnel_url(self):
        url = self.lbl_tunnel_url.text().strip()
        QApplication.clipboard().setText(url)
        self.toast_requested.emit(f"Public Worldwide URL copied to clipboard!")

    def _toggle_tunnel(self):
        if self.is_tunnel_active:
            self.stop_tunnel_requested.emit()
        else:
            self.start_tunnel_requested.emit()

    def set_tunnel_state(self, active: bool, url: str = ""):
        self.is_tunnel_active = active
        if active and url:
            self.badge_tunnel.setText("● ACTIVE")
            self.badge_tunnel.setStyleSheet("""
                background: rgba(16, 185, 129, 0.15); color: #10B981; border: 1px solid #059669; border-radius: 10px; padding: 3px 10px; font-size: 11px; font-weight: 700;
            """)
            self.lbl_tunnel_url.setText(url)
            self.btn_toggle_tunnel.setText(" Stop Worldwide Tunnel")
            self.btn_toggle_tunnel.setIcon(get_icon("stop", "#FFFFFF", size=15))
            self.btn_copy_tunnel.setEnabled(True)
            self.console.append(f"[Cloudflare] Connected to Edge Network: {url}")
        else:
            self.badge_tunnel.setText("○ OFFLINE")
            self.badge_tunnel.setStyleSheet("""
                background: rgba(148, 163, 184, 0.15); color: #94A3B8; border: 1px solid #475569; border-radius: 10px; padding: 3px 10px; font-size: 11px; font-weight: 700;
            """)
            self.lbl_tunnel_url.setText("Tunnel inactive (Click Start below)")
            self.btn_toggle_tunnel.setText(" Start Worldwide Tunnel")
            self.btn_toggle_tunnel.setIcon(get_icon("play", "#FFFFFF", size=15))
            self.btn_copy_tunnel.setEnabled(False)
            self.console.append("[Cloudflare] Tunnel stopped.")

    def append_log(self, text: str):
        self.console.append(text)

    def update_lan_info(self, lan_ip: str):
        self.lbl_lan_url.setText(f"http://{lan_ip}:8000")
