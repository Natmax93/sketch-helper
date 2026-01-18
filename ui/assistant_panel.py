from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QLabel,
    QLineEdit,
    QComboBox,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QHBoxLayout,
    QListView,
)
from PySide6.QtCore import Signal, QSize
from PySide6.QtGui import QIcon, QPixmap
from pathlib import Path


class GenerationPanel(QWidget):
    """
    Panneau de "Génération IA" (prototype).

    Rôle :
    - UI : input texte + catégorie + liste de suggestions
    - émet un signal quand l'utilisateur veut ajouter une suggestion
    - ne doit PAS modifier la scène directement (responsabilité du contrôleur/éditeur)
    """

    # Signal émis quand une suggestion est choisie.
    # On passe (category: str, item_id: str)
    suggestion_chosen = Signal(str, str)

    def __init__(self):
        super().__init__()

        layout = QVBoxLayout(self)

        layout.addWidget(QLabel("<b>Génération IA (prototype)</b>"))

        # Input (réalisme)
        layout.addWidget(QLabel("Que voulez-vous générer ?"))
        self.prompt_input = QLineEdit()
        self.prompt_input.setPlaceholderText(
            "Ex: une porte, une roue, une carrosserie..."
        )
        layout.addWidget(self.prompt_input)

        # Catégorie
        layout.addWidget(QLabel("Catégorie"))
        self.category_combo = QComboBox()
        self.category_combo.addItems(["Porte", "Roue", "Carrosserie"])
        layout.addWidget(self.category_combo)

        # Liste de suggestions (clic pour ajouter)
        layout.addWidget(QLabel("Suggestions"))
        self.list_widget = QListWidget()
        self.list_widget.setViewMode(QListView.IconMode)
        self.list_widget.setIconSize(QSize(64, 64))
        self.list_widget.setResizeMode(QListView.Adjust)
        self.list_widget.setMovement(QListView.Static)
        self.list_widget.setSpacing(8)
        layout.addWidget(self.list_widget)

        # Bouton "Ajouter" (facultatif : on peut ajouter au double-clic)
        btn_row = QHBoxLayout()
        self.add_btn = QPushButton("Ajouter l'élément sélectionné")
        btn_row.addWidget(self.add_btn)
        layout.addLayout(btn_row)

        # Données prototype : suggestions pré-programmées
        self._catalog = {
            "Porte": [
                ("porte_rayure", "Porte rayée", "assistant/previews/porte_rayure.png"),
                (
                    "porte_arrondie",
                    "Porte arrondie",
                    "assistant/previews/porte_arrondie.png",
                ),
            ],
            "Roue": [
                ("jante_foncee", "Jante foncée", "assistant/previews/jante_foncee.png"),
                ("jante_claire", "Jante claire", "assistant/previews/jante_claire.png"),
            ],
            "Carrosserie": [
                (
                    "carrosserie_bleue",
                    "Carrosserie bleue",
                    "assistant/previews/carrosserie_bleue.png",
                ),
                (
                    "carrosserie_rouge",
                    "Carrosserie rouge",
                    "assistant/previews/carrosserie_rouge.png",
                ),
                (
                    "carrosserie_verte",
                    "Carrosserie verte",
                    "assistant/previews/carrosserie_verte.png",
                ),
            ],
        }

        # Remplir liste selon catégorie
        self.category_combo.currentTextChanged.connect(self._populate_list)
        self._populate_list(self.category_combo.currentText())

        # Déclenchement ajout : double-clic ou bouton
        self.list_widget.itemDoubleClicked.connect(self._emit_selected)
        self.add_btn.clicked.connect(self._emit_selected)

    def _populate_list(self, category: str):
        """Recharge la liste d'items selon la catégorie."""
        self.list_widget.clear()

        root = Path(__file__).resolve().parents[1]  # racine projet

        for item_id, label, preview_path in self._catalog.get(category, []):
            it = QListWidgetItem(label)
            it.setData(0x0100, item_id)

            if preview_path:
                p = root / preview_path
                if p.exists():
                    pm = QPixmap(str(p))
                    if not pm.isNull():
                        it.setIcon(QIcon(pm))

            self.list_widget.addItem(it)

    def _emit_selected(self):
        """Émet suggestion_chosen(category, item_id) selon l'item sélectionné."""
        category = self.category_combo.currentText()
        current = self.list_widget.currentItem()
        if current is None:
            return
        item_id = current.data(0x0100)
        self.suggestion_chosen.emit(category, item_id)

    def get_prompt_text(self) -> str:
        """Permet de logguer ou afficher le prompt saisi (même si prototype)."""
        return self.prompt_input.text().strip()
