"""Home adapts to available height; it never creates a scrolling viewport."""

from PySide6.QtWidgets import QWidget


class Dashboard(QWidget):
    def __init__(self, owner):
        super().__init__()
        self.owner = owner

    def resizeEvent(self, event):
        super().resizeEvent(event)
        owner = self.owner
        compact = self.height() < 580
        diameter = 120 if self.height() < 530 else 148 if compact else 172
        owner.power.setFixedSize(diameter, diameter)
        for tile in owner.service_buttons.values():
            tile.setFixedHeight(40 if compact else 48)
        owner.services_note.setVisible(not compact)
        self.layout().setSpacing(5 if compact else 9)
