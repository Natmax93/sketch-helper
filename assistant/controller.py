import time
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QGraphicsEllipseItem, QGraphicsRectItem
from PySide6.QtGui import QPixmap
from pathlib import Path

from assistant import wizard
from ui.suggestion_dialog import SuggestionDialog
from drawing.commands import AddItemCommand


# Doit matcher le tag que tu mettras sur les oreilles dans assistant/suggestions.py
ASSISTANT_TAG_ROLE = int(Qt.UserRole)
TAG_CAT_EAR = "assistant:cat_ear"
TAG_ROOF_TRIANGLE = "assistant:roof_triangle"


class AssistantController:
    def __init__(self, editor_window, scene, logger):
        self.editor = editor_window
        self.scene = scene
        self.logger = logger

        self.auto_enabled = False
        self.floating_visible = True

        # Suggestions ignorées/refusées en auto (dans cette session)
        self._auto_suppressed = set()

        # Trigger automatique : quand un item utilisateur est créé
        self.scene.item_created.connect(self.on_item_created)

        # Trigger manuel : clic sur l'icône flottante
        self.editor.assistant_btn.clicked.connect(self.on_manual_invoke)

        # Prévisualisation des suggestions
        self._ghost_items = []

    def set_auto_enabled(self, enabled: bool):
        self.auto_enabled = enabled
        if self.logger:
            self.logger.log("assistant_auto_toggle", notes=str(enabled))

    def set_floating_visible(self, visible: bool):
        self.floating_visible = visible
        self.editor.assistant_btn.setVisible(visible)
        if self.logger:
            self.logger.log("assistant_floating_toggle", notes=str(visible))

    # ---------- Context helpers ----------
    def _build_context(self, trigger: str, created_item=None):
        items = self.scene.items()

        has_ellipse = any(isinstance(it, QGraphicsEllipseItem) for it in items)
        has_rect = any(isinstance(it, QGraphicsRectItem) for it in items)

        has_cat_ears = any(
            getattr(it, "data", lambda *_: None)(ASSISTANT_TAG_ROLE) == TAG_CAT_EAR
            for it in items
        )
        has_roof_triangle = any(
            getattr(it, "data", lambda *_: None)(ASSISTANT_TAG_ROLE)
            == TAG_ROOF_TRIANGLE
            for it in items
        )

        created_kind = type(created_item).__name__ if created_item is not None else None

        return {
            "trigger": trigger,
            "has_ellipse": has_ellipse,
            "has_rect": has_rect,
            "has_cat_ears": has_cat_ears,
            "has_roof_triangle": has_roof_triangle,
            "created_kind": created_kind,
            "auto_suppressed": set(self._auto_suppressed),
        }

    # ---------- Triggers ----------
    def on_manual_invoke(self):
        if self.logger:
            self.logger.log("invoke_help", tool="ASSISTANT")

        self._try_suggest(trigger="manual", created_item=None)

    def on_item_created(self, item):
        if not self.auto_enabled:
            return
        self._try_suggest(trigger="auto", created_item=item)

    # ---------- Suggestion flow ----------
    def _try_suggest(self, trigger: str, created_item=None):
        ctx = self._build_context(trigger, created_item=created_item)
        t0 = time.time()

        proposal = wizard.propose_suggestion(ctx)

        if proposal is None:
            # Abstention : en auto on ne montre rien
            if self.logger:
                self.logger.log("ai_output", tool="ASSISTANT", notes=f"none:{trigger}")
            if trigger == "manual":
                dlg = SuggestionDialog(
                    title="Pas de suggestion",
                    uncertainty_pct=0,
                    explanation=["Aucune suggestion pertinente pour le moment."],
                    what_to_do="Ajoutez une forme cible, ou réessayez plus tard.",
                )
                dlg.exec()
            return

        # Log : suggestion affichée
        if self.logger:
            sid = proposal.get("suggestion_id", "unknown")
            self.logger.log(
                "ai_output", tool="ASSISTANT", notes=f"shown:{trigger}:{sid}"
            )

        # Nettoie un éventuel ghost précédent
        self._clear_ghost()

        # Crée les items proposés
        ghost = proposal["suggestion"].create_items(self.scene)

        # Ajoute temporairement en "grisé"
        for it in ghost:
            it.setOpacity(0.35)
            it.setEnabled(False)
            it.setFlag(it.GraphicsItemFlag.ItemIsSelectable, False)
            it.setFlag(it.GraphicsItemFlag.ItemIsMovable, False)
            self.scene.addItem(it)

        self._ghost_items = ghost

        dlg = SuggestionDialog(
            title=proposal["suggestion"].label,
            uncertainty_pct=proposal["uncertainty_pct"],
            explanation=proposal["explanation"],
            what_to_do=proposal["what_to_do"],
            preview_pixmap=self._load_preview_pixmap(proposal["suggestion"]),
        )
        dlg.exec()

        decision_ms = int((time.time() - t0) * 1000)

        # Fermeture fenêtre = cancel (au lieu de ignore implicite)
        choice = dlg.choice or "cancel"

        if self.logger:
            sid = proposal.get("suggestion_id", "unknown")
            self.logger.log(
                "user_action",
                tool="ASSISTANT",
                notes=f"{choice}:{trigger}:{sid}:ms={decision_ms}",
            )

        # Si l'utilisateur n'applique pas :
        # - en auto : on supprime la répétition de cette suggestion (session)
        if choice in ("ignore", "override", "cancel"):
            if trigger == "auto":
                sid = proposal.get("suggestion_id")
                if sid:
                    self._auto_suppressed.add(sid)
                    if self.logger:
                        self.logger.log(
                            "assistant_suppress", tool="ASSISTANT", notes=f"{sid}"
                        )
            return

        if choice == "accept":
            # On "valide" : enlève le ghosting et rend undoable
            self.scene.undo_stack.beginMacro(
                f"Assistant: {proposal.get('suggestion_id','suggestion')}"
            )

            for it in self._ghost_items:
                it.setOpacity(1.0)
                it.setEnabled(True)
                it.setFlag(it.GraphicsItemFlag.ItemIsSelectable, True)
                it.setFlag(it.GraphicsItemFlag.ItemIsMovable, True)

                # already_in_scene=True car déjà visible (ghost)
                self.scene.undo_stack.push(
                    AddItemCommand(
                        self.scene,
                        it,
                        text="Assistant suggestion",
                        already_in_scene=True,
                    )
                )

            self.scene.undo_stack.endMacro()

            self._ghost_items = []

        else:
            # ignore / override / cancel => on retire les items
            self._clear_ghost()

    def _load_preview_pixmap(self, suggestion):
        path = getattr(suggestion, "preview_path", None)
        if not path:
            return None

        # Chemin relatif projet -> absolu
        root = Path(__file__).resolve().parents[1]
        abs_path = root / path
        if not abs_path.exists():
            return None
        pm = QPixmap(str(abs_path))
        return pm if not pm.isNull() else None

    def _clear_ghost(self):
        for it in self._ghost_items:
            if it.scene() is not None:
                self.scene.removeItem(it)
        self._ghost_items = []
