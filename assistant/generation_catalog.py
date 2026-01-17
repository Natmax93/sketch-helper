from PySide6.QtWidgets import QGraphicsRectItem, QGraphicsEllipseItem, QGraphicsLineItem
from PySide6.QtGui import QPen
from PySide6.QtCore import QRectF


def _default_pen(width=2):
    pen = QPen()
    pen.setWidth(width)
    return pen


def create_generation_item(category: str, item_id: str):
    """
    Retourne une liste de QGraphicsItem à ajouter sur la scène.
    Prototype : formes simples.
    """

    items = []

    if category == "Porte":
        # Porte = rectangle vertical + poignée (petit cercle)
        if item_id == "door_small":
            rect = QGraphicsRectItem(QRectF(0, 0, 60, 100))
            rect.setPen(_default_pen(2))
            knob = QGraphicsEllipseItem(QRectF(45, 50, 8, 8))
            knob.setPen(_default_pen(2))
            items = [rect, knob]

        elif item_id == "door_double":
            left = QGraphicsRectItem(QRectF(0, 0, 50, 110))
            right = QGraphicsRectItem(QRectF(52, 0, 50, 110))
            left.setPen(_default_pen(2))
            right.setPen(_default_pen(2))
            items = [left, right]

        elif item_id == "door_round":
            # Simplification : rect + ellipse en haut
            rect = QGraphicsRectItem(QRectF(0, 20, 70, 90))
            top = QGraphicsEllipseItem(QRectF(0, 0, 70, 40))
            rect.setPen(_default_pen(2))
            top.setPen(_default_pen(2))
            items = [rect, top]

    elif category == "Roue":
        if item_id == "wheel_small":
            wheel = QGraphicsEllipseItem(QRectF(0, 0, 50, 50))
            wheel.setPen(_default_pen(2))
            items = [wheel]

        elif item_id == "wheel_big":
            wheel = QGraphicsEllipseItem(QRectF(0, 0, 80, 80))
            wheel.setPen(_default_pen(2))
            items = [wheel]

        elif item_id == "wheel_spoked":
            wheel = QGraphicsEllipseItem(QRectF(0, 0, 70, 70))
            wheel.setPen(_default_pen(2))
            # 2 rayons en croix (prototype)
            h = QGraphicsLineItem(0, 35, 70, 35)
            v = QGraphicsLineItem(35, 0, 35, 70)
            h.setPen(_default_pen(2))
            v.setPen(_default_pen(2))
            items = [wheel, h, v]

    elif category == "Carrosserie":
        if item_id == "body_compact":
            body = QGraphicsRectItem(QRectF(0, 20, 140, 50))
            cabin = QGraphicsRectItem(QRectF(30, 0, 60, 30))
            body.setPen(_default_pen(2))
            cabin.setPen(_default_pen(2))
            items = [body, cabin]

        elif item_id == "body_sedan":
            body = QGraphicsRectItem(QRectF(0, 25, 180, 50))
            cabin = QGraphicsRectItem(QRectF(50, 0, 80, 35))
            body.setPen(_default_pen(2))
            cabin.setPen(_default_pen(2))
            items = [body, cabin]

        elif item_id == "body_truck":
            body = QGraphicsRectItem(QRectF(0, 30, 200, 50))
            cab = QGraphicsRectItem(QRectF(0, 0, 60, 35))
            bed = QGraphicsRectItem(QRectF(65, 10, 135, 70))
            body.setPen(_default_pen(2))
            cab.setPen(_default_pen(2))
            bed.setPen(_default_pen(2))
            items = [cab, bed]

    # rendre chaque item sélectionnable/déplaçable (cohérent Tool.SELECT)
    for it in items:
        it.setFlag(it.GraphicsItemFlag.ItemIsSelectable, True)
        it.setFlag(it.GraphicsItemFlag.ItemIsMovable, True)

    return items
