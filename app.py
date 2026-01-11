from PySide6.QtCore import QSize, Qt, QPoint
from PySide6.QtGui import QAction, QIcon, QPixmap, QPainter, QPen, QColor
from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QDockWidget,
    QToolBar,
    QStatusBar,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
)

# Only needed for access to command line arguments
import sys

# Import des classes pour le dessin
from draw_utils import Canvas, COLORS, QPaletteButton


class MainWindow(QMainWindow):
    """
    Subclass QMainWindow to customize your application's main window.
    """

    def __init__(self):
        """
        Tous les widgets de la fenêtre sont définis dans cette fonction.
        """

        # When you subclass a Qt class you must always call the super __init__
        # function to allow Qt to set up the object.
        super().__init__()

        # Changer le titre de la fenêtre
        self.setWindowTitle("Sketch Creator")

        # Fixer la taille de la fenêtre
        self.setFixedSize(QSize(1298, 853))

        # Layout de la fenêtre
        w = QWidget()
        l = QVBoxLayout()
        w.setLayout(l)

        # --- ZONE DE DESSIN ---

        # QLabel is the simplest widget available for displaying a QPixmap.
        self.canvas = Canvas()
        l.addWidget(self.canvas)

        # --- Palette pour choisir la couleur (temporaire) ---

        palette = QHBoxLayout()
        self.add_palette_buttons(palette)
        l.addLayout(palette)

        # --- La Toolbar qui contient tous les outils ---

        toolbar = QToolBar("My main toolbar")
        toolbar.setIconSize(QSize(48, 48))  # Taille minimale des icônes
        self.addToolBar(toolbar)

        # --- Les actions pour chaque outil ---

        # Bouton de génération des formes
        button_action = QAction("Génération IA", self)
        # Texte affiché dans la barre de status lorsque l'on passe
        # la souris dessus
        button_action.setStatusTip("C'est le bouton de génération")
        # Relier l'action au bouton
        button_action.triggered.connect(self.toolbar_button_clicked)
        # Ajout du bouton à la toolbar
        toolbar.addAction(button_action)

        # --- Panneau Génération IA

        ai_assistant = QDockWidget("Assistant IA")
        self.addDockWidget(Qt.LeftDockWidgetArea, ai_assistant)

        # Stylo pour dessiner
        button_action2 = QAction("Stylo", self)
        button_action2.setStatusTip("C'est le stylo")
        button_action2.triggered.connect(self.toolbar_button_clicked)
        # Le bouton a un état activé/désactivé
        button_action2.setCheckable(True)
        toolbar.addAction(button_action2)

        # Bouton pour revenir au Menu
        button_action3 = QAction(QIcon("exit_logo.png"), "Menu", self)
        button_action3.setStatusTip("Revenir au menu")
        button_action3.triggered.connect(self.toolbar_button_clicked)
        button_action3.setCheckable(False)
        toolbar.addAction(button_action3)

        # Barre de status affichée en bas de la fenêtre
        self.setStatusBar(QStatusBar(self))

        # Set the central widget of the Window.
        self.setCentralWidget(w)

    def toolbar_button_clicked(self, s):
        """
        Affiche "click" et le paramètre 's' correspondant à l'état du bouton
        (check = True/False)
        """
        print("click", s)

    def add_palette_buttons(self, layout):
        for c in COLORS:
            b = QPaletteButton(c)
            b.pressed.connect(lambda c=c: self.canvas.set_pen_color(c))
            layout.addWidget(b)

    def resizeEvent(self, event):
        print("Taille :", event.size())
        return super().resizeEvent(event)


# You need one (and only one) QApplication instance per application.
# Pass in sys.argv to allow command line arguments for your app.
# If you know you won't use command line arguments QApplication([]) works too.
app = QApplication(sys.argv)

# Create a Qt widget, which will be our window.
window = MainWindow()
window.show()  # IMPORTANT!!!!! Windows are hidden by default.

# Start the event loop.
app.exec()

# Your application won't reach here until you exit and the event
# loop has stopped.
