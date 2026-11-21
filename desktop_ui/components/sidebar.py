"""
RemoDesk Desktop UI - Navigation Sidebar Component
Houses branding, page selection items, and quick system status indicator.
"""

from PySide6.QtWidgets import QFrame, QVBoxLayout, QHBoxLayout, QLabel, QListWidget, QListWidgetItem
from PySide6.QtCore import Qt, Signal, QSize
from PySide6.QtGui import QIcon
from desktop_ui.resources.icons import get_icon, get_pixmap


class Sidebar(QFrame):
    page_selected = Signal(int)

    NAV_ITEMS = [
        ("Dashboard", "dashboard"),
        ("My Device", "my_device"),
        ("Remote Access", "remote_access"),
        ("Connected Devices", "connected_devices"),
        ("File Transfer", "file_transfer"),
        ("Security", "security"),
        ("Settings", "settings"),
        ("About RemoDesk", "about"),
    ]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(240)
        self.setObjectName("sidebarPanel")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 20, 12, 16)
        layout.setSpacing(12)

        # ─── Brand & Logo Header ──────────────────────────────────────────────
        brand_container = QHBoxLayout()
        brand_container.setContentsMargins(8, 4, 8, 12)
        brand_container.setSpacing(12)

        lbl_logo = QLabel()
        lbl_logo.setPixmap(get_pixmap("logo", size=32))
        lbl_logo.setFixedSize(36, 36)

        title_vbox = QVBoxLayout()
        title_vbox.setSpacing(1)
        lbl_app_name = QLabel("RemoDesk")
        lbl_app_name.setStyleSheet("font-size: 17px; font-weight: 800; color: #FFFFFF; letter-spacing: 0.5px;")

        lbl_edition = QLabel("Windows Host • v1.2")
        lbl_edition.setStyleSheet("font-size: 11px; color: #00D4FF; font-weight: 600;")

        title_vbox.addWidget(lbl_app_name)
        title_vbox.addWidget(lbl_edition)

        brand_container.addWidget(lbl_logo)
        brand_container.addLayout(title_vbox)
        brand_container.addStretch()

        layout.addLayout(brand_container)

        # ─── Navigation List ──────────────────────────────────────────────────
        self.list_widget = QListWidget()
        self.list_widget.setObjectName("sidebarList")
        self.list_widget.setIconSize(QSize(20, 20))

        for text, icon_name in self.NAV_ITEMS:
            item = QListWidgetItem(get_icon(icon_name, "#94A3B8"), f"  {text}")
            self.list_widget.addItem(item)

        self.list_widget.currentRowChanged.connect(self.page_selected.emit)
        layout.addWidget(self.list_widget)

        layout.addStretch()

        # ─── Bottom Status Card ───────────────────────────────────────────────
        self.bottom_card = QFrame()
        self.bottom_card.setStyleSheet("""
            QFrame {
                background-color: #111A29;
                border: 1px solid #1D2A40;
                border-radius: 10px;
                padding: 10px;
            }
        """)
        bottom_layout = QVBoxLayout(self.bottom_card)
        bottom_layout.setContentsMargins(8, 8, 8, 8)
        bottom_layout.setSpacing(4)

        status_row = QHBoxLayout()
        status_row.setSpacing(6)
        self.dot = QLabel("●")
        self.dot.setStyleSheet("color: #10B981; font-size: 14px;")
        lbl_status_txt = QLabel("Laptop Host Agent")
        lbl_status_txt.setStyleSheet("font-size: 11px; font-weight: 700; color: #E2E8F0;")
        status_row.addWidget(self.dot)
        status_row.addWidget(lbl_status_txt)
        status_row.addStretch()

        self.lbl_local_ip = QLabel("192.168.0.43:8000")
        self.lbl_local_ip.setStyleSheet("font-size: 11.5px; color: #38BDF8; font-family: monospace; font-weight: 600;")

        bottom_layout.addLayout(status_row)
        bottom_layout.addWidget(self.lbl_local_ip)

        layout.addWidget(self.bottom_card)

        # Select first item by default
        self.list_widget.setCurrentRow(0)

    def set_current_index(self, index: int):
        if 0 <= index < self.list_widget.count():
            self.list_widget.setCurrentRow(index)

    def update_status(self, is_online: bool, local_ip: str):
        if is_online:
            self.dot.setStyleSheet("color: #10B981; font-size: 14px;")
        else:
            self.dot.setStyleSheet("color: #EF4444; font-size: 14px;")
        self.lbl_local_ip.setText(local_ip)
