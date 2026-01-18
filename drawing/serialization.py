"""
drawing/serialization.py

Sérialisation/désérialisation d'items Qt (QGraphicsItem) en dict JSON-friendly.

Objectif :
- Réutiliser le même format pour :
  - copy/paste (clipboard)
  - export/import de "templates" (catalogue de génération)
  - éventuellement sauvegarde projet

Le format est volontairement simple et orienté prototype.
"""

from typing import Any, Dict, Optional

from PySide6.QtWidgets import (
    QGraphicsLineItem,
    QGraphicsRectItem,
    QGraphicsEllipseItem,
    QGraphicsPathItem,
    QGraphicsPolygonItem,
)
from PySide6.QtGui import QPainterPath, QPen, QColor, QBrush, QPolygonF
from PySide6.QtCore import QPointF, QRectF, Qt


def make_pen_from(stroke_hex: str, stroke_width: int) -> QPen:
    pen = QPen(QColor(stroke_hex))
    pen.setWidth(int(stroke_width))
    return pen


def apply_fill_from(item, fill_hex: str) -> None:
    if fill_hex == "none":
        item.setBrush(QBrush(Qt.BrushStyle.NoBrush))
    else:
        item.setBrush(QBrush(QColor(fill_hex)))


def enable_interaction_flags(item) -> None:
    """Rend l'item sélectionnable et déplaçable (mode SELECT)."""
    item.setFlag(item.GraphicsItemFlag.ItemIsSelectable, True)
    item.setFlag(item.GraphicsItemFlag.ItemIsMovable, True)


def serialize_item(item) -> Optional[Dict[str, Any]]:
    """Transforme un QGraphicsItem en dict JSON-friendly.
    Retourne None si le type n'est pas supporté.
    """
    pen = item.pen() if hasattr(item, "pen") else None
    stroke = pen.color().name() if pen else "#000000"
    width = pen.width() if pen else 1

    fill = "none"
    if hasattr(item, "brush"):
        b = item.brush()
        if b.style() != Qt.BrushStyle.NoBrush:
            c = b.color()
            if c.alpha() != 0:
                fill = c.name()

    base: Dict[str, Any] = {
        "type": type(item).__name__,
        "pos": [float(item.pos().x()), float(item.pos().y())],
        "stroke": stroke,
        "stroke_width": int(width),
        "fill": fill,
        "z": float(item.zValue()),
    }

    if isinstance(item, QGraphicsLineItem):
        l = item.line()
        base["line"] = [float(l.x1()), float(l.y1()), float(l.x2()), float(l.y2())]

    elif isinstance(item, QGraphicsRectItem):
        r = item.rect()
        base["rect"] = [float(r.x()), float(r.y()), float(r.width()), float(r.height())]

    elif isinstance(item, QGraphicsEllipseItem):
        r = item.rect()
        base["ellipse"] = [
            float(r.x()),
            float(r.y()),
            float(r.width()),
            float(r.height()),
        ]

    elif isinstance(item, QGraphicsPathItem):
        path = item.path()
        elems = []
        for i in range(path.elementCount()):
            e = path.elementAt(i)
            etype = "MoveTo" if i == 0 else "LineTo"
            elems.append([float(e.x), float(e.y), etype])
        base["path_elems"] = elems

    elif isinstance(item, QGraphicsPolygonItem):
        poly = item.polygon()
        base["polygon"] = [
            [float(poly.at(i).x()), float(poly.at(i).y())] for i in range(poly.count())
        ]

        # Optionnel : préserver un tag assistant si tu en utilises un
        tag = item.data(int(Qt.UserRole))
        if tag is not None:
            base["assistant_tag"] = tag

    else:
        return None

    return base


def deserialize_item(data: Dict[str, Any]):
    """Reconstruit un QGraphicsItem depuis un dict sérialisé.
    Retourne None si le type n'est pas supporté.
    """
    t = data.get("type")
    pos = data.get("pos", [0, 0])
    pos_pt = QPointF(float(pos[0]), float(pos[1]))

    pen = make_pen_from(data.get("stroke", "#000000"), data.get("stroke_width", 1))
    fill = data.get("fill", "none")

    item = None

    if t == "QGraphicsLineItem":
        x1, y1, x2, y2 = data["line"]
        item = QGraphicsLineItem(float(x1), float(y1), float(x2), float(y2))
        item.setPen(pen)

    elif t == "QGraphicsRectItem":
        x, y, w, h = data["rect"]
        item = QGraphicsRectItem(QRectF(float(x), float(y), float(w), float(h)))
        item.setPen(pen)
        apply_fill_from(item, fill)

    elif t == "QGraphicsEllipseItem":
        x, y, w, h = data["ellipse"]
        item = QGraphicsEllipseItem(QRectF(float(x), float(y), float(w), float(h)))
        item.setPen(pen)
        apply_fill_from(item, fill)

    elif t == "QGraphicsPathItem":
        elems = data.get("path_elems", [])
        if not elems:
            return None
        path = QPainterPath()
        x0, y0, _ = elems[0]
        path.moveTo(float(x0), float(y0))
        for x, y, _etype in elems[1:]:
            path.lineTo(float(x), float(y))
        item = QGraphicsPathItem(path)
        item.setPen(pen)

    elif t == "QGraphicsPolygonItem":
        pts = data.get("polygon", [])
        poly = QPolygonF([QPointF(float(x), float(y)) for x, y in pts])
        item = QGraphicsPolygonItem(poly)
        item.setPen(pen)
        apply_fill_from(item, fill)

        if "assistant_tag" in data:
            item.setData(int(Qt.UserRole), data["assistant_tag"])

    if item is None:
        return None

    item.setZValue(float(data.get("z", 0.0)))  # Conservation des Z-values
    enable_interaction_flags(item)
    item.setPos(pos_pt)
    return item
