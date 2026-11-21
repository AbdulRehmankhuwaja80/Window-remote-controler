"""
RemoDesk Desktop UI - Settings & Configuration Page
Configures Windows startup, system tray behavior, video streaming quality, and network ports.
"""

import os
import sys
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame,
    QCheckBox, QComboBox, QSlider, QGridLayout, QApplication
)
from PySide6.QtCore import Qt, Signal
from desktop_ui.resources.icons import get_icon

try:
    import winreg
except ImportError:
    winreg = None


class SettingsPage(QWidget):
    toast_requested = Signal(str)

    def __init__(self, backend_client, parent=None):
        super().__init__(parent)
        self.backend = backend_client

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(28, 24, 28, 24)
        main_layout.setSpacing(18)

        # ─── 1. System & Windows Startup Card ─────────────────────────────────
        card_sys = QFrame()
        card_sys.setObjectName("card")
        sys_layout = QVBoxLayout(card_sys)
        sys_layout.setContentsMargins(22, 18, 22, 18)
        sys_layout.setSpacing(12)

        lbl_sys_h = QLabel("SYSTEM & WINDOWS INTEGRATION")
        lbl_sys_h.setStyleSheet("font-size: 13px; font-weight: 800; color: #FFFFFF;")
        sys_layout.addWidget(lbl_sys_h)

        self.chk_autostart = QCheckBox("Start RemoDesk Host automatically when Windows boots")
        self.chk_autostart.setChecked(self._is_startup_enabled())
        self.chk_autostart.toggled.connect(self._toggle_autostart)

        self.chk_minimize_tray = QCheckBox("Minimize dashboard to Windows System Tray on close instead of exiting")
        self.chk_minimize_tray.setChecked(True)

        self.chk_notifications = QCheckBox("Show balloon notification toasts when an Android phone connects")
        self.chk_notifications.setChecked(True)

        sys_layout.addWidget(self.chk_autostart)
        sys_layout.addWidget(self.chk_minimize_tray)
        sys_layout.addWidget(self.chk_notifications)
        main_layout.addWidget(card_sys)

        # ─── 2. Video Streaming & Performance Card ────────────────────────────
        card_perf = QFrame()
        card_perf.setObjectName("card")
        perf_layout = QVBoxLayout(card_perf)
        perf_layout.setContentsMargins(22, 18, 22, 18)
        perf_layout.setSpacing(14)

        lbl_perf_h = QLabel("VIDEO STREAMING & PERFORMANCE PROFILES")
        lbl_perf_h.setStyleSheet("font-size: 13px; font-weight: 800; color: #FFFFFF;")
        perf_layout.addWidget(lbl_perf_h)

        perf_grid = QGridLayout()
        perf_grid.setSpacing(14)

        # Target Framerate
        lbl_fps = QLabel("Target Framerate:")
        lbl_fps.setStyleSheet("color: #94A3B8; font-weight: 600;")
        self.combo_fps = QComboBox()
        self.combo_fps.addItems(["30 FPS (Balanced)", "60 FPS (Ultra Smooth)", "15 FPS (Battery Saver)"])
        self.combo_fps.setCurrentIndex(0)
        perf_grid.addWidget(lbl_fps, 0, 0)
        perf_grid.addWidget(self.combo_fps, 0, 1)

        # JPEG Quality Slider
        lbl_quality = QLabel("Streaming Compression Quality:")
        lbl_quality.setStyleSheet("color: #94A3B8; font-weight: 600;")
        
        slider_row = QHBoxLayout()
        slider_row.setSpacing(12)
        self.slider_quality = QSlider(Qt.Horizontal)
        self.slider_quality.setRange(40, 95)
        self.slider_quality.setValue(75)

        self.lbl_quality_val = QLabel("75%")
        self.lbl_quality_val.setStyleSheet("font-weight: 700; color: #00D4FF; min-width: 35px;")
        self.slider_quality.valueChanged.connect(lambda val: self.lbl_quality_val.setText(f"{val}%"))

        slider_row.addWidget(self.slider_quality)
        slider_row.addWidget(self.lbl_quality_val)

        perf_grid.addWidget(lbl_quality, 1, 0)
        perf_grid.addLayout(slider_row, 1, 1)

        # Multi-Monitor Selection
        lbl_mon = QLabel("Target Display Monitor:")
        lbl_mon.setStyleSheet("color: #94A3B8; font-weight: 600;")
        self.combo_mon = QComboBox()
        self.combo_mon.addItems(["Primary Screen (Default)", "Display 2 (Extended Desktop)"])
        perf_grid.addWidget(lbl_mon, 2, 0)
        perf_grid.addWidget(self.combo_mon, 2, 1)

        perf_layout.addLayout(perf_grid)
        main_layout.addWidget(card_perf)

        # ─── Save Settings Button ─────────────────────────────────────────────
        btn_save = QPushButton(" Save All Settings")
        btn_save.setObjectName("primaryButton")
        btn_save.setIcon(get_icon("check", "#FFFFFF", size=16))
        btn_save.clicked.connect(self._save_settings)
        main_layout.addWidget(btn_save, alignment=Qt.AlignLeft)

        main_layout.addStretch()

    def _is_startup_enabled(self) -> bool:
        if not winreg:
            return False
        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run", 0, winreg.KEY_READ)
            val, _ = winreg.QueryValueEx(key, "RemoDeskHost")
            winreg.CloseKey(key)
            return bool(val)
        except Exception:
            return False

    def _toggle_autostart(self, enabled: bool):
        if not winreg:
            return
        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run", 0, winreg.KEY_SET_VALUE)
            if enabled:
                launcher = os.path.join(self.backend.repo_root, "Launch_RemoDesk_Desktop.bat")
                winreg.SetValueEx(key, "RemoDeskHost", 0, winreg.REG_SZ, f'"{launcher}" --minimized')
                self.toast_requested.emit("RemoDesk configured to launch on Windows startup.")
            else:
                try:
                    winreg.DeleteValue(key, "RemoDeskHost")
                    self.toast_requested.emit("Windows startup entry removed.")
                except FileNotFoundError:
                    pass
            winreg.CloseKey(key)
        except Exception as e:
            self.toast_requested.emit(f"Could not update registry: {e}")

    def _save_settings(self):
        cfg = self.backend.get_host_config()
        cfg["TargetFps"] = 60 if "60" in self.combo_fps.currentText() else (15 if "15" in self.combo_fps.currentText() else 30)
        cfg["JpegQuality"] = self.slider_quality.value()
        cfg["StartWithWindows"] = self.chk_autostart.isChecked()
        self.backend.save_host_config(cfg)
        self.toast_requested.emit("Host settings successfully saved!")
