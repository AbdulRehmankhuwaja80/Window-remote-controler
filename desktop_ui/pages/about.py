"""
RemoDesk Desktop UI - About & System Information Page
Displays version specs, architecture details, licenses, and diagnostics.
"""

import sys
import webbrowser
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame,
    QApplication
)
from PySide6.QtCore import Qt, Signal
from desktop_ui.resources.icons import get_icon, get_pixmap


class AboutPage(QWidget):
    toast_requested = Signal(str)

    def __init__(self, backend_client, parent=None):
        super().__init__(parent)
        self.backend = backend_client

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(28, 24, 28, 24)
        main_layout.setSpacing(20)

        # ─── Brand Banner Card ────────────────────────────────────────────────
        brand_card = QFrame()
        brand_card.setObjectName("heroCard")
        brand_card.setStyleSheet("""
            QFrame#heroCard {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #0F172A, stop:1 #1E293B);
                border: 1px solid #1E3A8A;
                border-radius: 14px;
                padding: 16px;
            }
        """)
        brand_layout = QHBoxLayout(brand_card)
        brand_layout.setContentsMargins(24, 20, 24, 20)
        brand_layout.setSpacing(18)

        lbl_logo = QLabel()
        lbl_logo.setPixmap(get_pixmap("logo", size=48))
        lbl_logo.setFixedSize(56, 56)

        title_vbox = QVBoxLayout()
        title_vbox.setSpacing(2)
        lbl_app_name = QLabel("RemoDesk Remote Control")
        lbl_app_name.setStyleSheet("font-size: 22px; font-weight: 900; color: #FFFFFF;")
        
        lbl_version_tag = QLabel("Version 1.2.0 • Commercial Windows Edition (Python 3.14 + PySide6 Qt 6.12)")
        lbl_version_tag.setStyleSheet("font-size: 12px; color: #00D4FF; font-weight: 600;")

        title_vbox.addWidget(lbl_app_name)
        title_vbox.addWidget(lbl_version_tag)

        brand_layout.addWidget(lbl_logo)
        brand_layout.addLayout(title_vbox)
        brand_layout.addStretch()

        btn_github = QPushButton(" View GitHub Repository")
        btn_github.setObjectName("primaryButton")
        btn_github.setIcon(get_icon("about", "#FFFFFF", size=14))
        btn_github.clicked.connect(lambda: webbrowser.open("https://github.com/AbdulRehmankhuwaja80/Window-remote-controler"))
        brand_layout.addWidget(btn_github)

        main_layout.addWidget(brand_card)

        # ─── System Architecture Highlights ───────────────────────────────────
        arch_card = QFrame()
        arch_card.setObjectName("card")
        arch_layout = QVBoxLayout(arch_card)
        arch_layout.setContentsMargins(22, 18, 22, 18)
        arch_layout.setSpacing(12)

        lbl_arch_title = QLabel("SYSTEM ARCHITECTURE & CAPABILITIES")
        lbl_arch_title.setStyleSheet("font-size: 12px; font-weight: 800; color: #38BDF8; letter-spacing: 0.5px;")
        arch_layout.addWidget(lbl_arch_title)

        features = [
            ("⚡ Ultra Low-Latency Video Pipeline", "DirectX 11 DXGI Desktop Duplication API with real-time hardware cursor composition and GDI fallback."),
            ("🖱️ Hardware-Accurate Input Injection", "Windows user32 SendInput supporting absolute coordinates, mouse wheel deltas, and keyboard scan codes."),
            ("📱 Modern Jetpack Compose Mobile Client", "Native Kotlin Android client with direct touch gestures, 2-finger wheel scroll, pinch zoom, and virtual touchpad."),
            ("☁️ Worldwide Cloudflare Edge Tunnel", "Zero-port-forwarding connectivity bypassing NATs, CGNATs, and mobile firewalls."),
            ("🛡️ Sandboxed Remote File Access", "Strict path authorization restricting remote file management to safe personal directories only."),
        ]

        for title, desc in features:
            f_box = QVBoxLayout()
            f_box.setSpacing(1)
            t_lbl = QLabel(title)
            t_lbl.setStyleSheet("font-size: 13px; font-weight: 700; color: #F8FAFC;")
            d_lbl = QLabel(desc)
            d_lbl.setStyleSheet("font-size: 11.5px; color: #94A3B8;")
            f_box.addWidget(t_lbl)
            f_box.addWidget(d_lbl)
            arch_layout.addLayout(f_box)

        main_layout.addWidget(arch_card)
        main_layout.addStretch()
