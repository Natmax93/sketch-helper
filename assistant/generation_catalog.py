import json
from pathlib import Path

from PySide6.QtWidgets import QGraphicsRectItem, QGraphicsEllipseItem, QGraphicsLineItem
from PySide6.QtGui import QPen
from PySide6.QtCore import QRectF

from drawing.serialization import deserialize_item


def _default_pen(width=2):
    pen = QPen()
    pen.setWidth(width)
    return pen


_TEMPLATE_CACHE = None  # dict[(category, item_id)] -> payload


def _load_templates_dev():
    """
    Charge assistant/templates_dev/*.json (dev-only).
    Format attendu :
      { "meta": {"category": "...", "item_id": "..."}, "items": [ ... ] }
    """
    global _TEMPLATE_CACHE
    if _TEMPLATE_CACHE is not None:
        return _TEMPLATE_CACHE

    _TEMPLATE_CACHE = {}
    base = Path(__file__).resolve().parent / "templates_dev"
    if not base.exists():
        return _TEMPLATE_CACHE

    for p in base.glob("*.json"):
        try:
            payload = json.loads(p.read_text(encoding="utf-8"))
            meta = payload.get("meta", {})
            cat = meta.get("category")
            iid = meta.get("item_id")
            items = payload.get("items", [])
            items = sorted(items, key=lambda d: float(d.get("z", 0.0)))
            if cat and iid and isinstance(items, list):
                _TEMPLATE_CACHE[(cat, iid)] = payload
        except Exception:
            # dev-only : ignore fichier invalide
            continue

    return _TEMPLATE_CACHE


def create_generation_item(category: str, item_id: str):
    """
    Retourne une liste de QGraphicsItem à ajouter sur la scène.

    Priorité :
    1) templates JSON dessinés (assistant/templates_dev/)
    2) fallback : items codés en dur
    """
    # 1) templates dessinés (dev)
    templates = _load_templates_dev()
    payload = templates.get((category, item_id))
    if payload:
        out = []
        for d in payload.get("items", []):
            it = deserialize_item(d)
            if it is not None:
                out.append(it)
        if out:
            return out

    # 2) fallback : anciennes formes codées en dur
    pen = _default_pen(2)

    if category == "basic" and item_id == "rect":
        r = QGraphicsRectItem(QRectF(0, 0, 120, 80))
        r.setPen(pen)
        return [r]

    if category == "basic" and item_id == "ellipse":
        e = QGraphicsEllipseItem(QRectF(0, 0, 120, 80))
        e.setPen(pen)
        return [e]

    if category == "basic" and item_id == "line":
        l = QGraphicsLineItem(0, 0, 120, 0)
        l.setPen(pen)
        return [l]

    return []
