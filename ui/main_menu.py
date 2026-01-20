"""
Fenêtre d'accueil.

Responsabilité :
- proposer à l'utilisateur de créer un nouveau projet (et plus tard : ouvrir un projet existant)
- ouvrir la fenêtre d'éditeur quand on clique sur "Nouveau dessin"
"""

from PySide6.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QPushButton,
    QLabel,
    QTextBrowser,
    QHBoxLayout,
)
from PySide6.QtCore import Qt, QSettings

from ui.editor import EditorWindow


WELCOME_HTML = """
<h2>Bienvenue sur <b>Sketch Helper</b> (prototype HAII)</h2>

<p>
Sketch Helper est un prototype d’outil de dessin qui explore l’assistance <i>Humain + IA</i>
pour la création de logos/dessins simples.
</p>

<h3>Ce que vous pouvez faire (outils de dessin)</h3>
<ul>
  <li>Dessiner : stylo, gomme, traits, rectangles, ellipses, triangles</li>
  <li>Choisir des couleurs : contour et remplissage</li>
  <li>Éditer : sélectionner/déplacer, copier, couper, coller, dupliquer</li>
  <li>Annuler / rétablir</li>
</ul>

<h3>Assistant IA (optionnel et contrôlable)</h3>
<p><b>L’assistant ne modifie jamais votre dessin “en secret” :</b> il propose, vous décidez.</p>
<ul>
  <li><b>Génération IA</b> : ouvre un panneau latéral avec des éléments préfaits (prototype).</li>
  <li><b>Auto-suggestions</b> : l’IA peut proposer automatiquement un ajout
      (avec prévisualisation + incertitude).</li>
  <li><b>Afficher assistant</b> : mascotte cliquable pour obtenir une suggestion manuelle.</li>
</ul>

<h3>Ce que l’application ne fait pas (limites du prototype)</h3>
<ul>
  <li>Ce n’est pas un logiciel professionnel de design.</li>
  <li>L’“IA” est simulée/prototypée : elle peut se tromper.</li>
  <li>Le résultat final dépend de vos choix (vous gardez le contrôle).</li>
</ul>

<h3>Mode “Test” (expérience)</h3>
<ol>
  <li>Cliquez sur <b>Test</b></li>
  <li>Choisissez <b>Avec IA</b> ou <b>Sans IA</b> (selon votre groupe)</li>
  <li>Reproduisez 3 modèles</li>
  <li>Pour chaque modèle, cliquez sur <b>Done</b> uniquement quand vous êtes satisfait</li>
  <li>Évaluez la ressemblance entre votre dessin et le modèle</li>
  <li>Fermez l’application après les 3 dessins</li>
</ol>

<h3>Données enregistrées</h3>
<p>
Temps, actions, outils utilisés, activation IA, décisions sur les suggestions,
afin d’analyser l’expérience.
</p>
"""


class MainMenuWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Menu - Sketch Helper (HAII)")
        self.resize(720, 720)

        self._settings = QSettings("SketchHelper", "HAII")
        self._editor = None

        root = QWidget()
        layout = QVBoxLayout(root)

        title = QLabel("<h1>Sketch Helper</h1>")
        title.setAlignment(Qt.AlignLeft)
        layout.addWidget(title)

        # Zone texte scrollable et bien lisible
        info = QTextBrowser()
        info.setOpenExternalLinks(False)
        info.setHtml(WELCOME_HTML)
        info.setMinimumHeight(280)
        layout.addWidget(info)

        # Boutons
        row = QHBoxLayout()

        btn_new = QPushButton("Nouveau dessin")
        btn_new.clicked.connect(self.open_editor_normal)
        row.addWidget(btn_new)

        layout.addLayout(row)

        self.setCentralWidget(root)

    def open_editor_normal(self):
        """Ouvre l'éditeur (mode normal) puis ferme le menu."""
        self._editor = EditorWindow()
        self._editor.show()
        self.close()
