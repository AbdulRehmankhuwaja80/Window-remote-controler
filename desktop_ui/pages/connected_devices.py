"""
RemoDesk Desktop UI - Connected Devices Page
Manages paired mobile clients, active remote desktop sessions, and access permissions.
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame,
    QTableWidget, QTableWidgetItem, QHeaderView, QApplication
)
from PySide6.QtCore import Qt, Signal
from desktop_ui.resources.icons import get_icon


class ConnectedDevicesPage(QWidget):
    disconnect_session_requested = Signal(str)
    toast_requested = Signal(str)

    def __init__(self, backend_client, parent=None):
        super().__init__(parent)
        self.backend = backend_client

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(28, 24, 28, 24)
        main_layout.setSpacing(18)

        # ─── Top Info Banner ──────────────────────────────────────────────────
        top_card = QFrame()
        top_card.setObjectName("card")
        top_layout = QHBoxLayout(top_card)
        top_layout.setContentsMargins(20, 16, 20, 16)
        top_layout.setSpacing(14)

        icon_devices = QLabel()
        icon_devices.setPixmap(get_icon("connected_devices", "#00D4FF", size=28).pixmap(32, 32))

        text_vbox = QVBoxLayout()
        text_vbox.setSpacing(2)
        lbl_h = QLabel("PAIRED & AUTHORIZED MOBILE DEVICES")
        lbl_h.setStyleSheet("font-size: 14px; font-weight: 800; color: #FFFFFF;")
        lbl_p = QLabel("Manage Android smartphones authorized to view and control your laptop.")
        lbl_p.setStyleSheet("font-size: 12px; color: #94A3B8;")
        text_vbox.addWidget(lbl_h)
        text_vbox.addWidget(lbl_p)

        top_layout.addWidget(icon_devices)
        top_layout.addLayout(text_vbox)
        top_layout.addStretch()

        self.btn_refresh = QPushButton(" Refresh List")
        self.btn_refresh.setObjectName("copyButton")
        self.btn_refresh.setIcon(get_icon("refresh", "#38BDF8", size=14))
        self.btn_refresh.clicked.connect(self.load_devices)
        top_layout.addWidget(self.btn_refresh)

        main_layout.addWidget(top_card)

        # ─── Devices & Sessions Table ─────────────────────────────────────────
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels([
            "Device / Client Info", "Session Identifier", "Status", "Started At", "Action"
        ])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)
        self.table.setShowGrid(False)
        self.table.setStyleSheet("""
            QTableWidget {
                background-color: #141D2D;
                border: 1px solid #202D42;
                border-radius: 10px;
                color: #F8FAFC;
                selection-background-color: #1E3A8A;
            }
            QTableWidget::item {
                padding: 10px;
                border-bottom: 1px solid #1E293B;
            }
        """)

        main_layout.addWidget(self.table)

        # Initial data load
        self.load_devices()

    def load_devices(self):
        sessions = self.backend.get_connected_devices()
        self.table.setRowCount(len(sessions))

        if not sessions:
            self.table.setRowCount(1)
            item = QTableWidgetItem("No paired client sessions recorded yet. Link your phone using your Partner ID.")
            item.setFlags(Qt.ItemIsEnabled)
            item.setForeground(Qt.gray)
            self.table.setItem(0, 0, item)
            for c in range(1, 5):
                empty = QTableWidgetItem("")
                empty.setFlags(Qt.ItemIsEnabled)
                self.table.setItem(0, c, empty)
            return

        for row, s in enumerate(sessions):
            # Client Info
            item_name = QTableWidgetItem(s.get("client_info") or "Android Device")
            item_name.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
            self.table.setItem(row, 0, item_name)

            # Session ID (shortened)
            raw_id = s.get("session_id", "N/A")
            short_id = raw_id[:8] + "..." if len(raw_id) > 8 else raw_id
            item_id = QTableWidgetItem(short_id)
            item_id.setFlags(Qt.ItemIsEnabled)
            self.table.setItem(row, 1, item_id)

            # Status Badge
            status_text = s.get("status", "TERMINATED")
            item_status = QTableWidgetItem(f"● {status_text}")
            item_status.setFlags(Qt.ItemIsEnabled)
            if status_text in ("ACTIVE", "STARTING"):
                item_status.setForeground(Qt.green)
            else:
                item_status.setForeground(Qt.lightGray)
            self.table.setItem(row, 2, item_status)

            # Started At
            started = s.get("started_at", "N/A")
            if started and "T" in started:
                started = started.split(".")[0].replace("T", " ")
            item_time = QTableWidgetItem(started)
            item_time.setFlags(Qt.ItemIsEnabled)
            self.table.setItem(row, 3, item_time)

            # Action button
            btn_disconnect = QPushButton("End Session")
            btn_disconnect.setStyleSheet("""
                QPushButton {
                    background: #7F1D1D;
                    color: #FEE2E2;
                    border: 1px solid #DC2626;
                    border-radius: 6px;
                    padding: 4px 10px;
                    font-size: 11px;
                    font-weight: 600;
                }
                QPushButton:hover { background: #991B1B; }
            """)
            btn_disconnect.clicked.connect(lambda checked=False, sid=raw_id: self._disconnect(sid))
            self.table.setCellWidget(row, 4, btn_disconnect)

    def _disconnect(self, session_id: str):
        self.disconnect_session_requested.emit(session_id)
        self.toast_requested.emit(f"Session disconnect request sent.")
        self.load_devices()
