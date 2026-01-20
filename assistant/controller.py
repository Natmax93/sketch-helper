"""
assistant/controller.py

Contrôleur de l'assistant :
- écoute des triggers (manuel / auto)
- demande au "wizard" une suggestion en fonction du contexte
- affiche une fenêtre de suggestion (SuggestionDialog)
- gère une prévisualisation "ghost" sur la scène

Correctif principal (bug "ghost non retiré") :
- Dans la version précédente, un `return` anticipé dans le bloc
  `if choice in ("ignore","override","cancel"):` empêchait l'appel à `_clear_ghost()`.
  Résultat : si l'utilisateur ignorait/refusait/cancel, le ghost restait affiché.
- Ici, on structure le flux pour que :
  - si `choice == "accept"` : on "commit" et on garde les items (on retire l'effet ghost)
  - sinon : on retire systématiquement le ghost via `_clear_ghost()`
  - et ce nettoyage se fait même en cas d'exception ou fermeture inattendue grâce à `try/finally`

Remarque :
- Le commit "undoable" se fait via AddItemCommand(already_in_scene=True) puisque les items
  sont déjà dans la scène en tant que ghost.
"""

import time
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QGraphicsEllipseItem, QGraphicsRectItem

from assistant import wizard
from drawing.commands import AddItemCommand
from ui.suggestion_dialog import SuggestionDialog


# ---- Tags/roles : permet d'identifier des items ajoutés par l'assistant ----
# Doit matcher le tag que tu mets sur les items (ex: oreilles) dans assistant/suggestions.py
ASSISTANT_TAG_ROLE = int(Qt.UserRole)
TAG_CAT_EAR = "assistant:cat_ear"
TAG_ROOF_TRIANGLE = "assistant:roof_triangle"


