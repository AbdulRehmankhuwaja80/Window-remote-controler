"""
RemoDesk Desktop UI - Security & Audit Event Logs Page
Manages pairing authorization, access guard policies, and live security audit trails.
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame,
    QTableWidget, QTableWidgetItem, QHeaderView, QCheckBox, QApplication
)
from PySide6.QtCore import Qt, Signal
from desktop_ui.resources.icons import get_icon


class SecurityPage(QWidget):
    regenerate_pin_requested = Signal()
    toast_requested = Signal(str)

    def __init__(self, backend_client, parent=None):
        super().__init__(parent)
        self.backend = backend_client

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(28, 24, 28, 24)
        main_layout.setSpacing(18)

        # ─── Top Security Policy Card ─────────────────────────────────────────
        top_card = QFrame()
        top_card.setObjectName("card")
        top_layout = QVBoxLayout(top_card)
        top_layout.setContentsMargins(22, 18, 22, 18)
        top_layout.setSpacing(14)

        header_row = QHBoxLayout()
        icon_sec = QLabel()
        icon_sec.setPixmap(get_icon("security", "#10B981", size=26).pixmap(28, 28))
        lbl_h = QLabel("HOST SECURITY & ACCESS GUARDS")
        lbl_h.setStyleSheet("font-size: 14px; font-weight: 800; color: #FFFFFF;")
        header_row.addWidget(icon_sec)
        header_row.addWidget(lbl_h)
        header_row.addStretch()

        self.btn_regen = QPushButton(" Generate New PIN")
        self.btn_regen.setObjectName("primaryButton")
        self.btn_regen.setIcon(get_icon("refresh", "#FFFFFF", size=14))
        self.btn_regen.clicked.connect(self.regenerate_pin_requested.emit)
        header_row.addWidget(self.btn_regen)
        top_layout.addLayout(header_row)

        # PIN & Guard controls
        controls_row = QHBoxLayout()
        controls_row.setSpacing(20)

        # Current PIN box
        pin_box = QFrame()
        pin_box.setStyleSheet("background: #0E1626; border: 1px solid #1E2D44; border-radius: 8px; padding: 10px;")
        p_vbox = QVBoxLayout(pin_box)
        p_vbox.setSpacing(2)
        lbl_p_title = QLabel("CURRENT 6-DIGIT PAIRING PIN:")
        lbl_p_title.setStyleSheet("font-size: 10px; font-weight: 700; color: #64748B;")
        self.lbl_pin_display = QLabel("867902")
        self.lbl_pin_display.setStyleSheet("font-size: 22px; font-weight: 900; color: #00D4FF; letter-spacing: 4px; font-family: monospace;")
        p_vbox.addWidget(lbl_p_title)
        p_vbox.addWidget(self.lbl_pin_display)
        controls_row.addWidget(pin_box)

        # Policy Checkboxes
        checks_vbox = QVBoxLayout()
        checks_vbox.setSpacing(8)

        self.chk_confirm = QCheckBox("Prompt approval dialog on PC screen when new phone connects")
        self.chk_confirm.setChecked(True)

        self.chk_sleep = QCheckBox("Prevent laptop from entering sleep mode during active remote sessions")
        self.chk_sleep.setChecked(True)

        self.chk_sandbox = QCheckBox("Enforce strict sandbox isolation on all remote file operations")
        self.chk_sandbox.setChecked(True)

        checks_vbox.addWidget(self.chk_confirm)
        checks_vbox.addWidget(self.chk_sleep)
        checks_vbox.addWidget(self.chk_sandbox)
        controls_row.addLayout(checks_vbox)

        top_layout.addLayout(controls_row)
        main_layout.addWidget(top_card)

        # ─── Live Audit Logs Table ────────────────────────────────────────────
        logs_card = QFrame()
        logs_card.setObjectName("card")
        logs_layout = QVBoxLayout(logs_card)
        logs_layout.setContentsMargins(18, 14, 18, 14)
        logs_layout.setSpacing(10)

        logs_header = QHBoxLayout()
        lbl_logs_title = QLabel("SECURITY AUDIT TRAIL (DATABASE EVENT LOGS)")
        lbl_logs_title.setStyleSheet("font-size: 11px; font-weight: 700; color: #94A3B8; letter-spacing: 0.5px;")
        logs_header.addWidget(lbl_logs_title)
        logs_header.addStretch()

        btn_refresh_logs = QPushButton(" Refresh Audit Logs")
        btn_refresh_logs.setObjectName("copyButton")
        btn_refresh_logs.setIcon(get_icon("refresh", "#38BDF8", size=13))
        btn_refresh_logs.clicked.connect(self.load_audit_logs)
        logs_header.addWidget(btn_refresh_logs)

        logs_layout.addLayout(logs_header)

        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["Event Action", "Details", "Origin IP", "Timestamp"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)
        self.table.setShowGrid(False)
        self.table.setStyleSheet("""
            QTableWidget {
                background-color: #141D2D;
                border: 1px solid #202D42;
                border-radius: 8px;
                color: #F8FAFC;
            }
            QTableWidget::item {
                padding: 7px;
                border-bottom: 1px solid #1E293B;
            }
        """)

        logs_layout.addWidget(self.table)
        main_layout.addWidget(logs_card)

        # Initial data load
        self.load_audit_logs()

    def update_pin(self, pin: str):
        self.lbl_pin_display.setText(pin)

    def load_audit_logs(self):
        logs = self.backend.get_audit_logs(limit=30)
        self.table.setRowCount(len(logs))

        if not logs:
            self.table.setRowCount(1)
            item = QTableWidgetItem("No security events logged yet.")
            item.setFlags(Qt.ItemIsEnabled)
            item.setForeground(Qt.gray)
            self.table.setItem(0, 0, item)
            return

        for row, log in enumerate(logs):
            # Action
            action = log.get("action", "EVENT")
            it_act = QTableWidgetItem(action)
            it_act.setFlags(Qt.ItemIsEnabled)
            if "REJECT" in action or "STOP" in action or "DENIED" in action:
                it_act.setForeground(Qt.red)
            elif "APPROVED" in action or "REGISTER" in action or "VERIFIED" in action:
                it_act.setForeground(Qt.green)
            else:
                it_act.setForeground(Qt.cyan)
            self.table.setItem(row, 0, it_act)

            # Details
            it_det = QTableWidgetItem(log.get("details", ""))
            it_det.setFlags(Qt.ItemIsEnabled)
            self.table.setItem(row, 1, it_det)

            # IP
            it_ip = QTableWidgetItem(log.get("ip_address", "127.0.0.1"))
            it_ip.setFlags(Qt.ItemIsEnabled)
            self.table.setItem(row, 2, it_ip)

            # Timestamp
            ts = log.get("created_at", "")
            if ts and "T" in str(ts):
                ts = str(ts).split(".")[0].replace("T", " ")
            it_ts = QTableWidgetItem(str(ts))
            it_ts.setFlags(Qt.ItemIsEnabled)
            self.table.setItem(row, 3, it_ts)
