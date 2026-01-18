import json
from pathlib import Path

from PySide6.QtWidgets import (
    QMainWindow,
    QToolBar,
    QGraphicsView,
    QMessageBox,
    QInputDialog,
    QColorDialog,
    QToolButton,
    QLabel,
)
from PySide6.QtGui import QAction, QColor
from PySide6.QtCore import QPointF, Qt

from drawing.scene import DrawingScene
from drawing.tools import Tool
from drawing.serialization import serialize_item, deserialize_item
from drawing.commands import AddItemCommand


class TemplateBuilderWindow(QMainWindow):
    """
    Fenêtre dev-only :
    - tu dessines des items (mêmes outils que l'éditeur)
    - tu exportes en JSON sérialisé dans assistant/templates_dev/
    - ensuite generation_catalog.py peut les charger et désérialiser
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Template Builder (dev)")
        self.resize(900, 600)

        self.scene = DrawingScene(logger=None)
        self.view = QGraphicsView(self.scene)
        self.setCentralWidget(self.view)

        self._build_toolbar()

    def _build_toolbar(self):
        tb = QToolBar("Template Tools", self)
        self.addToolBar(tb)

        def set_tool(tool: Tool):
            self.scene.set_tool(tool)
            if tool == Tool.SELECT:
                self.view.setDragMode(QGraphicsView.RubberBandDrag)
            else:
                self.view.setDragMode(QGraphicsView.NoDrag)

        act_select = QAction("Sélection", self)
        act_select.triggered.connect(lambda: set_tool(Tool.SELECT))
        tb.addAction(act_select)

        act_pen = QAction("Stylo", self)
        act_pen.triggered.connect(lambda: set_tool(Tool.PEN))
        tb.addAction(act_pen)

        act_line = QAction("Trait", self)
        act_line.triggered.connect(lambda: set_tool(Tool.LINE))
        tb.addAction(act_line)

        act_rect = QAction("Rectangle", self)
        act_rect.triggered.connect(lambda: set_tool(Tool.RECT))
        tb.addAction(act_rect)

        act_ellipse = QAction("Ellipse", self)
        act_ellipse.triggered.connect(lambda: set_tool(Tool.ELLIPSE))
        tb.addAction(act_ellipse)

        tb.addSeparator()

        act_undo = QAction("Annuler", self)
        act_undo.triggered.connect(self.scene.undo_stack.undo)
        tb.addAction(act_undo)

        act_redo = QAction("Rétablir", self)
        act_redo.triggered.connect(self.scene.undo_stack.redo)
        tb.addAction(act_redo)

        tb.addSeparator()

        act_duplicate = QAction("Dupliquer", self)
        act_duplicate.setToolTip("Dupliquer la sélection")
        act_duplicate.triggered.connect(self._duplicate_selection)
        act_duplicate.setShortcut("Ctrl+D")
        tb.addAction(act_duplicate)

        tb.addSeparator()

        # Couleurs prédéfinies (tu peux adapter)
        palette = [
            "#000000",
            "#FFFFFF",
            "#808080",
            "#FF0000",
            "#00FF00",
            "#0000FF",
            "#FFFF00",
            "#FF00FF",
            "#00FFFF",
            "#FFA500",
            "#8A2BE2",
            "#A52A2A",
        ]

        # ----- Stroke (contour) -----
        tb.addWidget(QLabel("Contour:", self))
        for hx in palette:
            tb.addWidget(
                self._make_color_swatch(
                    hx, lambda _=False, h=hx: self.scene.set_stroke_color(QColor(h))
                )
            )

        btn_more_stroke = QToolButton(self)
        btn_more_stroke.setText("…")
        btn_more_stroke.setToolTip("Choisir une couleur de contour")
        btn_more_stroke.clicked.connect(self._choose_custom_stroke)
        tb.addWidget(btn_more_stroke)

        tb.addSeparator()

        # ----- Fill (remplissage) -----
        tb.addWidget(QLabel("Remplissage:", self))

        btn_no_fill = QToolButton(self)
        btn_no_fill.setText("Aucun")
        btn_no_fill.setToolTip("Pas de remplissage")
        btn_no_fill.clicked.connect(lambda: self.scene.set_fill_color(None))
        tb.addWidget(btn_no_fill)

        for hx in palette:
            tb.addWidget(
                self._make_color_swatch(
                    hx, lambda _=False, h=hx: self.scene.set_fill_color(QColor(h))
                )
            )

        btn_more_fill = QToolButton(self)
        btn_more_fill.setText("…")
        btn_more_fill.setToolTip("Choisir une couleur de remplissage")
        btn_more_fill.clicked.connect(self._choose_custom_fill)
        tb.addWidget(btn_more_fill)

        tb.addSeparator()

        act_export_sel = QAction("Exporter sélection", self)
        act_export_sel.triggered.connect(lambda: self._export(selection_only=True))
        tb.addAction(act_export_sel)

        act_export_all = QAction("Exporter tout", self)
        act_export_all.triggered.connect(lambda: self._export(selection_only=False))
        tb.addAction(act_export_all)

    def _duplicate_selection(self):
        """
        Duplique les items sélectionnés :
        - sérialisation -> désérialisation
        - léger décalage
        - undo/redo supporté
        """
        selected = set(self.scene.selectedItems())
        if not selected:
            return

        # Ordre bas -> haut (pour préserver l'empilement)
        ordered = self.scene.items(Qt.SortOrder.AscendingOrder)
        items_to_dup = [it for it in ordered if it in selected]

        OFFSET = QPointF(20, 20)

        self.scene.undo_stack.beginMacro("Duplicate items")
        new_items = []

        for it in items_to_dup:
            data = serialize_item(it)
            if data is None:
                continue
            new_it = deserialize_item(data)
            if new_it is None:
                continue

            # Décalage visuel
            new_it.setPos(it.pos() + OFFSET)

            self.scene.addItem(new_it)
            self.scene.undo_stack.push(
                AddItemCommand(
                    self.scene, new_it, text="Duplicate item", already_in_scene=True
                )
            )
            new_items.append(new_it)

        self.scene.undo_stack.endMacro()

        # UX : sélectionner les nouveaux items
        self.scene.clearSelection()
        for it in new_items:
            it.setSelected(True)

    def _make_color_swatch(self, hex_color: str, on_click):
        """
        Crée un petit bouton couleur (pastille) inséré dans une toolbar.
        """
        btn = QToolButton(self)
        btn.setFixedSize(18, 18)
        btn.setToolTip(hex_color)
        # Pastille simple via stylesheet (fiable, pas besoin d'icônes)
        btn.setStyleSheet(
            f"""
            QToolButton {{
                background-color: {hex_color};
                border: 1px solid #444;
                border-radius: 3px;
                margin: 1px;
            }}
            QToolButton:hover {{
                border: 2px solid #222;
            }}
            """
        )
        btn.clicked.connect(on_click)
        return btn

    def _choose_custom_stroke(self):
        c = QColorDialog.getColor(parent=self, title="Couleur du contour")
        if c.isValid():
            self.scene.set_stroke_color(c)

    def _choose_custom_fill(self):
        c = QColorDialog.getColor(parent=self, title="Couleur du remplissage")
        if c.isValid():
            self.scene.set_fill_color(c)

    def _export(self, selection_only: bool):
        if selection_only:
            selected = set(self.scene.selectedItems())
            if not selected:
                QMessageBox.information(self, "Export", "Aucun item sélectionné.")
                return
            # Ordre bas -> haut, filtré par sélection
            ordered = self.scene.items(Qt.SortOrder.AscendingOrder)
            items = [it for it in ordered if it in selected]
        else:
            # Ordre bas -> haut
            items = self.scene.items(Qt.SortOrder.AscendingOrder)

        if not items:
            QMessageBox.information(self, "Export", "Aucun item à exporter.")
            return

        category, ok = QInputDialog.getText(
            self, "Export", "Category (ex: Porte, Fenêtre, ...)"
        )
        if not ok or not category.strip():
            return

        item_id, ok = QInputDialog.getText(self, "Export", "Item id (ex: door_gothic)")
        if not ok or not item_id.strip():
            return

        ser = []
        for it in items:
            d = serialize_item(it)
            if d is not None:
                ser.append(d)

        if not ser:
            QMessageBox.warning(
                self, "Export", "Items non supportés : rien n'a été exporté."
            )
            return

        root = (
            Path(__file__).resolve().parents[1]
        )  # racine projet (si ui/ est au même niveau que assistant/)
        out_dir = root / "assistant" / "templates_dev"
        out_dir.mkdir(parents=True, exist_ok=True)

        out_path = out_dir / f"{category}__{item_id}.json"

        payload = {
            "meta": {"category": category, "item_id": item_id},
            "items": ser,
        }

        out_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        QMessageBox.information(self, "Export", f"Template exporté :\n{out_path}")