class AssistantController:
    """
    Pilote la logique de suggestion.

    Responsabilités :
    - Construire un contexte minimal depuis la scène
    - Obtenir une proposition du wizard
    - Afficher la suggestion à l'utilisateur
    - Gérer la prévisualisation ghost + commit/rollback
    """

    def __init__(self, editor_window, scene, logger):
        # Référence vers la fenêtre principale (bouton flottant, etc.)
        self.editor = editor_window

        # Référence vers la QGraphicsScene (DrawingScene) principale
        self.scene = scene

        # Logger (peut être None)
        self.logger = logger

        # Paramètres UI / comportement
        self.auto_enabled = False
        self.floating_visible = True

        # Ensemble de suggestions ignorées/refusées automatiquement pendant la session
        # (pour éviter le spam en mode auto)
        self._auto_suppressed = set()

        # Trigger automatique : quand un item utilisateur est créé
        self.scene.item_created.connect(self.on_item_created)

        # Trigger manuel : clic sur l'icône flottante
        self.editor.assistant_btn.clicked.connect(self.on_manual_invoke)

        # Liste des items actuellement en "ghost preview"
        self._ghost_items = []

    # ---------------------------------------------------------------------
    # Paramétrage assistant
    # ---------------------------------------------------------------------
    def set_auto_enabled(self, enabled: bool):
        """
        Active/désactive les suggestions automatiques (déclenchées à chaque création d'item).
        """
        self.auto_enabled = enabled
        if self.logger:
            self.logger.log("assistant_auto_toggle", notes=str(enabled))

    def set_floating_visible(self, visible: bool):
        """
        Affiche/masque le bouton flottant de l'assistant.
        """
        self.floating_visible = visible
        self.editor.assistant_btn.setVisible(visible)
        if self.logger:
            self.logger.log("assistant_floating_toggle", notes=str(visible))

    # ---------------------------------------------------------------------
    # Construction du contexte minimal pour le wizard
    # ---------------------------------------------------------------------
    def _build_context(self, trigger: str, created_item=None):
        """
        Construit un dict de contexte à partir de l'état actuel de la scène.

        - trigger : "manual" ou "auto"
        - created_item : l'item nouvellement créé (si auto), sinon None
        """
        items = self.scene.items()

        # Détecte la présence de formes de base
        has_ellipse = any(isinstance(it, QGraphicsEllipseItem) for it in items)
        has_rect = any(isinstance(it, QGraphicsRectItem) for it in items)

        # Détecte si les items assistant ont déjà été ajoutés (via tags)
        has_cat_ears = any(
            getattr(it, "data", lambda *_: None)(ASSISTANT_TAG_ROLE) == TAG_CAT_EAR
            for it in items
        )
        has_roof_triangle = any(
            getattr(it, "data", lambda *_: None)(ASSISTANT_TAG_ROLE)
            == TAG_ROOF_TRIANGLE
            for it in items
        )

        # Type de l'item récemment créé (utile pour certaines heuristiques)
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

    # ---------------------------------------------------------------------
    # Triggers
    # ---------------------------------------------------------------------
    def on_manual_invoke(self):
        """
        Trigger manuel : l'utilisateur clique sur le bouton flottant.
        """
        if self.logger:
            self.logger.log("invoke_help", tool="ASSISTANT")
        self._try_suggest(trigger="manual", created_item=None)

    def on_item_created(self, item):
        """
        Trigger auto : quand l'utilisateur termine la création d'un item.
        Ne fait rien si l'auto est désactivé.
        """
        if not self.auto_enabled:
            return
        self._try_suggest(trigger="auto", created_item=item)

    def _log_suggest_event(
        self, event_type: str, trigger: str, sid: str, decision_ms: int | None = None
    ):
        if not self.logger:
            return
        extra = f";ms={decision_ms}" if decision_ms is not None else ""
        self.logger.log(
            event_type, tool="ASSISTANT", notes=f"trigger={trigger};sid={sid}{extra}"
        )

    # ---------------------------------------------------------------------
    # Flux principal de suggestion
    # ---------------------------------------------------------------------
    def _try_suggest(self, trigger: str, created_item=None):
        """
        1) Construire le contexte
        2) Demander au wizard une proposition
        3) Si proposition :
           - créer le ghost
           - afficher dialog
           - commit si accept, sinon rollback
        4) Si pas de proposition :
           - en auto : rien
           - en manuel : info "pas de suggestion"
        """
        ctx = self._build_context(trigger, created_item=created_item)
        t0 = time.time()

        proposal = wizard.propose_suggestion(ctx)

        # ---------------------------------------------------------------
        # Cas "pas de suggestion"
        # ---------------------------------------------------------------
        if proposal is None:
            if self.logger:
                self.logger.log("ai_output", tool="ASSISTANT", notes=f"none:{trigger}")

            # En manuel, on informe l'utilisateur
            if trigger == "manual":
                dlg = SuggestionDialog(
                    title="Pas de suggestion",
                    uncertainty_pct=0,
                    explanation=["Aucune suggestion pertinente pour le moment."],
                    what_to_do="Ajoutez une forme cible, ou réessayez plus tard.",
                )
                dlg.exec()

            return

        # ---------------------------------------------------------------
        # On a une proposition : log "shown"
        # ---------------------------------------------------------------
        if self.logger:
            sid = proposal.get("suggestion_id", "unknown")

            # Uniquement pour l’auto
            if trigger == "auto":
                self._log_suggest_event("autosuggest_shown", trigger=trigger, sid=sid)

        # Important : si un ghost précédent traîne, on le retire
        self._clear_ghost()

        # ---------------------------------------------------------------
        # Création du ghost
        # ---------------------------------------------------------------
        ghost = proposal["suggestion"].create_items(self.scene)

        # Ajout temporaire en "grisé" :
        # - opacity réduite => aspect ghost
        # - disabled + flags off => pas d'interaction utilisateur
        for it in ghost:
            it.setOpacity(0.35)
            it.setEnabled(False)
            it.setFlag(it.GraphicsItemFlag.ItemIsSelectable, False)
            it.setFlag(it.GraphicsItemFlag.ItemIsMovable, False)
            self.scene.addItem(it)

        self._ghost_items = ghost

        # ---------------------------------------------------------------
        # Préparation + affichage de la fenêtre de suggestion
        # ---------------------------------------------------------------
        dlg = SuggestionDialog(
            title=proposal["suggestion"].label,
            uncertainty_pct=proposal["uncertainty_pct"],
            explanation=proposal["explanation"],
            what_to_do=proposal["what_to_do"],
            preview_pixmap=self._load_preview_pixmap(proposal["suggestion"]),
        )

        # Décision par défaut : None (puis sera "cancel" si fermeture sans choix)
        choice = None

        # On protège le flux : si le dialog se ferme de façon inattendue ou si une
        # exception survient, le `finally` retire le ghost (sauf si accepté).
        try:
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

                if choice == "accept":
                    if trigger == "auto":
                        self._log_suggest_event(
                            "autosuggest_accept",
                            trigger=trigger,
                            sid=sid,
                            decision_ms=decision_ms,
                        )
                    else:
                        self._log_suggest_event(
                            "assistant_accept",
                            trigger=trigger,
                            sid=sid,
                            decision_ms=decision_ms,
                        )
                else:
                    # On regroupe ignore / override / cancel comme "reject" pour l’analyse
                    if trigger == "auto":
                        self._log_suggest_event(
                            "autosuggest_reject",
                            trigger=trigger,
                            sid=sid,
                            decision_ms=decision_ms,
                        )
                    else:
                        self._log_suggest_event(
                            "assistant_reject",
                            trigger=trigger,
                            sid=sid,
                            decision_ms=decision_ms,
                        )

            # -----------------------------------------------------------
            # Si l'utilisateur accepte -> commit (items deviennent "réels")
            # -----------------------------------------------------------
            if choice == "accept":
                # On rend undoable l'ajout :
                # - les items sont déjà dans la scène => already_in_scene=True
                # - macro => un seul Ctrl+Z pour tout le pack
                self.scene.undo_stack.beginMacro(
                    f"Assistant: {proposal.get('suggestion_id', 'suggestion')}"
                )

                for it in self._ghost_items:
                    # Retire l'effet ghost
                    it.setOpacity(1.0)
                    it.setEnabled(True)
                    it.setFlag(it.GraphicsItemFlag.ItemIsSelectable, True)
                    it.setFlag(it.GraphicsItemFlag.ItemIsMovable, True)

                    # Ajout à la pile undo (l'item est déjà dans la scène)
                    self.scene.undo_stack.push(
                        AddItemCommand(
                            self.scene,
                            it,
                            text="Assistant suggestion",
                            already_in_scene=True,
                        )
                    )

                self.scene.undo_stack.endMacro()

                # On vide la liste : ces items ne sont plus "ghost"
                self._ghost_items = []

                # En auto : si l'utilisateur accepte, on ne supprime rien
                return

            # -----------------------------------------------------------
            # Si l'utilisateur n'applique pas :
            # - en auto : on supprime la répétition de cette suggestion (session)
            # - et on laisse le `finally` retirer le ghost
            # -----------------------------------------------------------
            if choice in ("ignore", "override", "cancel"):
                if trigger == "auto":
                    sid = proposal.get("suggestion_id")
                    if sid:
                        self._auto_suppressed.add(sid)
                        if self.logger:
                            self.logger.log(
                                "assistant_suppress", tool="ASSISTANT", notes=f"{sid}"
                            )

                # Pas de commit : le `finally` va retirer le ghost
                return

            # Si jamais d'autres choix apparaissent dans le futur :
            # on ne commite pas par défaut, donc le `finally` supprimera le ghost.

        finally:
            # -----------------------------------------------------------
            # Nettoyage garanti :
            # - si non accepté, on retire le ghost
            # - si accepté, _ghost_items a été vidé, donc _clear_ghost ne fait rien
            # -----------------------------------------------------------
            if choice != "accept":
                self._clear_ghost()

    # ---------------------------------------------------------------------
    # Préviews (images) : chargement optionnel
    # ---------------------------------------------------------------------
    def _load_preview_pixmap(self, suggestion):
        """
        Charge un aperçu (image) si `suggestion.preview_path` existe.

        - preview_path est supposé être un chemin relatif à la racine du projet.
        - retourne un QPixmap ou None.
        """
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

    # ---------------------------------------------------------------------
    # Gestion du ghost
    # ---------------------------------------------------------------------
    def _clear_ghost(self):
        """
        Retire tous les items actuellement en ghost de la scène.

        Points de robustesse :
        - on vérifie que l'item est encore dans une scène
        - on protège contre RuntimeError (objet Qt détruit)
        """
        if not getattr(self, "_ghost_items", None):
            self._ghost_items = []
            return

        for it in self._ghost_items:
            try:
                if it is not None and it.scene() is not None:
                    it.scene().removeItem(it)
            except RuntimeError:
                # L'item Qt a déjà été détruit ou la scène n'est plus valide
                pass

        self._ghost_items = []
