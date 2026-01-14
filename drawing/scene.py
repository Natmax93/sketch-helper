"""
scene.py

QGraphicsScene spécialisée pour un éditeur de dessin.

Responsabilités :
- gérer l'outil courant (stylo, sélection, etc.)
- intercepter les événements souris (press / move / release)
- créer et manipuler des QGraphicsItem
- notifier le logger des actions utilisateur

La scène ne s'occupe PAS :
- de l'UI (toolbar, boutons)
- de la logique de l'assistant IA
"""

from PySide6.QtWidgets import (
    QGraphicsScene,
    QGraphicsPathItem,
    QGraphicsLineItem,
    QGraphicsRectItem,
    QGraphicsEllipseItem,
)
from PySide6.QtGui import QPainterPath, QPen
from PySide6.QtCore import QRectF, QLineF

from drawing.tools import Tool


class DrawingScene(QGraphicsScene):
    def __init__(self, logger=None):
        super().__init__()

        width = 1280
        height = 720
        self.setSceneRect(QRectF(0, 0, width, height))

        self._tool = Tool.SELECT
        self.logger = logger

        # ---- PEN ----
        self._current_path = None
        self._current_item = None
        self._points_count = 0

        # ---- SELECT ----
        self._press_item = None
        self._press_pos = None

        # ---- SHAPES (LINE/RECT/ELLIPSE) ----
        self._shape_start = None  # QPointF (scene coords)
        self._shape_item = None  # QGraphicsItem (line/rect/ellipse)

    # ----------------------------
    # Utils
    # ----------------------------
    def _make_pen(self, width=2):
        pen = QPen()
        pen.setWidth(width)
        return pen

    def _enable_interaction_flags(self, item):
        # sélection + déplacement via SELECT
        item.setFlag(item.GraphicsItemFlag.ItemIsSelectable, True)
        item.setFlag(item.GraphicsItemFlag.ItemIsMovable, True)

    def _item_at_scene_pos(self, scene_pos):
        # itemAt a besoin d'une transform de la vue
        if not self.views():
            return None
        view = self.views()[0]
        return self.itemAt(scene_pos, view.transform())

    def set_tool(self, tool: Tool):
        self._tool = tool
        if self.logger:
            self.logger.log(event_type="tool_change", tool=tool.name)

    def tool(self) -> Tool:
        return self._tool

    # ------------------------------------------------------------------
    # Mouse events
    # ------------------------------------------------------------------
    def mousePressEvent(self, event):
        p = event.scenePos()

        # ---------------- ERASER ----------------
        if self._tool == Tool.ERASER and event.button():
            item = self._item_at_scene_pos(p)
            if item is not None:
                self.removeItem(item)
                if self.logger:
                    self.logger.log(
                        event_type="erase",
                        tool="ERASER",
                        item_type=type(item).__name__,
                    )
                event.accept()
                return
            # si rien à gommer, on laisse Qt faire (ou on accept quand même)
            super().mousePressEvent(event)
            return

        # ---------------- PEN ----------------
        if self._tool == Tool.PEN and event.button():
            self._current_path = QPainterPath(p)
            self._points_count = 1

            self._current_item = QGraphicsPathItem(self._current_path)
            self._current_item.setPen(self._make_pen(width=2))
            self._enable_interaction_flags(self._current_item)

            self.addItem(self._current_item)

            if self.logger:
                self.logger.log(event_type="pen_start", tool="PEN")

            event.accept()
            return

        # ---------------- LINE ----------------
        if self._tool == Tool.LINE and event.button():
            self._shape_start = p
            self._shape_item = QGraphicsLineItem(QLineF(p, p))
            self._shape_item.setPen(self._make_pen(width=2))
            self._enable_interaction_flags(self._shape_item)
            self.addItem(self._shape_item)

            if self.logger:
                self.logger.log(event_type="line_start", tool="LINE")

            event.accept()
            return

        # ---------------- RECT ----------------
        if self._tool == Tool.RECT and event.button():
            self._shape_start = p
            self._shape_item = QGraphicsRectItem(QRectF(p, p))
            self._shape_item.setPen(self._make_pen(width=2))
            self._enable_interaction_flags(self._shape_item)
            self.addItem(self._shape_item)

            if self.logger:
                self.logger.log(event_type="rect_start", tool="RECT")

            event.accept()
            return

        # ---------------- ELLIPSE ----------------
        if self._tool == Tool.ELLIPSE and event.button():
            self._shape_start = p
            self._shape_item = QGraphicsEllipseItem(QRectF(p, p))
            self._shape_item.setPen(self._make_pen(width=2))
            self._enable_interaction_flags(self._shape_item)
            self.addItem(self._shape_item)

            if self.logger:
                self.logger.log(event_type="ellipse_start", tool="ELLIPSE")

            event.accept()
            return

        # ---------------- SELECT ----------------
        if self._tool == Tool.SELECT:
            self._press_item = self._item_at_scene_pos(p)
            self._press_pos = p

            if self.logger:
                self.logger.log(
                    event_type="select_press",
                    tool="SELECT",
                    item_type=(
                        type(self._press_item).__name__ if self._press_item else "None"
                    ),
                )

        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        p = event.scenePos()

        # ---------------- ERASER (gomme “continue”) ----------------
        if self._tool == Tool.ERASER:
            item = self._item_at_scene_pos(p)
            if item is not None:
                self.removeItem(item)
                if self.logger:
                    self.logger.log(
                        event_type="erase",
                        tool="ERASER",
                        item_type=type(item).__name__,
                        notes="move",
                    )
                event.accept()
                return
            super().mouseMoveEvent(event)
            return

        # ---------------- PEN ----------------
        if self._tool == Tool.PEN and self._current_path is not None:
            self._current_path.lineTo(p)
            self._points_count += 1
            self._current_item.setPath(self._current_path)
            event.accept()
            return

        # ---------------- LINE/RECT/ELLIPSE ----------------
        if (
            self._tool in (Tool.LINE, Tool.RECT, Tool.ELLIPSE)
            and self._shape_start is not None
            and self._shape_item is not None
        ):
            if self._tool == Tool.LINE:
                self._shape_item.setLine(QLineF(self._shape_start, p))
            else:
                rect = QRectF(self._shape_start, p).normalized()
                # rect/ellipse ont la même logique de bounding box
                if self._tool == Tool.RECT:
                    self._shape_item.setRect(rect)
                else:
                    self._shape_item.setRect(rect)

            event.accept()
            return

        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        p = event.scenePos()

        # ---------------- PEN ----------------
        if self._tool == Tool.PEN and self._current_path is not None:
            if self.logger:
                self.logger.log(
                    event_type="pen_end",
                    tool="PEN",
                    item_type="QGraphicsPathItem",
                    n_points=str(self._points_count),
                )

            self._current_path = None
            self._current_item = None
            self._points_count = 0

            event.accept()
            return

        # ---------------- LINE/RECT/ELLIPSE ----------------
        if (
            self._tool in (Tool.LINE, Tool.RECT, Tool.ELLIPSE)
            and self._shape_item is not None
        ):
            # log “end” avec un peu d’info utile
            if self.logger:
                if self._tool == Tool.LINE:
                    line = self._shape_item.line()
                    self.logger.log(
                        event_type="line_end",
                        tool="LINE",
                        item_type="QGraphicsLineItem",
                        notes=f"({line.x1():.1f},{line.y1():.1f})->({line.x2():.1f},{line.y2():.1f})",
                    )
                elif self._tool == Tool.RECT:
                    r = self._shape_item.rect()
                    self.logger.log(
                        event_type="rect_end",
                        tool="RECT",
                        item_type="QGraphicsRectItem",
                        notes=f"x={r.x():.1f},y={r.y():.1f},w={r.width():.1f},h={r.height():.1f}",
                    )
                else:
                    r = self._shape_item.rect()
                    self.logger.log(
                        event_type="ellipse_end",
                        tool="ELLIPSE",
                        item_type="QGraphicsEllipseItem",
                        notes=f"x={r.x():.1f},y={r.y():.1f},w={r.width():.1f},h={r.height():.1f}",
                    )

            self._shape_start = None
            self._shape_item = None

            event.accept()
            return

        # ---------------- SELECT ----------------
        if self._tool == Tool.SELECT and self._press_pos is not None:
            delta = p - self._press_pos
            moved = abs(delta.x()) + abs(delta.y()) > 2.0

            if moved and self.logger:
                self.logger.log(event_type="item_moved", tool="SELECT")

            self._press_item = None
            self._press_pos = None

        super().mouseReleaseEvent(event)
