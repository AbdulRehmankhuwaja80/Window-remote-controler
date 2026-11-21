"""
RemoDesk Desktop UI - My Device Page
Displays complete host system hardware, network info, partner identifiers, and device properties.
"""

import socket
import platform
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame,
    QGridLayout, QApplication, QLineEdit
)
from PySide6.QtCore import Qt, Signal
from desktop_ui.resources.icons import get_icon


class MyDevicePage(QWidget):
    toast_requested = Signal(str)

    def __init__(self, backend_client, parent=None):
        super().__init__(parent)
        self.backend = backend_client

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(28, 24, 28, 24)
        main_layout.setSpacing(20)

        # ─── Top Overview Card ────────────────────────────────────────────────
        header_card = QFrame()
        header_card.setObjectName("cardElevated")
        header_layout = QHBoxLayout(header_card)
        header_layout.setContentsMargins(22, 18, 22, 18)
        header_layout.setSpacing(16)

        lbl_laptop_icon = QLabel()
        lbl_laptop_icon.setPixmap(get_icon("my_device", "#00D4FF", size=36).pixmap(48, 48))

        vbox_info = QVBoxLayout()
        vbox_info.setSpacing(3)
        self.lbl_device_title = QLabel(socket.gethostname())
        self.lbl_device_title.setStyleSheet("font-size: 20px; font-weight: 800; color: #FFFFFF;")

        self.lbl_device_subtitle = QLabel("Windows 10/11 Personal Laptop Host")
        self.lbl_device_subtitle.setStyleSheet("font-size: 12px; color: #94A3B8;")

        vbox_info.addWidget(self.lbl_device_title)
        vbox_info.addWidget(self.lbl_device_subtitle)

        header_layout.addWidget(lbl_laptop_icon)
        header_layout.addLayout(vbox_info)
        header_layout.addStretch()

        btn_copy_all = QPushButton(" Copy System Specs")
        btn_copy_all.setObjectName("copyButton")
        btn_copy_all.setIcon(get_icon("copy", "#38BDF8", size=14))
        btn_copy_all.clicked.connect(self._copy_all_info)
        header_layout.addWidget(btn_copy_all)

        main_layout.addWidget(header_card)

        # ─── System & Identification Grid ─────────────────────────────────────
        grid_frame = QFrame()
        grid_frame.setObjectName("card")
        grid_layout = QGridLayout(grid_frame)
        grid_layout.setContentsMargins(22, 20, 22, 20)
        grid_layout.setHorizontalSpacing(32)
        grid_layout.setVerticalSpacing(16)

        specs = [
            ("PARTNER IDENTIFIER", "lbl_partner_id", "AbdulRehman"),
            ("DEVICE UUID", "lbl_device_uuid", "96016c4c-d8fa-4e1c-8628-1ad273a7b356"),
            ("LOCAL NETWORK IP", "lbl_local_ip", "192.168.0.43"),
            ("SIGNALLING PORT", "lbl_port", "8000 (TCP / WebSocket)"),
            ("OPERATING SYSTEM", "lbl_os", f"{platform.system()} {platform.release()}"),
            ("SYSTEM ARCHITECTURE", "lbl_arch", platform.machine()),
            ("HOST AGENT ENGINE", "lbl_engine", "DirectX 11 DXGI + Win32 SendInput"),
            ("HOST AGENT VERSION", "lbl_version", "v1.2.0 Commercial Edition"),
        ]

        self.spec_labels = {}
        for idx, (title, key, default_val) in enumerate(specs):
            row = idx // 2
            col = (idx % 2) * 2

            t_lbl = QLabel(title)
            t_lbl.setStyleSheet("font-size: 11px; font-weight: 700; color: #94A3B8; letter-spacing: 0.5px;")

            v_lbl = QLabel(default_val)
            v_lbl.setStyleSheet("font-size: 14px; font-weight: 600; color: #F8FAFC; font-family: monospace;")
            self.spec_labels[key] = v_lbl

            grid_layout.addWidget(t_lbl, row * 2, col)
            grid_layout.addWidget(v_lbl, row * 2 + 1, col)

        main_layout.addWidget(grid_frame)

        # ─── Security Notice Card ─────────────────────────────────────────────
        security_card = QFrame()
        security_card.setObjectName("card")
        sec_layout = QHBoxLayout(security_card)
        sec_layout.setContentsMargins(18, 14, 18, 14)
        sec_layout.setSpacing(12)

        icon_sec = QLabel()
        icon_sec.setPixmap(get_icon("security", "#10B981", size=24).pixmap(24, 24))

        lbl_sec_text = QLabel(
            "<b>Host Authorization Notice:</b> Sensitive authorization keys and certificates are protected "
            "using local Windows user profile encryption. Never share your AuthKey or internal API tokens."
        )
        lbl_sec_text.setStyleSheet("font-size: 12px; color: #CBD5E1; line-height: 1.4;")
        lbl_sec_text.setWordWrap(True)

        sec_layout.addWidget(icon_sec)
        sec_layout.addWidget(lbl_sec_text, stretch=1)
        main_layout.addWidget(security_card)

        main_layout.addStretch()

    def update_data(self, device_info: dict):
        name = device_info.get("device_name") or device_info.get("hostname", "AbdulRehman")
        dev_id = device_info.get("device_id", "N/A")
        net = self.backend.get_network_info()

        self.lbl_device_title.setText(name)
        if "lbl_partner_id" in self.spec_labels:
            self.spec_labels["lbl_partner_id"].setText(name)
        if "lbl_device_uuid" in self.spec_labels:
            self.spec_labels["lbl_device_uuid"].setText(dev_id)
        if "lbl_local_ip" in self.spec_labels:
            self.spec_labels["lbl_local_ip"].setText(net["lan_ip"])
        if "lbl_os" in self.spec_labels:
            self.spec_labels["lbl_os"].setText(net["os_name"])

    def _copy_all_info(self):
        net = self.backend.get_network_info()
        text = (
            f"RemoDesk Host Specifications:\n"
            f"Device Name: {self.lbl_device_title.text()}\n"
            f"Partner ID: {self.spec_labels.get('lbl_partner_id', QLabel()).text()}\n"
            f"Local IP: {net['lan_ip']}:8000\n"
            f"OS: {net['os_name']}\n"
            f"Architecture: {platform.machine()}\n"
            f"Engine: DirectX 11 DXGI + Win32 SendInput\n"
            f"Version: v1.2.0"
        )
        QApplication.clipboard().setText(text)
        self.toast_requested.emit("Complete system specifications copied to clipboard!")
