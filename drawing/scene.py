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

import json  # Sérialisation/désérialisation des items pour copy/paste via le clipboard


# Widgets/Items Qt utilisés par la scène
from PySide6.QtWidgets import (
    QGraphicsScene,  # Scène “modèle” : contient les items
    QGraphicsPathItem,  # Item pour le dessin libre (stylo) via QPainterPath
    QGraphicsLineItem,  # Item pour un segment
    QGraphicsRectItem,  # Item pour un rectangle
    QGraphicsEllipseItem,  # Item pour une ellipse
    QApplication,  # Accès au clipboard (copy/paste)
)

# Outils graphiques + pile undo/redo
from PySide6.QtGui import (
    QPainterPath,  # Représentation vectorielle d’un trait libre
    QPen,  # Style de contour (couleur, épaisseur, etc.)
    QColor,  # Couleurs (hex, RGB...)
    QBrush,  # Style de remplissage (fill) des formes
    QUndoStack,  # Pile de commandes pour Annuler/Rétablir (Undo/Redo)
)

# Types géométriques
from PySide6.QtCore import (
    QRectF,  # Rectangle flottant (coordonnées en float)
    QLineF,  # Segment flottant
    QPointF,  # Point flottant
    Signal,
)

# Enum métier des outils (SELECT, PEN, ERASER, LINE, RECT, ELLIPSE, ...)
from drawing.tools import Tool

# Commandes “undoables” : ajout, suppression, déplacement
from drawing.commands import AddItemCommand, RemoveItemCommand, MoveItemsCommand


