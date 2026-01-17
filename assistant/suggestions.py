"""
Catalogue de suggestions (templates).

Responsabilité :
- décrire les suggestions disponibles
- fournir une méthode qui créera des QGraphicsItem
  (pour l'instant : placeholder)
"""

from PySide6.QtWidgets import QGraphicsPolygonItem
from PySide6.QtGui import QPolygonF, QPen
from PySide6.QtCore import QPointF


class Suggestion:
    def __init__(self, label: str, create_fn):
        # Nom affiché dans l'UI
        self.label = label
        self.create_fn = create_fn  # (scene) -> list[QGraphicsItem]

    def create_items(self, scene):
        """
        Retournera plus tard une liste de QGraphicsItem.
        Exemple futur :
            return [QGraphicsRectItem(...), QGraphicsEllipseItem(...)]
        """
        return self.create_fn(scene)


def make_cat_ears_for_first_ellipse(scene):
    # trouver une ellipse existante
    ellipse = None
    for it in scene.items():
        if it.__class__.__name__ == "QGraphicsEllipseItem":
            ellipse = it
            break
    if ellipse is None:
        return []

    rect = ellipse.sceneBoundingRect()
    # points oreilles (coordonnées scène)
    # Oreille gauche
    left_base = QPointF(rect.left() + rect.width() * 0.25, rect.top())
    left_tip = QPointF(
        rect.left() + rect.width() * 0.15, rect.top() - rect.height() * 0.35
    )
    left_base2 = QPointF(rect.left() + rect.width() * 0.35, rect.top())

    # Oreille droite
    right_base = QPointF(rect.left() + rect.width() * 0.75, rect.top())
    right_tip = QPointF(
        rect.left() + rect.width() * 0.85, rect.top() - rect.height() * 0.35
    )
    right_base2 = QPointF(rect.left() + rect.width() * 0.65, rect.top())

    items = []
    for a, b, c in [
        (left_base, left_tip, left_base2),
        (right_base, right_tip, right_base2),
    ]:
        poly = QPolygonF([a, b, c])
        ear = QGraphicsPolygonItem(poly)
        pen = QPen()
        pen.setWidth(2)
        ear.setPen(pen)
        # selectable/movable
        ear.setFlag(ear.GraphicsItemFlag.ItemIsSelectable, True)
        ear.setFlag(ear.GraphicsItemFlag.ItemIsMovable, True)
        items.append(ear)

    return items


CAT_EARS = Suggestion(
    "Ajouter des oreilles (si ellipse)", make_cat_ears_for_first_ellipse
)
