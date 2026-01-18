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
    QToolButton,
    QLabel,
    QColorDialog,
    QButtonGroup,
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
from drawing.commands import AddItemCommand
from ui.template_builder import TemplateBuilderWindow


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

        def make_swatch_button(hex_color: str, tooltip: str, on_pick):
            """
            Crée un bouton-couleur (QToolButton) checkable, avec rendu proche Template Builder
            MAIS avec un style :checked (bouton enfoncé).
            """
            btn = QToolButton(self)
            btn.setFixedSize(18, 18)
            btn.setCheckable(True)
            btn.setToolTip(tooltip)

            btn.setStyleSheet(
                f"""
                QToolButton {{
                    background-color: {hex_color};
                    border: 1px solid #444;
                    border-radius: 3px;
                    margin: 2px;
                }}
                QToolButton:hover {{
                    border: 2px solid #222;
                }}
                QToolButton:checked {{
                    border: 3px solid #111;     /* effet "enfoncé" / sélection */
                    margin: 0px;                /* compense l'épaisseur du border */
                }}
                """
            )

            btn.clicked.connect(on_pick)
            return btn

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

        # Palette rapide : noir, rouge, bleu, vert, gris
        quick_palette = [
            "#000000",  # noir
            "#FF0000",  # rouge
            "#0000FF",  # bleu
            "#00FF00",  # vert
            "#808080",  # gris
        ]

        toolbar.addWidget(QLabel("Contour:", self))

        stroke_group = QButtonGroup(self)
        stroke_group.setExclusive(True)

        # --- 4 swatches ---
        for hx in quick_palette:
            btn = make_swatch_button(
                hx,
                f"Contour {hx}",
                lambda checked=False, h=hx: self.scene.set_stroke_color(QColor(h)),
            )
            stroke_group.addButton(btn)
            toolbar.addWidget(btn)

        # --- Bouton "..." (couleur custom) ---
        btn_more_stroke = QToolButton(self)
        btn_more_stroke.setText("…")
        btn_more_stroke.setFixedSize(22, 18)
        btn_more_stroke.setCheckable(True)
        btn_more_stroke.setToolTip("Choisir une couleur de contour")

        # Style cohérent + état checked visible
        btn_more_stroke.setStyleSheet(
            """
            QToolButton { border: 1px solid #444; border-radius: 3px; margin: 1px; padding: 0px 4px; }
            QToolButton:hover { border: 2px solid #222; }
            QToolButton:checked { border: 3px solid #111; margin: 0px; }
            """
        )

        def choose_custom_stroke():
            c = QColorDialog.getColor(
                self.scene.stroke_color(), parent=self, title="Couleur du contour"
            )
            if c.isValid():
                self.scene.set_stroke_color(c)

                # Teinter le bouton de la couleur actuellement sélectionnée
                btn_more_stroke.setStyleSheet(
                    f"""
                    QToolButton {{
                        background-color: {c.name()};
                        border: 1px solid #444;
                        border-radius: 3px;
                        margin: 1px;
                        padding: 0px 4px;
                    }}
                    QToolButton:hover {{ border: 2px solid #222; }}
                    QToolButton:checked {{ border: 3px solid #111; margin: 0px; }}
                    """
                )

                # Indique visuellement "custom" : le bouton … devient sélectionné
                btn_more_stroke.setChecked(True)

        btn_more_stroke.clicked.connect(lambda checked=False: choose_custom_stroke())
        stroke_group.addButton(btn_more_stroke)
        toolbar.addWidget(btn_more_stroke)

        # Valeur par défaut : noir sélectionné
        # (On coche le premier bouton ajouté : le noir)
        stroke_buttons = stroke_group.buttons()
        if stroke_buttons:
            stroke_buttons[0].setChecked(True)
            self.scene.set_stroke_color(QColor(quick_palette[0]))

        toolbar.addSeparator()
        toolbar.addWidget(QLabel("Remplissage:", self))

        fill_group = QButtonGroup(self)
        fill_group.setExclusive(True)

        # --- Bouton "Aucun" (pas de fill) ---
        btn_no_fill = QToolButton(self)
        btn_no_fill.setText("Aucun")
        btn_no_fill.setCheckable(True)
        btn_no_fill.setToolTip("Pas de remplissage")
        btn_no_fill.setStyleSheet(
            """
            QToolButton { border: 1px solid #444; border-radius: 3px; margin: 1px; padding: 0px 6px; }
            QToolButton:hover { border: 2px solid #222; }
            QToolButton:checked { border: 3px solid #111; margin: 0px; }
            """
        )
        btn_no_fill.clicked.connect(
            lambda checked=False: self.scene.set_fill_color(None)
        )
        fill_group.addButton(btn_no_fill)
        toolbar.addWidget(btn_no_fill)

        # --- 4 swatches ---
        for hx in quick_palette:
            btn = make_swatch_button(
                hx,
                f"Remplissage {hx}",
                lambda checked=False, h=hx: self.scene.set_fill_color(QColor(h)),
            )
            fill_group.addButton(btn)
            toolbar.addWidget(btn)

        # --- Bouton "..." (fill custom) ---
        btn_more_fill = QToolButton(self)
        btn_more_fill.setText("…")
        btn_more_fill.setFixedSize(22, 18)
        btn_more_fill.setCheckable(True)
        btn_more_fill.setToolTip("Choisir une couleur de remplissage")
        btn_more_fill.setStyleSheet(
            """
            QToolButton { border: 1px solid #444; border-radius: 3px; margin: 1px; padding: 0px 4px; }
            QToolButton:hover { border: 2px solid #222; }
            QToolButton:checked { border: 3px solid #111; margin: 0px; }
            """
        )

        def choose_custom_fill():
            current = self.scene.fill_color()
            c = QColorDialog.getColor(
                current if current else QColor("#ffffff"),
                parent=self,
                title="Couleur du remplissage",
            )
            if c.isValid():
                self.scene.set_fill_color(c)

                # Teinter le bouton de la couleur actuellement sélectionnée
                btn_more_fill.setStyleSheet(
                    f"""
                    QToolButton {{
                        background-color: {c.name()};
                        border: 1px solid #444;
                        border-radius: 3px;
                        margin: 1px;
                        padding: 0px 4px;
                    }}
                    QToolButton:hover {{ border: 2px solid #222; }}
                    QToolButton:checked {{ border: 3px solid #111; margin: 0px; }}
                    """
                )

                btn_more_fill.setChecked(True)

        btn_more_fill.clicked.connect(lambda checked=False: choose_custom_fill())
        fill_group.addButton(btn_more_fill)
        toolbar.addWidget(btn_more_fill)

        # Valeur par défaut : "Aucun" sélectionné
        btn_no_fill.setChecked(True)
        self.scene.set_fill_color(None)

        undo_action = self.scene.history().createUndoAction(self, "Annuler")
        redo_action = self.scene.history().createRedoAction(self, "Rétablir")

        undo_action.setShortcut("Ctrl+Z")
        redo_action.setShortcut("Ctrl+Shift+Z")  # ou Ctrl+Y

        toolbar.addSeparator()
        toolbar.addAction(undo_action)
        toolbar.addAction(redo_action)

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
        self.addDockWidget(Qt.LeftDockWidgetArea, self.gen_dock)

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

            # Macro = un seul undo pour l'ensemble
            self.scene.undo_stack.beginMacro(f"Generate {category}:{item_id}")

            for it in items:
                it.setPos(center)

                # ajouter à la scène
                self.scene.addItem(it)

                # 2) Commande undoable (already_in_scene=True car déjà ajouté)
                self.scene.undo_stack.push(
                    AddItemCommand(
                        self.scene, it, text="Generated item", already_in_scene=True
                    )
                )

            self.scene.undo_stack.endMacro()

            # 3) log (si tu as self.logger)
            if hasattr(self, "logger") and self.logger:
                prompt = self.gen_panel.get_prompt_text()
                self.logger.log(
                    "gen_add", tool="GEN", notes=f"{category}:{item_id}|prompt={prompt}"
                )

        self.gen_panel.suggestion_chosen.connect(on_suggestion)

        # --- Template Builder (dev) ---
        # TODO : à commenter une fois les templates créés
        act_tpl = QAction("Template Builder (dev)", self)
        act_tpl.triggered.connect(self._open_template_builder)
        toolbar.addSeparator()
        toolbar.addAction(act_tpl)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._place_assistant_btn()

    def _open_template_builder(self):
        if not hasattr(self, "_tpl_builder") or self._tpl_builder is None:
            self._tpl_builder = TemplateBuilderWindow(parent=self)
        self._tpl_builder.show()
        self._tpl_builder.raise_()
        self._tpl_builder.activateWindow()
