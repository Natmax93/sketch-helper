import sys
from PySide6 import QtCore, QtGui, QtWidgets
from PySide6.QtCore import Qt


COLORS = [
    # 17 undertones https://lospec.com/palette-list/17undertones
    "#000000",
    "#141923",
    "#414168",
    "#3a7fa7",
    "#35e3e3",
    "#8fd970",
    "#5ebb49",
    "#458352",
    "#dcd37b",
    "#fffee5",
    "#ffd035",
    "#cc9245",
    "#a15c3e",
    "#a42f3b",
    "#f45b7a",
    "#c24998",
    "#81588d",
    "#bcb0c2",
    "#ffffff",
]


class QPaletteButton(QtWidgets.QPushButton):

    def __init__(self, color):
        super().__init__()
        self.setFixedSize(QtCore.QSize(24, 24))
        self.color = color
        self.setStyleSheet("background-color: %s;" % color)


class Canvas(QtWidgets.QLabel):
    """
    Classe pour la zone de dessin. Utile pour éviter d'avoir un décalage avec
    la position de la souris. QLabel is the simplest widget available for
    displaying a QPixmap : c'est pour ça que Canvas hérite de Label.
    """

    def __init__(self):
        super().__init__()

        # All standard widgets draw themselves as bitmaps on a rectangular
        # "canvas" that forms the shape of the widget
        pixmap = QtGui.QPixmap(1280, 720)
        pixmap.fill(Qt.white)
        self.setPixmap(pixmap)

        # Dernière position de la souris
        self.last_x, self.last_y = None, None

        # Couleur du stylo noir par défaut
        self.pen_color = QtGui.QColor("#000000")

    def set_pen_color(self, c):
        """
        Permet de changer la couleur du stylo.

        :param self: Le canvas sur lequel on dessine.
        :param c: La nouvelle couleur à appliquer.
        """
        self.pen_color = QtGui.QColor(c)

    def mouseMoveEvent(self, e):
        """
        Cette fonction permet de dessiner un trait entre deux positions
        de souris.
        """
        if self.last_x is None:  # First event.
            self.last_x = e.x()
            self.last_y = e.y()
            return  # Ignore the first time.

        # Récupérer la zone de dessin
        canvas = self.pixmap()

        # Sélectionner
        painter = QtGui.QPainter(canvas)
        p = painter.pen()
        p.setWidth(4)
        p.setColor(self.pen_color)
        painter.setPen(p)
        painter.drawLine(self.last_x, self.last_y, e.x(), e.y())
        painter.end()
        self.setPixmap(canvas)

        # Update the origin for next time.
        self.last_x = e.x()
        self.last_y = e.y()

    def mouseReleaseEvent(self, e):
        self.last_x = None
        self.last_y = None
