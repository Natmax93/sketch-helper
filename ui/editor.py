"""
Fenêtre principale d'édition.

Responsabilité :
- afficher la zone de dessin (QGraphicsView + QGraphicsScene)
- fournir une toolbar pour changer d'outil
- afficher un panneau assistant sous forme de DockWidget
"""

from PySide6.QtWidgets import (
    QMainWindow,
    QToolBar,
    QGraphicsView,
    QDockWidget,
)
from PySide6.QtGui import QAction, QColor, QPixmap, QIcon, QActionGroup
from PySide6.QtCore import Qt, QTimer

from drawing.scene import DrawingScene
from ui.assistant_panel import GenerationPanel
from drawing.tools import Tool
from logs.logger import EventLogger
from ui.assistant_floating import FloatingAssistantButton
from assistant.controller import AssistantController
from assistant.generation_catalog import create_generation_item


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

        def make_color_icon(color: QColor) -> QIcon:
            pm = QPixmap(16, 16)
            pm.fill(color)
            return QIcon(pm)

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

        copy_act = QAction("Copier", self)
        copy_act.setShortcut("Ctrl+C")
        copy_act.triggered.connect(lambda checked=False: self.scene.copy_selection())
        toolbar.addAction(copy_act)

        cut_act = QAction("Couper", self)
        cut_act.setShortcut("Ctrl+X")
        cut_act.triggered.connect(lambda checked=False: self.scene.cut_selection())
        toolbar.addAction(cut_act)

        paste_act = QAction("Coller", self)
        paste_act.setShortcut("Ctrl+V")
        paste_act.triggered.connect(lambda checked=False: self.scene.paste())
        toolbar.addAction(paste_act)

        dup_act = QAction("Dupliquer", self)
        dup_act.setShortcut("Ctrl+D")
        dup_act.triggered.connect(
            lambda checked=False: self.scene.duplicate_selection()
        )
        toolbar.addAction(dup_act)

        toolbar.addSeparator()

        stroke_colors = [
            ("Noir", QColor("#000000")),
            ("Rouge", QColor("#e53935")),
            ("Vert", QColor("#43a047")),
            ("Bleu", QColor("#1e88e5")),
            ("Violet", QColor("#8e24aa")),
            ("Orange", QColor("#fb8c00")),
        ]

        stroke_group = QActionGroup(self)
        stroke_group.setExclusive(True)

        for i, (name, c) in enumerate(stroke_colors):
            act = QAction(make_color_icon(c), name, self)
            act.setCheckable(True)
            if i == 0:
                act.setChecked(True)  # noir par défaut
            act.triggered.connect(
                lambda checked=False, col=c: self.scene.set_stroke_color(col)
            )
            stroke_group.addAction(act)
            toolbar.addAction(act)

        undo_action = self.scene.history().createUndoAction(self, "Annuler")
        redo_action = self.scene.history().createRedoAction(self, "Rétablir")

        undo_action.setShortcut("Ctrl+Z")
        redo_action.setShortcut("Ctrl+Shift+Z")  # ou Ctrl+Y

        toolbar.addSeparator()
        toolbar.addAction(undo_action)
        toolbar.addAction(redo_action)

        fill_group = QActionGroup(self)
        fill_group.setExclusive(True)

        # Action “Aucun”
        act_fill_none = QAction("Fill: aucun", self)
        act_fill_none.setCheckable(True)
        act_fill_none.setChecked(True)  # fill None par défaut
        act_fill_none.triggered.connect(lambda: self.scene.set_fill_color(None))
        fill_group.addAction(act_fill_none)
        toolbar.addAction(act_fill_none)

        fill_colors = [
            ("Fill rouge", QColor("#ffcdd2")),
            ("Fill vert", QColor("#c8e6c9")),
            ("Fill bleu", QColor("#bbdefb")),
            ("Fill jaune", QColor("#fff9c4")),
            ("Fill gris", QColor("#eeeeee")),
        ]

        for name, c in fill_colors:
            act = QAction(make_color_icon(c), name, self)
            act.setCheckable(True)
            act.triggered.connect(
                lambda checked=False, col=c: self.scene.set_fill_color(col)
            )
            fill_group.addAction(act)
            toolbar.addAction(act)

        # Options de l'assistant
        toolbar.addSeparator()

        act_auto = QAction("Auto suggestions", self)
        act_auto.setCheckable(True)
        toolbar.addAction(act_auto)

        act_float = QAction("Afficher assistant", self)
        act_float.setCheckable(True)
        act_float.setChecked(True)
        toolbar.addAction(act_float)

        # Bouton assistant

        self.assistant_btn = FloatingAssistantButton(self.view.viewport())
        self.assistant_btn.show()

        def place_btn():
            margin = 12
            vp = self.view.viewport()
            self.assistant_btn.move(
                vp.width() - self.assistant_btn.width() - margin,
                vp.height() - self.assistant_btn.height() - margin,
            )

        self._place_assistant_btn = place_btn

        # Placement initial différé : laisse Qt finir le layout
        QTimer.singleShot(0, self._place_assistant_btn)

        # Contrôleur de l'assistant

        self.assistant_controller = AssistantController(self, self.scene, self.logger)

        act_auto.toggled.connect(self.assistant_controller.set_auto_enabled)
        act_float.toggled.connect(self.assistant_controller.set_floating_visible)

        # --- Panneau (Dock) de génération d'items ---

        self.gen_panel = GenerationPanel()

        self.gen_dock = QDockWidget("Génération IA", self)
        self.gen_dock.setWidget(self.gen_panel)
        self.addDockWidget(Qt.RightDockWidgetArea, self.gen_dock)

        # caché par défaut
        self.gen_dock.hide()

        # Ajouter une action toolbar "Génération IA" qui toggle le dock

        act_gen = QAction("Génération IA", self)
        act_gen.setCheckable(True)  # permet un état ON/OFF
        act_gen.setChecked(False)
        toolbar.addAction(act_gen)

        def toggle_gen(checked: bool):
            self.gen_dock.setVisible(checked)

        act_gen.toggled.connect(toggle_gen)

        def on_suggestion(category: str, item_id: str):
            # 1) créer items
            items = create_generation_item(category, item_id)

            # 2) positionner intelligemment : proche du centre de la vue
            center = self.view.mapToScene(self.view.viewport().rect().center())
            for it in items:
                it.setPos(center)

                # ajouter à la scène
                self.scene.addItem(it)

            # 3) log (si tu as self.logger)
            if hasattr(self, "logger") and self.logger:
                prompt = self.gen_panel.get_prompt_text()
                self.logger.log(
                    "gen_add", tool="GEN", notes=f"{category}:{item_id}|prompt={prompt}"
                )

        self.gen_panel.suggestion_chosen.connect(on_suggestion)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._place_assistant_btn()
