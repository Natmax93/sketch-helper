"""
Fenêtre principale d'édition.

Responsabilité :
- afficher la zone de dessin (QGraphicsView + QGraphicsScene)
- fournir une toolbar pour changer d'outil
- afficher un panneau assistant sous forme de DockWidget
"""

from PySide6.QtWidgets import QMainWindow, QToolBar, QGraphicsView, QDockWidget
from PySide6.QtGui import QAction
from PySide6.QtCore import Qt

from drawing.scene import DrawingScene
from ui.assistant_panel import AssistantPanel
from drawing.tools import Tool
from logs.logger import EventLogger


class EditorWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Éditeur - Prototype HAII")

        self.logger = EventLogger("logs/events.csv")

        self.scene = DrawingScene(logger=self.logger)
        self.view = QGraphicsView(self.scene)

        # Par défaut, sélection
        self.view.setDragMode(QGraphicsView.RubberBandDrag)

        self.setCentralWidget(self.view)

        toolbar = QToolBar("Outils")
        self.addToolBar(toolbar)

        def set_tool_and_view_mode(tool: Tool):
            self.scene.set_tool(tool)
            self.view.setDragMode(
                QGraphicsView.RubberBandDrag
                if tool == Tool.SELECT
                else QGraphicsView.NoDrag
            )

        act_select = QAction("Sélection", self)
        act_select.triggered.connect(lambda: set_tool_and_view_mode(Tool.SELECT))
        toolbar.addAction(act_select)

        act_pen = QAction("Stylo", self)
        act_pen.triggered.connect(lambda: set_tool_and_view_mode(Tool.PEN))
        toolbar.addAction(act_pen)

        act_eraser = QAction("Gomme", self)
        act_eraser.triggered.connect(lambda: set_tool_and_view_mode(Tool.ERASER))
        toolbar.addAction(act_eraser)

        act_line = QAction("Trait", self)
        act_line.triggered.connect(lambda: set_tool_and_view_mode(Tool.LINE))
        toolbar.addAction(act_line)

        act_rect = QAction("Rectangle", self)
        act_rect.triggered.connect(lambda: set_tool_and_view_mode(Tool.RECT))
        toolbar.addAction(act_rect)

        act_ellipse = QAction("Ellipse", self)
        act_ellipse.triggered.connect(lambda: set_tool_and_view_mode(Tool.ELLIPSE))
        toolbar.addAction(act_ellipse)

        dock = QDockWidget("Assistant", self)
        dock.setWidget(AssistantPanel())
        self.addDockWidget(Qt.LeftDockWidgetArea, dock)
