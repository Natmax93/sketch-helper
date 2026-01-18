from PySide6.QtWidgets import QDialog, QVBoxLayout, QLabel, QHBoxLayout, QPushButton
from PySide6.QtGui import QPixmap
from PySide6.QtCore import Qt


class SuggestionDialog(QDialog):
    def __init__(
        self,
        title: str,
        uncertainty_pct: int,
        explanation: list[str],
        what_to_do: str,
        preview_pixmap: QPixmap | None = None,  # NEW
    ):
        super().__init__()
        self.setWindowTitle("Suggestion de l'assistant")

        layout = QVBoxLayout(self)

        layout.addWidget(QLabel(f"<b>{title}</b>"))
        layout.addWidget(QLabel(f"Incertitude : {uncertainty_pct}%"))

        if preview_pixmap is not None and not preview_pixmap.isNull():
            img = QLabel()
            img.setAlignment(Qt.AlignCenter)
            # Ajuste à une taille raisonnable
            img.setPixmap(
                preview_pixmap.scaled(
                    320, 240, Qt.KeepAspectRatio, Qt.SmoothTransformation
                )
            )
            layout.addWidget(img)

        layout.addWidget(QLabel("Pourquoi :"))
        for e in explanation[:3]:
            layout.addWidget(QLabel(f"• {e}"))

        layout.addWidget(QLabel(f"<i>Que faire maintenant ?</i> {what_to_do}"))

        btns = QHBoxLayout()
        self.btn_apply = QPushButton("Appliquer")
        self.btn_ignore = QPushButton("Ignorer")
        self.btn_refuse = QPushButton("Refuser")

        btns.addWidget(self.btn_apply)
        btns.addWidget(self.btn_ignore)
        btns.addWidget(self.btn_refuse)
        layout.addLayout(btns)

        self.choice = None
        self.btn_apply.clicked.connect(lambda: self._set_choice("accept"))
        self.btn_ignore.clicked.connect(lambda: self._set_choice("ignore"))
        self.btn_refuse.clicked.connect(lambda: self._set_choice("override"))

    def _set_choice(self, c: str):
        self.choice = c
        self.accept()
