"""
Catalogue de suggestions (templates).

Responsabilité :
- décrire les suggestions disponibles
- fournir une méthode qui créera des QGraphicsItem
  (pour l'instant : placeholder)
"""

from PySide6.QtWidgets import QGraphicsPolygonItem, QGraphicsRectItem
from PySide6.QtGui import QPolygonF, QPen, QBrush, QColor
from PySide6.QtCore import QPointF, Qt


class Suggestion:
    def __init__(self, label: str, create_fn, preview_path: str | None = None):
        self.label = label
        self.create_fn = create_fn
        self.preview_path = preview_path

    def create_items(self, scene):
        return self.create_fn(scene)


# --- Tags assistant (pour détecter si déjà appliqué) ---
ASSISTANT_TAG_ROLE = int(Qt.UserRole)
TAG_CAT_EAR = "assistant:cat_ear"
TAG_ROOF_TRIANGLE = "assistant:roof_triangle"


def make_cat_ears_for_first_ellipse(scene):
    # inchangé sauf ajout du tag
    ellipse = None
    for it in scene.items():
        if it.__class__.__name__ == "QGraphicsEllipseItem":
            ellipse = it
            break
    if ellipse is None:
        return []

    rect = ellipse.sceneBoundingRect()

    left_base = QPointF(rect.left() + rect.width() * 0.25, rect.top())
    left_tip = QPointF(
        rect.left() + rect.width() * 0.15, rect.top() - rect.height() * 0.35
    )
    left_base2 = QPointF(rect.left() + rect.width() * 0.35, rect.top())

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

        ear.setFlag(ear.GraphicsItemFlag.ItemIsSelectable, True)
        ear.setFlag(ear.GraphicsItemFlag.ItemIsMovable, True)

        # Tag oreilles
        ear.setData(ASSISTANT_TAG_ROLE, TAG_CAT_EAR)

        items.append(ear)

    return items


def make_roof_triangle_for_first_rect(scene):
    """
    Crée un triangle rouge (rempli) au-dessus d'un rectangle.
    Style : contour noir, remplissage rouge.
    """
    target_rect = None

    # 1) On cherche un rectangle (idéalement avec contour noir)
    for it in scene.items():
        if isinstance(it, QGraphicsRectItem):
            # si possible, privilégier bordure noire
            try:
                if it.pen().color().name().lower() == "#000000":
                    target_rect = it
                    break
            except Exception:
                pass
            if target_rect is None:
                target_rect = it

    if target_rect is None:
        return []

    r = target_rect.sceneBoundingRect()

    # 2) Géométrie du toit : base = bord haut du rectangle, sommet au-dessus
    left = QPointF(r.left(), r.top())
    right = QPointF(r.right(), r.top())

    height = max(20.0, r.height() * 0.45)  # hauteur du toit
    tip = QPointF((r.left() + r.right()) / 2.0, r.top() - height)

    poly = QPolygonF([left, tip, right])
    roof = QGraphicsPolygonItem(poly)

    # 3) Style : contour noir + remplissage rouge
    pen = QPen(QColor("#000000"))
    pen.setWidth(2)
    roof.setPen(pen)

    roof.setBrush(
        QBrush(QColor("#e53935"))
    )  # rouge (comme ta palette) :contentReference[oaicite:1]{index=1}

    roof.setFlag(roof.GraphicsItemFlag.ItemIsSelectable, True)
    roof.setFlag(roof.GraphicsItemFlag.ItemIsMovable, True)

    # Tag toit
    roof.setData(ASSISTANT_TAG_ROLE, TAG_ROOF_TRIANGLE)

    return [roof]


CAT_EARS = Suggestion(
    label="Ajouter des oreilles",
    create_fn=make_cat_ears_for_first_ellipse,
    preview_path="assistant/previews/CAT_EARS.png",
)

ROOF_TRIANGLE = Suggestion(
    label="Ajouter un toit",
    create_fn=make_roof_triangle_for_first_rect,
    preview_path="assistant/previews/ROOF_TRIANGLE.png",
)
