"""
Fenêtre principale d'édition.

Responsabilité :
- afficher la zone de dessin (QGraphicsView + QGraphicsScene)
- fournir une toolbar pour changer d'outil
- afficher un panneau assistant sous forme de DockWidget
"""

from pathlib import Path
import time

from PySide6.QtWidgets import (
    QMainWindow,
    QToolBar,
    QGraphicsView,
    QDockWidget,
    QToolButton,
    QLabel,
    QColorDialog,
    QButtonGroup,
    QVBoxLayout,
    QPushButton,
    QWidget,
    QDialog,
    QHBoxLayout,
)
from PySide6.QtGui import QAction, QColor, QPainter, QPen, QPixmap
from PySide6.QtCore import Qt, QTimer, Signal

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

        # --- Condition between-subjects (simple) ---
        self.condition = None  # choisie au moment du test

        # True si H_ONLY False sinon (mode vérrouillé)
        self._test_lock = False

        # --- Protocole test ---
        self._test_running = False
        self._trial_started_at = None  # time.time()
        self._tasks = [("cat", "Chat"), ("castle", "Château"), ("car", "Voiture")]
        self._trial_index = -1

        self.scene = DrawingScene(logger=self.logger)
        self.view = QGraphicsView(self.scene)

        # Par défaut, sélection
        self.view.setDragMode(QGraphicsView.RubberBandDrag)

        self.setCentralWidget(self.view)

        # Fenêtre de test
        self.task_window = TaskWindow()
        self.task_window.doneClicked.connect(self.on_done_clicked)
        self.task_window.set_done_enabled(False)

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

        self.act_auto = QAction("Auto suggestions", self)
        self.act_auto.setCheckable(True)
        toolbar.addAction(self.act_auto)

        self.act_float = QAction("Afficher assistant", self)
        self.act_float.setCheckable(True)
        self.act_float.setChecked(True)
        toolbar.addAction(self.act_float)

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

        self.act_auto.toggled.connect(self.assistant_controller.set_auto_enabled)
        self.act_float.toggled.connect(self.assistant_controller.set_floating_visible)

        # --- Panneau (Dock) de génération d'items ---

        self.gen_panel = GenerationPanel()

        self.gen_dock = QDockWidget("Génération IA", self)
        self.gen_dock.setWidget(self.gen_panel)
        self.addDockWidget(Qt.LeftDockWidgetArea, self.gen_dock)

        # caché par défaut
        self.gen_dock.hide()

        # Ajouter une action toolbar "Génération IA" qui toggle le dock

        self.act_gen = QAction("Génération IA", self)
        self.act_gen.setCheckable(True)  # permet un état ON/OFF
        self.act_gen.setChecked(False)
        toolbar.addAction(self.act_gen)

        self.act_gen.toggled.connect(self._toggle_gen_dock_guarded)

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
        # act_tpl = QAction("Template Builder (dev)", self)
        # act_tpl.triggered.connect(self._open_template_builder)
        # toolbar.addSeparator()
        # toolbar.addAction(act_tpl)

        # editor.py (dans __init__, après tes autres actions toolbar)

        toolbar.addSeparator()

        self.act_test = QAction("Test", self)
        self.act_test.triggered.connect(self.start_test)
        toolbar.addAction(self.act_test)

        self.act_done = QAction("Done", self)
        self.act_done.setEnabled(False)  # activé seulement pendant un essai
        self.act_done.triggered.connect(self.on_done_clicked)
        toolbar.addAction(self.act_done)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._place_assistant_btn()

    def _open_template_builder(self):
        if not hasattr(self, "_tpl_builder") or self._tpl_builder is None:
            self._tpl_builder = TemplateBuilderWindow(parent=self)
        self._tpl_builder.show()
        self._tpl_builder.raise_()
        self._tpl_builder.activateWindow()

    def start_test(self):
        if self._test_running:
            return

        # Choisir la condition AU DÉBUT du test
        dlg = ConditionDialog(self)
        if dlg.exec() != QDialog.Accepted or dlg.selected_condition is None:
            return

        # Verrouillage condition pour tout le test
        self.condition = dlg.selected_condition

        # Appliquer contexte logger (Solution A)
        self.logger.set_context(condition=self.condition)

        # Log haut niveau (utile pour audit)
        self.logger.log(
            "test_start", notes=f"condition={self.condition};3_tasks_fixed_order"
        )

        # Verrouiller uniquement si test H_ONLY
        if self.condition == "H_ONLY":
            self._apply_h_only_lock(True)
        else:
            # H_PLUS_IA : on laisse les contrôles tels quels
            self._apply_h_only_lock(False)

        # Activer/désactiver l'assistant pour toute la durée du test
        self._apply_assistant_condition(self.condition)

        # Lancer protocole
        self._test_running = True
        self.act_test.setEnabled(False)
        self._trial_index = -1
        self._trial_started_at = None

        self._start_next_trial()

    def _toggle_gen_dock_guarded(self, checked: bool):
        # Si on est en test H_ONLY, on bloque toute ouverture/fermeture via l'action
        if self._test_running and self.condition == "H_ONLY":
            # on force l'action à OFF pour cohérence visuelle
            self.act_gen.blockSignals(True)
            self.act_gen.setChecked(False)
            self.act_gen.blockSignals(False)

            self.gen_dock.hide()
            return

        self.gen_dock.setVisible(checked)

    def _apply_assistant_condition(self, condition: str):
        """Applique la condition expérimentale au comportement assistant."""
        if condition == "H_ONLY":
            # Le verrouillage gère déjà l'UI ; ici on assure juste la logique
            self.assistant_controller.set_auto_enabled(False)
            self.assistant_controller.set_floating_visible(False)
        else:
            # IA autorisée : ne force pas OFF, laisse l'utilisateur choisir
            self.assistant_btn.setEnabled(True)

    def _start_next_trial(self):
        self._trial_index += 1

        if self._trial_index >= len(self._tasks):
            self._end_test()
            return

        task_id, label = self._tasks[self._trial_index]

        # Contexte logger pour tagger tous les events fins
        self.logger.set_context(task_id=task_id, trial_index=self._trial_index + 1)

        # Mettre à jour / afficher la fenêtre modèle (non-modale)
        pm = make_task_pixmap(task_id)
        self.task_window.set_task(label, pm)
        self.task_window.set_done_enabled(True)
        self.task_window.show()
        self.task_window.raise_()
        self.task_window.activateWindow()

        # Reset scène (prototype)
        self.scene.clear()
        self.scene.undo_stack.clear()

        # Démarrer l’essai immédiatement (puisque la fenêtre ne “valide” plus)
        self._trial_started_at = time.time()
        self.logger.log("trial_start", notes=f"task={task_id}")

    def on_done_clicked(self):
        if not self._test_running or self._trial_started_at is None:
            return

        now = time.time()
        duration_s = now - self._trial_started_at

        # Logs haut niveau
        self.logger.log("done_clicked")
        self.logger.log("trial_end", notes=f"duration_s={duration_s:.3f}")

        # Préparer essai suivant
        self._trial_started_at = None
        self.task_window.set_done_enabled(False)

        self._start_next_trial()

    def _end_test(self, cancelled: bool = False):
        self._test_running = False
        self.act_test.setEnabled(True)
        self.task_window.set_done_enabled(False)
        self.task_window.close()

        # Déverrouiller si on était en H_ONLY
        if self.condition == "H_ONLY":
            self._apply_h_only_lock(False)

        self.logger.log("test_end", notes=("cancelled" if cancelled else "completed"))

        # Nettoyer contexte essai (optionnel)
        self.logger.set_context(task_id="", trial_index="")

    def _apply_h_only_lock(self, enabled: bool):
        """
        Verrouille/déverrouille les contrôles IA pendant un test H_ONLY.
        Ne doit pas être appelé pour H_PLUS_IA.
        """
        self._test_lock = enabled

        if enabled:
            # 1) Fermer le dock et empêcher son ouverture
            self.gen_dock.hide()
            self.act_gen.blockSignals(True)
            self.act_gen.setChecked(False)
            self.act_gen.blockSignals(False)
            self.act_gen.setEnabled(False)

            # 2) Désactiver Auto suggestions + forcer OFF
            self.assistant_controller.set_auto_enabled(False)
            self.act_auto.blockSignals(True)
            self.act_auto.setChecked(False)
            self.act_auto.blockSignals(False)
            self.act_auto.setEnabled(False)

            # 3) Désactiver Afficher assistant + forcer OFF
            self.assistant_controller.set_floating_visible(False)
            self.act_float.blockSignals(True)
            self.act_float.setChecked(False)
            self.act_float.blockSignals(False)
            self.act_float.setEnabled(False)

            # 4) Désactiver bouton assistant flottant
            self.assistant_btn.setEnabled(False)

        else:
            # Réactiver contrôles (état par défaut ; l'utilisateur choisira ensuite)
            self.act_gen.setEnabled(True)
            self.act_auto.setEnabled(True)
            self.act_float.setEnabled(True)
            self.assistant_btn.setEnabled(True)


