"""Constrain hidden page hints; wrap controls without resizing the user's window."""

from PySide6.QtCore import QSize
from PySide6.QtWidgets import (
    QStackedWidget,
    QWidget,
    QHBoxLayout,
    QBoxLayout,
    QSizePolicy,
    QCheckBox,
)


class ResponsiveStack(QStackedWidget):
    def minimumSizeHint(self):
        return QSize(0, 0)

    def sizeHint(self):
        return QSize(380, 400)


class SettingRow(QWidget):
    def __init__(self, boolean=False):
        super().__init__()
        self.boolean = boolean
        self.setMinimumWidth(0)
        self.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        layout = self.layout()
        if layout:
            direction = (
                QBoxLayout.LeftToRight
                if self.boolean or self.width() >= 600
                else QBoxLayout.TopToBottom
            )
            if layout.direction() != direction:
                layout.setDirection(direction)


class ToolGroup(QWidget):
    def __init__(self, buttons):
        super().__init__()
        from PySide6.QtWidgets import QGridLayout

        self.buttons = buttons
        self.columns = 0
        self.grid = QGridLayout(self)
        self.grid.setContentsMargins(0, 0, 0, 0)
        self.grid.setSpacing(8)
        self.setMinimumWidth(0)
        self.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        self.arrange(1)

    def arrange(self, columns):
        if columns == self.columns:
            return
        self.columns = columns
        for button in self.buttons:
            self.grid.removeWidget(button)
        for n, button in enumerate(self.buttons):
            button.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
            button.setMinimumWidth(0)
            self.grid.addWidget(button, n // columns, n % columns)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.arrange(1 if self.width() < 560 else 2)


class ToggleSwitch(QCheckBox):
    """Native checkable semantics with a compact, legible switch track."""

    def __init__(self):
        super().__init__()
        from PySide6.QtCore import Qt

        self.setCursor(Qt.PointingHandCursor)
        self.setFixedSize(48, 26)
        from PySide6.QtCore import QVariantAnimation,QEasingCurve
        self.position=0.;self.slide=QVariantAnimation(self);self.slide.setDuration(190);self.slide.setEasingCurve(QEasingCurve.OutBack)
        self.slide.valueChanged.connect(self.slide_changed)
        self.toggled.connect(self.slide_to)

    def slide_changed(self,value):
        self.position=float(value);self.update()

    def slide_to(self,checked):
        from .interactions import allowed
        self.slide.stop()
        if not self.isVisible() or not allowed(self.window()):self.position=float(checked);self.update();return
        self.slide.setStartValue(self.position);self.slide.setEndValue(float(checked));self.slide.start()

    def hitButton(self, pos):
        return self.rect().contains(pos)

    def paintEvent(self, event):
        from PySide6.QtGui import QPainter, QColor, QPen
        from PySide6.QtCore import Qt, QRectF

        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        x = (self.width() - 40) / 2
        color = "#4F8CFF" if self.isChecked() else "#66758B"
        if self.slide.state().name=='Running':
            a,b=QColor("#66758B"),QColor("#4F8CFF");t=max(0,min(1,self.position))
            color=QColor(round(a.red()+(b.red()-a.red())*t),round(a.green()+(b.green()-a.green())*t),round(a.blue()+(b.blue()-a.blue())*t))
        if self.isDown():
            color = "#325CC2" if self.isChecked() else "#4F668C"
        p.setOpacity(1 if self.isEnabled() else 0.4)
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(color))
        p.drawRoundedRect(QRectF(x, 3, 40, 20), 10, 10)
        p.setBrush(QColor("white"))
        p.drawEllipse(QRectF(x + 2 + 20*max(-.06,min(1.06,self.position)), 5, 16, 16))
        if self.hasFocus():
            p.setBrush(Qt.NoBrush)
            p.setPen(QPen(QColor("#8FB2FF"), 1))
            p.drawRoundedRect(QRectF(x - 3, 0, 46, 26), 12, 12)
