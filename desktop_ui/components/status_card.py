"""
RemoDesk Desktop UI - Status Card Component
Reusable card for displaying system state, metrics, and network status.
"""

from PySide6.QtWidgets import QFrame, QHBoxLayout, QVBoxLayout, QLabel
from PySide6.QtCore import Qt
from desktop_ui.resources.icons import get_pixmap


class StatusCard(QFrame):
    def __init__(self, icon_name: str, title: str, value: str, subtitle: str = "", accent_color: str = "#00D4FF", parent=None):
        super().__init__(parent)
        self.setObjectName("card")
        self.setStyleSheet(f"""
            QFrame#card {{
                background-color: #141D2D;
                border: 1px solid #202D42;
                border-radius: 12px;
            }}
            QFrame#card:hover {{
                border: 1px solid {accent_color};
            }}
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(14)

        # Icon container
        self.icon_frame = QFrame()
        self.icon_frame.setFixedSize(46, 46)
        self.icon_frame.setStyleSheet(f"""
            background: rgba({int(accent_color[1:3], 16)}, {int(accent_color[3:5], 16)}, {int(accent_color[5:7], 16)}, 0.12);
            border-radius: 10px;
        """)
        icon_layout = QVBoxLayout(self.icon_frame)
        icon_layout.setContentsMargins(0, 0, 0, 0)
        self.lbl_icon = QLabel()
        self.lbl_icon.setAlignment(Qt.AlignCenter)
        self.lbl_icon.setPixmap(get_pixmap(icon_name, accent_color, size=24))
        icon_layout.addWidget(self.lbl_icon)

        layout.addWidget(self.icon_frame)

        # Text information
        text_layout = QVBoxLayout()
        text_layout.setSpacing(2)

        self.lbl_title = QLabel(title.upper())
        self.lbl_title.setStyleSheet("font-size: 11px; font-weight: 700; color: #94A3B8; letter-spacing: 0.5px;")

        self.lbl_value = QLabel(value)
        self.lbl_value.setStyleSheet(f"font-size: 16px; font-weight: 800; color: {accent_color};")

        self.lbl_subtitle = QLabel(subtitle)
        self.lbl_subtitle.setStyleSheet("font-size: 11.5px; color: #CBD5E1;")

        text_layout.addWidget(self.lbl_title)
        text_layout.addWidget(self.lbl_value)
        if subtitle:
            text_layout.addWidget(self.lbl_subtitle)

        layout.addLayout(text_layout)
        layout.addStretch()

    def update_card(self, value: str, subtitle: str = None, accent_color: str = None):
        self.lbl_value.setText(value)
        if subtitle is not None:
            self.lbl_subtitle.setText(subtitle)
        if accent_color:
            self.lbl_value.setStyleSheet(f"font-size: 16px; font-weight: 800; color: {accent_color};")
            self.icon_frame.setStyleSheet(f"""
                background: rgba({int(accent_color[1:3], 16)}, {int(accent_color[3:5], 16)}, {int(accent_color[5:7], 16)}, 0.12);
                border-radius: 10px;
            """)