class DrawingScene(QGraphicsScene):
    item_created = Signal(object)  # émettra le QGraphicsItem créé

    def __init__(self, logger=None):
        """
        Parameters
        ----------
        logger : EventLogger | None
            Logger utilisé pour enregistrer les interactions utilisateur.
            (Peut être None si on veut désactiver la journalisation.)
        """
        super().__init__()

        # Dimensions “fixes” de la zone de dessin (coordonnées de scène)
        width = 1280
        height = 720
        self.setSceneRect(QRectF(0, 0, width, height))

        # Pile des commandes (Annuler/Rétablir).
        # On “push” des QUndoCommand dès qu’une action modifie réellement la scène.
        self.undo_stack = QUndoStack(self)

        # Sauvegarde des positions des items sélectionnés au moment du mousePress (SELECT),
        # pour pouvoir construire une commande MoveItemsCommand au mouseRelease.
        self._move_old_positions = None

        # Outil courant (par défaut : SELECT)
        self._tool = Tool.SELECT

        # Logger HAII (si fourni)
        self.logger = logger

        # Couleur de contour (stroke) et de remplissage (fill) courantes
        self._stroke_color = QColor("#000000")  # noir par défaut
        self._fill_color = None  # None = pas de remplissage (NoBrush)

        # ---- État interne pour Tool.PEN (dessin libre) ----

        # Path en cours de construction (QPainterPath)
        self._current_path = None

        # Item graphique associé au path en cours (QGraphicsPathItem)
        self._current_item = None

        # Nombre de points ajoutés dans le path (utile pour logs)
        self._points_count = 0

        # ---- État interne pour Tool.SELECT ----

        # Item sous la souris au mousePress (peut être None)
        self._press_item = None

        # Position de la souris au mousePress (QPointF)
        self._press_pos = None

        # ---- État interne pour LINE/RECT/ELLIPSE ----

        # Point de départ (mousePress) de la forme en création
        self._shape_start = None  # QPointF (scene coords)

        # Item graphique temporaire (preview) de la forme en création
        self._shape_item = None  # QGraphicsLineItem / RectItem / EllipseItem

    # ----------------------------
    # Utils (clipboard, styles, helpers)
    # ----------------------------

    def _serialize_item(self, item):
        """
        Transforme un QGraphicsItem en dict JSON-friendly.
        Utilisé pour copier/coller des items via le clipboard.

        Limite assumée :
        - On supporte seulement Line/Rect/Ellipse/Path (traits libres).
        - Pour le path : on stocke les éléments (MoveTo/LineTo/...) du QPainterPath.
        """
        # Récupère le style de contour si l'item expose pen()
        pen = item.pen() if hasattr(item, "pen") else None
        stroke = pen.color().name() if pen else "#000000"  # couleur de contour en hex
        width = pen.width() if pen else 1  # épaisseur du contour

        # Récupère le fill si l'item expose brush()
        fill = "none"
        if hasattr(item, "brush"):
            b = item.brush()
            if b.style() != 0:  # Qt.NoBrush == 0 => pas de remplissage
                fill = b.color().name()

        # Données communes à tous les types d'items
        base = {
            "type": type(item).__name__,  # ex "QGraphicsRectItem"
            "pos": [item.pos().x(), item.pos().y()],  # position (translation) de l'item
            "stroke": stroke,  # couleur du contour
            "stroke_width": width,  # épaisseur du contour
            "fill": fill,  # couleur de remplissage ou "none"
        }

        # Cas selon le type concret d'item
        if isinstance(item, QGraphicsLineItem):
            # On stocke les coordonnées du segment
            line = item.line()
            base["line"] = [line.x1(), line.y1(), line.x2(), line.y2()]

        elif isinstance(item, QGraphicsRectItem):
            # On stocke la bounding box du rectangle
            r = item.rect()
            base["rect"] = [r.x(), r.y(), r.width(), r.height()]

        elif isinstance(item, QGraphicsEllipseItem):
            # Une ellipse est définie par son rectangle englobant (bounding box)
            r = item.rect()
            base["ellipse"] = [r.x(), r.y(), r.width(), r.height()]

        elif isinstance(item, QGraphicsPathItem):
            # Pour un prototype : on stocke les éléments du path.
            # (Suffisant si ton stylo fait surtout des segments.)
            path = item.path()
            elems = []
            for i in range(path.elementCount()):
                e = path.elementAt(i)
                # e.type : MoveTo/LineTo/CurveTo... (on le garde pour info/debug)
                elems.append([e.x, e.y, int(e.type)])
            base["path_elems"] = elems

        else:
            # Type non supporté : on ne peut pas copier/coller cet item
            return None

        return base

    def _make_pen(self, width=2):
        """
        Construit un QPen à partir de la couleur de contour courante (stroke)
        et d'une épaisseur donnée.
        """
        pen = QPen(self._stroke_color)
        pen.setWidth(width)
        return pen

    def _enable_interaction_flags(self, item):
        """
        Rend l'item sélectionnable et déplaçable en mode SELECT.
        (C’est Qt qui gère le drag une fois ces flags activés.)
        """
        item.setFlag(item.GraphicsItemFlag.ItemIsSelectable, True)
        item.setFlag(item.GraphicsItemFlag.ItemIsMovable, True)

    def _item_at_scene_pos(self, scene_pos):
        """
        Retourne l'item sous une position en coordonnées de scène.

        Pourquoi view.transform() ?
        QGraphicsScene.itemAt() nécessite un QTransform (celui de la QGraphicsView)
        pour interpréter correctement les coordonnées écran/scene.
        """
        if not self.views():
            return None
        view = self.views()[0]
        return self.itemAt(scene_pos, view.transform())

    def _apply_fill(self, item):
        """
        Applique le remplissage (fill) courant à l'item.
        Utile surtout pour RECT/ELLIPSE (le fill n'a pas d'intérêt sur LINE/Path).
        """
        if self._fill_color is None:
            # Brush “vide” => pas de remplissage
            item.setBrush(QBrush())
        else:
            item.setBrush(QBrush(self._fill_color))

    def _make_pen_from(self, stroke_hex, width):
        """
        Reconstruit un QPen depuis des données sérialisées (clipboard).
        """
        pen = QPen(QColor(stroke_hex))
        pen.setWidth(int(width))
        return pen

    def _apply_fill_from(self, item, fill_hex):
        """
        Reconstruit un brush depuis des données sérialisées (clipboard).
        """
        if fill_hex == "none":
            item.setBrush(QBrush())
        else:
            item.setBrush(QBrush(QColor(fill_hex)))

    def _deserialize_item(self, data):
        """
        Reconstruit un QGraphicsItem depuis un dict (issu du clipboard).
        Cette méthode est l'inverse logique de _serialize_item().
        """
        t = data["type"]

        # Position globale de l'item (translation)
        pos = QPointF(data["pos"][0], data["pos"][1])

        # Styles
        pen = self._make_pen_from(
            data.get("stroke", "#000000"),
            data.get("stroke_width", 1),
        )
        fill = data.get("fill", "none")

        item = None

        # Reconstruction selon le type
        if t == "QGraphicsLineItem":
            x1, y1, x2, y2 = data["line"]
            item = QGraphicsLineItem(QLineF(x1, y1, x2, y2))
            item.setPen(pen)

        elif t == "QGraphicsRectItem":
            x, y, w, h = data["rect"]
            item = QGraphicsRectItem(QRectF(x, y, w, h))
            item.setPen(pen)
            self._apply_fill_from(item, fill)

        elif t == "QGraphicsEllipseItem":
            x, y, w, h = data["ellipse"]
            item = QGraphicsEllipseItem(QRectF(x, y, w, h))
            item.setPen(pen)
            self._apply_fill_from(item, fill)

        elif t == "QGraphicsPathItem":
            elems = data["path_elems"]
            if not elems:
                return None

            # Reconstruit un path en faisant un moveTo puis une suite de lineTo.
            # (On ignore le etype ici : OK pour un prototype basé sur segments.)
            path = QPainterPath()
            x0, y0, _ = elems[0]
            path.moveTo(x0, y0)
            for x, y, etype in elems[1:]:
                path.lineTo(x, y)

            item = QGraphicsPathItem(path)
            item.setPen(pen)

        # Type inconnu/non supporté
        if item is None:
            return None

        # Rend l'item manipulable en mode SELECT
        self._enable_interaction_flags(item)

        # Applique la position globale
        item.setPos(pos)
        return item

    def _finalize_created_item(self, item):
        """À appeler quand un item 'définitif' est créé par l'utilisateur."""
        self.item_created.emit(item)

    # ---------
    # API publique (appelée par l'UI)
    # ---------

    def set_tool(self, tool: Tool):
        """Change l'outil courant (appelé depuis la toolbar)."""
        self._tool = tool
        if self.logger:
            self.logger.log(event_type="tool_change", tool=tool.name)

    def tool(self) -> Tool:
        """Retourne l'outil courant."""
        return self._tool

    def set_stroke_color(self, color: QColor):
        """Change la couleur de contour courante (stroke)."""
        self._stroke_color = QColor(color)
        if self.logger:
            self.logger.log(
                event_type="stroke_color_change",
                stroke_color=self._stroke_color.name(),
            )

    def stroke_color(self) -> QColor:
        """Retourne une copie de la couleur de contour courante."""
        return QColor(self._stroke_color)

    def set_fill_color(self, color: QColor | None):
        """
        Change la couleur de remplissage (fill).
        - color=None => pas de remplissage
        - color=QColor => remplissage avec cette couleur
        """
        self._fill_color = QColor(color) if color is not None else None
        if self.logger:
            self.logger.log(
                event_type="fill_color_change",
                fill_color=(self._fill_color.name() if self._fill_color else "none"),
            )

    def fill_color(self):
        """Retourne la couleur de fill (ou None si pas de remplissage)."""
        return QColor(self._fill_color) if self._fill_color is not None else None

    def history(self) -> QUndoStack:
        """Expose la pile undo/redo au EditorWindow (pour créer les QAction Undo/Redo)."""
        return self.undo_stack

    # ----------------------------
    # Clipboard : copier/couper/coller/dupliquer
    # ----------------------------

    def copy_selection(self):
        """
        Copie la sélection dans le clipboard sous forme JSON.
        (On choisit du texte JSON pour rester simple et portable.)
        """
        items = self.selectedItems()

        # Sérialise uniquement les types supportés (les None sont filtrés)
        payload = [self._serialize_item(it) for it in items]
        payload = [p for p in payload if p is not None]

        text = json.dumps({"items": payload})
        QApplication.clipboard().setText(text)

        if self.logger:
            self.logger.log(
                event_type="copy", tool=self._tool.name, notes=f"n={len(payload)}"
            )

    def cut_selection(self):
        """
        Couper = copier puis supprimer la sélection via des commandes undoables.
        """
        self.copy_selection()

        # Supprime chaque item via une commande RemoveItemCommand => undo possible
        for it in list(self.selectedItems()):
            self.undo_stack.push(RemoveItemCommand(self, it, text="Cut item"))

        if self.logger:
            self.logger.log(event_type="cut", tool=self._tool.name)

    def paste(self, offset=None):
        """
        Colle les items du clipboard.

        offset :
        - None => offset par défaut (10, 10) pour “décaler” la copie (UX classique).
        - QPointF => décalage personnalisé.

        Note importante :
        On utilise moveBy(dx, dy) plutôt que it.pos() + offset, car certaines versions
        de PySide6 ont des soucis avec operator+ sur QPointF.
        """
        if offset is None:
            offset = QPointF(10, 10)

        txt = QApplication.clipboard().text()
        try:
            data = json.loads(txt)
            items_data = data.get("items", [])
        except Exception:
            # Clipboard non compatible / pas du JSON attendu
            return

        new_items = []
        for d in items_data:
            it = self._deserialize_item(d)
            if it is None:
                continue

            # Décale l'item collé (évite QPointF + QPointF)
            it.moveBy(offset.x(), offset.y())

            # Ajoute l'item à la scène immédiatement
            self.addItem(it)

            # Enregistre l'ajout dans la pile undo (already_in_scene=True car déjà ajouté)
            self.undo_stack.push(
                AddItemCommand(self, it, text="Paste item", already_in_scene=True)
            )
            new_items.append(it)

        # UX : après collage, sélectionner les nouveaux items
        self.clearSelection()
        for it in new_items:
            it.setSelected(True)

        if self.logger:
            self.logger.log(
                event_type="paste", tool=self._tool.name, notes=f"n={len(new_items)}"
            )

    def duplicate_selection(self):
        """
        Dupliquer = recréer une copie des items sélectionnés, avec un petit offset,
        sans passer par le clipboard OS.
        """
        items = self.selectedItems()
        payload = [self._serialize_item(it) for it in items]
        payload = [p for p in payload if p is not None]
        if not payload:
            return

        for d in payload:
            it = self._deserialize_item(d)
            if it is None:
                continue

            # Décale la copie pour la distinguer visuellement
            it.moveBy(10, 10)

            self.addItem(it)
            self.undo_stack.push(
                AddItemCommand(self, it, text="Duplicate item", already_in_scene=True)
            )

        if self.logger:
            self.logger.log(
                event_type="duplicate", tool=self._tool.name, notes=f"n={len(payload)}"
            )

    # ------------------------------------------------------------------
    # Mouse events (interaction directe)
    # ------------------------------------------------------------------

    def mousePressEvent(self, event):
        """
        Début d'interaction souris.

        Selon l'outil courant :
        - ERASER : supprime l'item sous la souris via une commande undoable
        - PEN : crée un QPainterPath et un QGraphicsPathItem (preview)
        - LINE/RECT/ELLIPSE : crée l'item de forme (preview)
        - SELECT : laisse Qt gérer la sélection et capture l'état pour un éventuel move
        """
        p = event.scenePos()

        # ---------------- ERASER ----------------
        if self._tool == Tool.ERASER and event.button():
            item = self._item_at_scene_pos(p)
            if item is not None:
                # Suppression undoable
                self.undo_stack.push(RemoveItemCommand(self, item, text="Erase item"))
                if self.logger:
                    self.logger.log(
                        event_type="erase", tool="ERASER", item_type=type(item).__name__
                    )
                event.accept()
                return

            # Rien à gommer : laisse Qt propager (pas grave)
            super().mousePressEvent(event)
            return

        # ---------------- PEN ----------------
        if self._tool == Tool.PEN and event.button():
            # Initialise un path au point de départ
            self._current_path = QPainterPath(p)
            self._points_count = 1

            # Item “preview” : ajouté immédiatement pour dessiner en temps réel
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
            self._shape_item = QGraphicsLineItem(
                QLineF(p, p)
            )  # segment dégénéré au départ
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
            self._shape_item = QGraphicsRectItem(QRectF(p, p))  # rect vide au départ
            self._shape_item.setPen(self._make_pen(width=2))
            self._apply_fill(self._shape_item)
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
            self._apply_fill(self._shape_item)
            self._enable_interaction_flags(self._shape_item)
            self.addItem(self._shape_item)

            if self.logger:
                self.logger.log(event_type="ellipse_start", tool="ELLIPSE")

            event.accept()
            return

        # ---------------- SELECT ----------------
        if self._tool == Tool.SELECT:
            # Mémorise ce qu'il y a sous la souris et la position du press
            self._press_item = self._item_at_scene_pos(p)
            self._press_pos = p

            # Laisse Qt gérer la sélection / focus / etc.
            super().mousePressEvent(event)

            # Capture la position des items sélectionnés *après* mise à jour de Qt.
            # Objectif : avoir un “avant” fiable pour construire MoveItemsCommand au release.
            self._move_old_positions = {it: it.pos() for it in self.selectedItems()}

            if self.logger:
                self.logger.log(
                    event_type="select_press",
                    tool="SELECT",
                    item_type=(
                        type(self._press_item).__name__ if self._press_item else "None"
                    ),
                )

    def mouseMoveEvent(self, event):
        """
        Mouvement de souris avec bouton pressé :
        - ERASER : gomme en continu (supprime des items au passage)
        - PEN : ajoute des segments au QPainterPath en cours
        - LINE/RECT/ELLIPSE : met à jour la forme preview
        - SELECT : Qt gère le déplacement (ItemIsMovable) si applicable
        """
        p = event.scenePos()

        # ---------------- ERASER (gomme “continue”) ----------------
        if self._tool == Tool.ERASER:
            item = self._item_at_scene_pos(p)
            if item is not None:
                self.undo_stack.push(RemoveItemCommand(self, item, text="Erase item"))
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
                # Segment entre le point de départ et la position courante
                self._shape_item.setLine(QLineF(self._shape_start, p))
            else:
                # Pour rect/ellipse : on utilise un QRectF normalisé (x<=, y<=)
                rect = QRectF(self._shape_start, p).normalized()
                self._shape_item.setRect(rect)

            event.accept()
            return

        # SELECT et autres : comportement Qt standard
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        """
        Fin d'interaction souris :
        - PEN : finalize + push AddItemCommand (undoable)
        - LINE/RECT/ELLIPSE : finalize + push AddItemCommand (undoable)
        - SELECT : si déplacement => push MoveItemsCommand (undoable)
        """
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

            # L'item est déjà dans la scène (preview), on “enregistre” l’action dans l’historique.
            self.undo_stack.push(
                AddItemCommand(
                    self, self._current_item, text="Pen stroke", already_in_scene=True
                )
            )

            # Signal pour le nouvel item créé
            self._finalize_created_item(self._current_item)

            # Reset état interne
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
            # Log de fin (utile pour debug/analytics)
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

            # Enregistre l’ajout de la forme dans l’historique (undoable)
            self.undo_stack.push(
                AddItemCommand(
                    self, self._shape_item, text="Shape stroke", already_in_scene=True
                )
            )

            # Signal pour le nouvel item créé
            self._finalize_created_item(self._shape_item)

            # Reset état interne shapes
            self._shape_start = None
            self._shape_item = None

            event.accept()
            return

        # ---------------- SELECT ----------------
        if self._tool == Tool.SELECT and self._press_pos is not None:
            # Détection d'un déplacement significatif (évite d'enregistrer des moves “fantômes”)
            delta = p - self._press_pos
            moved = abs(delta.x()) + abs(delta.y()) > 2.0

            if moved:
                if self.logger:
                    self.logger.log(event_type="item_moved", tool="SELECT")

                selected = self.selectedItems()

                # Si on avait bien capturé le “avant”
                if self._move_old_positions:
                    new_positions = {
                        it: it.pos()
                        for it in selected
                        if it in self._move_old_positions
                    }

                    # Vérifie que quelque chose a réellement bougé
                    changed = any(
                        new_positions[it] != self._move_old_positions[it]
                        for it in new_positions
                    )

                    if changed:
                        # Enregistre le déplacement comme commande undoable
                        self.undo_stack.push(
                            MoveItemsCommand(
                                items=list(new_positions.keys()),
                                old_positions=self._move_old_positions,
                                new_positions=new_positions,
                                text="Move selection",
                            )
                        )

            # Reset état interne SELECT
            self._move_old_positions = None
            self._press_item = None
            self._press_pos = None

        # Toujours laisser Qt finaliser le comportement standard
        super().mouseReleaseEvent(event)
