"""
RemoDesk Desktop UI - Toast Notification Component
Floating, semi-transparent in-app banner for feedback on user actions.
"""

from PySide6.QtWidgets import QLabel, QGraphicsOpacityEffect
from PySide6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve


class ToastNotification(QLabel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAlignment(Qt.AlignCenter)
        self.setStyleSheet("""
            background-color: #0E1626;
            color: #38BDF8;
            border: 1px solid #0284C7;
            border-radius: 8px;
            padding: 10px 20px;
            font-size: 13px;
            font-weight: 700;
        """)
        self.setFixedHeight(44)
        self.hide()

        self.opacity_effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self.opacity_effect)

        self.anim = QPropertyAnimation(self.opacity_effect, b"opacity")
        self.anim.setDuration(250)
        self.anim.setEasingCurve(QEasingCurve.InOutQuad)

        self.hide_timer = QTimer(self)
        self.hide_timer.setSingleShot(True)
        self.hide_timer.timeout.connect(self._fade_out)

    def show_message(self, message: str, duration_ms: int = 2500):
        self.setText(f"✓  {message}")
        self.adjustSize()

        # Center horizontally at the bottom of the parent
        if self.parent():
            parent_w = self.parent().width()
            parent_h = self.parent().height()
            w = max(self.width() + 40, 260)
            self.setGeometry((parent_w - w) // 2, parent_h - 75, w, 44)

        self.show()
        self.raise_()
        self.anim.stop()
        self.anim.setStartValue(0.0)
        self.anim.setEndValue(1.0)
        self.anim.start()

        self.hide_timer.start(duration_ms)

    def _fade_out(self):
        self.anim.stop()
        self.anim.setStartValue(1.0)
        self.anim.setEndValue(0.0)
        self.anim.finished.connect(self.hide)
        self.anim.start()
