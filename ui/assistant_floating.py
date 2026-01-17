from PySide6.QtWidgets import QToolButton
from PySide6.QtCore import Qt


class FloatingAssistantButton(QToolButton):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setText("🤖")
        self.setToolTip("Assistant")
        self.setFixedSize(44, 44)
        self.setStyleSheet(
            """
            QToolButton {
                border-radius: 22px;
                font-size: 18px;
            }
        """
        )
