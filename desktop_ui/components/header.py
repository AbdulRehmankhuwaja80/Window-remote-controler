"""
RemoDesk Desktop UI - Top Header Bar Component
Displays current active view title, live service badges, and quick refresh control.
"""

from PySide6.QtWidgets import QFrame, QHBoxLayout, QVBoxLayout, QLabel, QPushButton
from PySide6.QtCore import Qt, Signal
from desktop_ui.resources.icons import get_icon


class HeaderBar(QFrame):
    refresh_clicked = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(72)
        self.setStyleSheet("""
            QFrame {
                background-color: #0A0E17;
                border-bottom: 1px solid #1A263B;
            }
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(28, 12, 28, 12)
        layout.setSpacing(16)

        # Title & Subtitle container
        title_box = QVBoxLayout()
        title_box.setSpacing(2)
        self.lbl_title = QLabel("Dashboard")
        self.lbl_title.setStyleSheet("font-size: 19px; font-weight: 700; color: #FFFFFF;")

        self.lbl_subtitle = QLabel("Overview & Remote Access Control")
        self.lbl_subtitle.setStyleSheet("font-size: 12px; color: #94A3B8;")

        title_box.addWidget(self.lbl_title)
        title_box.addWidget(self.lbl_subtitle)
        layout.addLayout(title_box)

        layout.addStretch()

        # Service Status Badges
        self.badge_host = QLabel("● Host Running")
        self.badge_host.setStyleSheet("""
            background: rgba(16, 185, 129, 0.12);
            color: #10B981;
            border: 1px solid rgba(16, 185, 129, 0.35);
            border-radius: 12px;
            padding: 5px 12px;
            font-size: 11.5px;
            font-weight: 600;
        """)

        self.badge_gateway = QLabel("● Gateway Online")
        self.badge_gateway.setStyleSheet("""
            background: rgba(0, 212, 255, 0.12);
            color: #00D4FF;
            border: 1px solid rgba(0, 212, 255, 0.35);
            border-radius: 12px;
            padding: 5px 12px;
            font-size: 11.5px;
            font-weight: 600;
        """)

        self.badge_remote = QLabel("● Remote Enabled")
        self.badge_remote.setStyleSheet("""
            background: rgba(59, 130, 246, 0.12);
            color: #60A5FA;
            border: 1px solid rgba(59, 130, 246, 0.35);
            border-radius: 12px;
            padding: 5px 12px;
            font-size: 11.5px;
            font-weight: 600;
        """)

        layout.addWidget(self.badge_host)
        layout.addWidget(self.badge_gateway)
        layout.addWidget(self.badge_remote)

        # Refresh button
        self.btn_refresh = QPushButton()
        self.btn_refresh.setIcon(get_icon("refresh", "#38BDF8", size=18))
        self.btn_refresh.setFixedSize(36, 36)
        self.btn_refresh.setToolTip("Refresh status & device records")
        self.btn_refresh.setStyleSheet("""
            QPushButton {
                background: #141D2D;
                border: 1px solid #283953;
                border-radius: 8px;
            }
            QPushButton:hover {
                background: #1E293B;
                border: 1px solid #00D4FF;
            }
        """)
        self.btn_refresh.clicked.connect(self.refresh_clicked.emit)
        layout.addWidget(self.btn_refresh)

    def set_page_header(self, title: str, subtitle: str):
        self.lbl_title.setText(title)
        self.lbl_subtitle.setText(subtitle)

    def update_badges(self, host_running: bool, gateway_online: bool, remote_enabled: bool):
        if host_running:
            self.badge_host.setText("● Host Running")
            self.badge_host.setStyleSheet("""
                background: rgba(16, 185, 129, 0.12);
                color: #10B981;
                border: 1px solid rgba(16, 185, 129, 0.35);
                border-radius: 12px; padding: 5px 12px; font-size: 11.5px; font-weight: 600;
            """)
        else:
            self.badge_host.setText("○ Host Stopped")
            self.badge_host.setStyleSheet("""
                background: rgba(239, 68, 68, 0.12);
                color: #EF4444;
                border: 1px solid rgba(239, 68, 68, 0.35);
                border-radius: 12px; padding: 5px 12px; font-size: 11.5px; font-weight: 600;
            """)

        if gateway_online:
            self.badge_gateway.setText("● Gateway Online")
            self.badge_gateway.setStyleSheet("""
                background: rgba(0, 212, 255, 0.12);
                color: #00D4FF;
                border: 1px solid rgba(0, 212, 255, 0.35);
                border-radius: 12px; padding: 5px 12px; font-size: 11.5px; font-weight: 600;
            """)
        else:
            self.badge_gateway.setText("○ Gateway Offline")
            self.badge_gateway.setStyleSheet("""
                background: rgba(148, 163, 184, 0.12);
                color: #94A3B8;
                border: 1px solid rgba(148, 163, 184, 0.35);
                border-radius: 12px; padding: 5px 12px; font-size: 11.5px; font-weight: 600;
            """)

        if remote_enabled:
            self.badge_remote.setText("● Remote Enabled")
            self.badge_remote.setStyleSheet("""
                background: rgba(59, 130, 246, 0.12);
                color: #60A5FA;
                border: 1px solid rgba(59, 130, 246, 0.35);
                border-radius: 12px; padding: 5px 12px; font-size: 11.5px; font-weight: 600;
            """)
        else:
            self.badge_remote.setText("○ Remote Paused")
            self.badge_remote.setStyleSheet("""
                background: rgba(245, 158, 11, 0.12);
                color: #F59E0B;
                border: 1px solid rgba(245, 158, 11, 0.35);
                border-radius: 12px; padding: 5px 12px; font-size: 11.5px; font-weight: 600;
            """)
