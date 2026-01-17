import time
from assistant import wizard
from ui.suggestion_dialog import SuggestionDialog


class AssistantController:
    def __init__(self, editor_window, scene, logger):
        self.editor = editor_window
        self.scene = scene
        self.logger = logger

        self.auto_enabled = False
        self.floating_visible = True

        # Trigger automatique : quand un item utilisateur est créé
        self.scene.item_created.connect(self.on_item_created)

        # Trigger manuel : clic sur l'icône flottante
        self.editor.assistant_btn.clicked.connect(self.on_manual_invoke)

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
    def _build_context(self, trigger: str):
        # contexte minimal pour le prototype
        has_ellipse = any(
            it.__class__.__name__ == "QGraphicsEllipseItem" for it in self.scene.items()
        )
        return {"trigger": trigger, "has_ellipse": has_ellipse}

    # ---------- Triggers ----------
    def on_manual_invoke(self):
        if self.logger:
            self.logger.log("invoke_help", tool="ASSISTANT")

        self._try_suggest(trigger="manual")

    def on_item_created(self, item):
        if not self.auto_enabled:
            return
        self._try_suggest(trigger="auto")

    # ---------- Suggestion flow ----------
    def _try_suggest(self, trigger: str):
        ctx = self._build_context(trigger)
        t0 = time.time()

        proposal = wizard.propose_suggestion(ctx)

        if proposal is None:
            # Abstention / "Pas de suggestion"
            if self.logger:
                self.logger.log("ai_output", notes="none")
            dlg = SuggestionDialog(
                title="Pas de suggestion",
                uncertainty_pct=0,
                explanation=["Précondition non satisfaite (ex: aucune ellipse)."],
                what_to_do="Dessinez d'abord une forme cible, ou invoquez plus tard.",
            )
            dlg.exec()
            return

        # Log : suggestion affichée
        if self.logger:
            self.logger.log("ai_output", notes="shown")

        dlg = SuggestionDialog(
            title=proposal["suggestion"].label,
            uncertainty_pct=proposal["uncertainty_pct"],
            explanation=proposal["explanation"],
            what_to_do=proposal["what_to_do"],
        )
        dlg.exec()

        decision_ms = int((time.time() - t0) * 1000)
        choice = dlg.choice or "ignore"

        # Log décision utilisateur
        if self.logger:
            self.logger.log("user_action", tool="ASSISTANT", notes=choice)

        if choice == "accept":
            items = proposal["suggestion"].create_items(self.scene)
            for it in items:
                self.scene.addItem(it)
            if self.logger:
                self.logger.log("assistant_apply", notes=f"n_items={len(items)}")
