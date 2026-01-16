from PySide6.QtGui import QUndoCommand
from PySide6.QtWidgets import QGraphicsItem, QGraphicsScene


class AddItemCommand(QUndoCommand):
    def __init__(
        self,
        scene: QGraphicsScene,
        item: QGraphicsItem,
        text="Add item",
        already_in_scene=True,
    ):
        super().__init__(text)
        self.scene = scene
        self.item = item
        self._first_redo = already_in_scene  # l'item est déjà visible (preview)

    def redo(self):
        # Premier redo = no-op si l'item est déjà dans la scène
        if self._first_redo:
            self._first_redo = False
            return
        if self.item.scene() is None:
            self.scene.addItem(self.item)

    def undo(self):
        if self.item.scene() is not None:
            self.scene.removeItem(self.item)


class RemoveItemCommand(QUndoCommand):
    def __init__(self, scene: QGraphicsScene, item: QGraphicsItem, text="Remove item"):
        super().__init__(text)
        self.scene = scene
        self.item = item
        self._pos = item.pos()  # utile si tu veux conserver des infos

    def redo(self):
        if self.item.scene() is not None:
            self.scene.removeItem(self.item)

    def undo(self):
        if self.item.scene() is None:
            self.scene.addItem(self.item)
            self.item.setPos(self._pos)


class MoveItemsCommand(QUndoCommand):
    """
    Déplacement d'un ensemble d'items (utile quand l'utilisateur bouge une sélection).
    """

    def __init__(self, items, old_positions, new_positions, text="Move items"):
        super().__init__(text)
        self.items = list(items)
        self.old_positions = old_positions  # dict[item] = QPointF
        self.new_positions = new_positions  # dict[item] = QPointF

    def redo(self):
        for it in self.items:
            it.setPos(self.new_positions[it])

    def undo(self):
        for it in self.items:
            it.setPos(self.old_positions[it])
