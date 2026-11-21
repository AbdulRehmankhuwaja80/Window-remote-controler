"""
RemoDesk Desktop UI - File Transfer Activity & Sandbox Manager
Displays authorized directories, recent transfers, and explorer shortcuts.
"""

import os
import subprocess
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame,
    QGridLayout, QTableWidget, QTableWidgetItem, QHeaderView, QApplication
)
from PySide6.QtCore import Qt, Signal
from desktop_ui.resources.icons import get_icon


class FileTransferPage(QWidget):
    toast_requested = Signal(str)

    def __init__(self, backend_client, parent=None):
        super().__init__(parent)
        self.backend = backend_client

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(28, 24, 28, 24)
        main_layout.setSpacing(18)

        # ─── Top Authorized Roots Banner ──────────────────────────────────────
        top_card = QFrame()
        top_card.setObjectName("card")
        top_layout = QVBoxLayout(top_card)
        top_layout.setContentsMargins(20, 16, 20, 16)
        top_layout.setSpacing(12)

        header_row = QHBoxLayout()
        icon_folder = QLabel()
        icon_folder.setPixmap(get_icon("file_transfer", "#00D4FF", size=26).pixmap(28, 28))
        lbl_h = QLabel("SANDBOXED FILE ACCESS ROOTS")
        lbl_h.setStyleSheet("font-size: 14px; font-weight: 800; color: #FFFFFF;")
        header_row.addWidget(icon_folder)
        header_row.addWidget(lbl_h)
        header_row.addStretch()

        btn_open_downloads = QPushButton(" Open Downloads Folder")
        btn_open_downloads.setObjectName("primaryButton")
        btn_open_downloads.setIcon(get_icon("folder", "#FFFFFF", size=14))
        btn_open_downloads.clicked.connect(self._open_downloads)
        header_row.addWidget(btn_open_downloads)
        top_layout.addLayout(header_row)

        lbl_desc = QLabel(
            "Remote phone file management is strictly sandboxed. Only the 8 authorized user folders below "
            "can be viewed, uploaded, or downloaded. Windows system directories are completely protected."
        )
        lbl_desc.setStyleSheet("font-size: 12px; color: #94A3B8; line-height: 1.4;")
        lbl_desc.setWordWrap(True)
        top_layout.addWidget(lbl_desc)

        # Grid of authorized folders
        folders_grid = QGridLayout()
        folders_grid.setSpacing(10)

        user_profile = os.environ.get("USERPROFILE", os.path.expanduser("~"))
        self.authorized_folders = [
            ("Downloads", os.path.join(user_profile, "Downloads")),
            ("Documents", os.path.join(user_profile, "Documents")),
            ("Desktop", os.path.join(user_profile, "Desktop")),
            ("Pictures", os.path.join(user_profile, "Pictures")),
            ("Videos", os.path.join(user_profile, "Videos")),
            ("Music", os.path.join(user_profile, "Music")),
            ("UserProfile", user_profile),
            ("OneDrive", os.path.join(user_profile, "OneDrive")),
        ]

        for idx, (name, path) in enumerate(self.authorized_folders):
            row = idx // 4
            col = idx % 4

            btn_folder = QPushButton(f" 📂 {name}")
            btn_folder.setStyleSheet("""
                QPushButton {
                    background: #0E1626;
                    border: 1px solid #1E2D44;
                    border-radius: 6px;
                    color: #CBD5E1;
                    padding: 6px 12px;
                    font-size: 11.5px;
                    font-weight: 600;
                    text-align: left;
                }
                QPushButton:hover {
                    background: #1E293B;
                    border: 1px solid #00D4FF;
                    color: #FFFFFF;
                }
            """)
            btn_folder.setToolTip(path)
            btn_folder.clicked.connect(lambda checked=False, p=path: self._open_path(p))
            folders_grid.addWidget(btn_folder, row, col)

        top_layout.addLayout(folders_grid)
        main_layout.addWidget(top_card)

        # ─── Recent Transfers Table ───────────────────────────────────────────
        table_frame = QFrame()
        table_frame.setObjectName("card")
        table_layout = QVBoxLayout(table_frame)
        table_layout.setContentsMargins(18, 14, 18, 14)
        table_layout.setSpacing(10)

        lbl_table_title = QLabel("RECENT FILE TRANSFERS")
        lbl_table_title.setStyleSheet("font-size: 11px; font-weight: 700; color: #94A3B8; letter-spacing: 0.5px;")
        table_layout.addWidget(lbl_table_title)

        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels([
            "File Name", "Direction", "Size", "Status", "Timestamp"
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
                border-radius: 8px;
                color: #F8FAFC;
            }
            QTableWidget::item {
                padding: 8px;
                border-bottom: 1px solid #1E293B;
            }
        """)

        # Default placeholder rows
        sample_transfers = [
            ("RemoDesk.apk", "Download to Phone", "56.9 MB", "Completed", "Active Distribution"),
            ("host_config.json", "System Config", "342 B", "Synced", "Protected APPDATA"),
            ("remodesk.db", "Database", "61.4 KB", "Active", "SQLite Engine"),
        ]
        self.table.setRowCount(len(sample_transfers))
        for r, (fname, direction, fsize, status, ts) in enumerate(sample_transfers):
            self.table.setItem(r, 0, QTableWidgetItem(fname))
            self.table.setItem(r, 1, QTableWidgetItem(direction))
            self.table.setItem(r, 2, QTableWidgetItem(fsize))
            st_item = QTableWidgetItem(f"● {status}")
            st_item.setForeground(Qt.green)
            self.table.setItem(r, 3, st_item)
            self.table.setItem(r, 4, QTableWidgetItem(ts))

        table_layout.addWidget(self.table)
        main_layout.addWidget(table_frame)

    def _open_downloads(self):
        downloads = os.path.join(os.environ.get("USERPROFILE", os.path.expanduser("~")), "Downloads")
        self._open_path(downloads)

    def _open_path(self, path: str):
        if os.path.exists(path):
            try:
                os.startfile(path)
                self.toast_requested.emit(f"Opened folder: {os.path.basename(path)}")
            except Exception as e:
                self.toast_requested.emit(f"Cannot open folder: {e}")
        else:
            self.toast_requested.emit(f"Folder does not exist: {path}")