class TaskWindow(QWidget):
    doneClicked = Signal()

    def __init__(self, parent=None):
        # Qt.Window => vraie fenêtre indépendante (pas juste un widget enfant)
        super().__init__(parent)
        self.setWindowTitle("Modèle à reproduire")

        self._label = QLabel(self)
        self._label.setAlignment(Qt.AlignCenter)

        self._done_btn = QPushButton("Done", self)
        self._done_btn.clicked.connect(self.doneClicked.emit)

        layout = QVBoxLayout(self)
        layout.addWidget(self._label)
        layout.addWidget(self._done_btn)

        # Optionnel : empêcher le redimensionnement trop petit
        self.setMinimumSize(260, 300)

    def set_task(self, title: str, pixmap):
        self.setWindowTitle(f"Modèle : {title}")
        self._label.setPixmap(pixmap)

    def set_done_enabled(self, enabled: bool):
        self._done_btn.setEnabled(enabled)


def make_task_pixmap(task_id: str, size: int = 220) -> QPixmap:
    """
    Charge un PNG de référence pour la tâche et le met au bon format d'affichage.

    - task_id: "cat" | "castle" | "car"
    - size: taille (carrée) cible d'affichage dans la TaskWindow
    """
    mapping = {
        "cat": "cat_model.png",
        "castle": "castle_model.png",
        "car": "car_model.png",
    }

    filename = mapping.get(task_id)
    if not filename:
        # fallback : pixmap vide
        pm = QPixmap(size, size)
        pm.fill(Qt.white)
        return pm

    # Chemin de l'image
    img_path = f"assets/tasks/{filename}"

    pm = QPixmap(str(img_path))
    if pm.isNull():
        # Fallback si le PNG n'est pas trouvé/chargeable
        fallback = QPixmap(size, size)
        fallback.fill(Qt.white)
        painter = QPainter(fallback)
        painter.setPen(QPen(Qt.black))
        painter.drawText(
            fallback.rect(), Qt.AlignCenter, f"Image introuvable:\n{img_path}"
        )
        painter.end()
        return fallback

    # Redimensionnement : conserve le ratio et évite l'effet “pixellisé”
    pm = pm.scaled(size, size, Qt.KeepAspectRatio, Qt.SmoothTransformation)

    # Option : placer sur fond blanc (utile si PNG transparent)
    out = QPixmap(size, size)
    out.fill(Qt.white)
    painter = QPainter(out)
    x = (size - pm.width()) // 2
    y = (size - pm.height()) // 2
    painter.drawPixmap(x, y, pm)
    painter.end()

    return out


class ConditionDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Choix du mode de test")
        self.setModal(True)

        self.selected_condition = None  # "H_ONLY" ou "H_PLUS_IA"

        layout = QVBoxLayout(self)
        layout.addWidget(
            QLabel("Souhaites-tu faire le test avec IA ou sans IA ?", self)
        )

        row = QHBoxLayout()
        btn_no = QPushButton("Sans IA", self)
        btn_ai = QPushButton("Avec IA", self)

        btn_no.clicked.connect(lambda: self._choose("H_ONLY"))
        btn_ai.clicked.connect(lambda: self._choose("H_PLUS_IA"))

        row.addWidget(btn_no)
        row.addWidget(btn_ai)
        layout.addLayout(row)

    def _choose(self, condition: str):
        self.selected_condition = condition
        self.accept()
