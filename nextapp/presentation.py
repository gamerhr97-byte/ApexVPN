"""Lightweight painted glass-style surfaces and vector controls. No web view."""

import math
from PySide6.QtCore import Qt, QRectF, QPointF, QVariantAnimation, QEasingCurve
from PySide6.QtGui import (
    QColor,
    QPainter,
    QPen,
    QFont,
    QLinearGradient,
    QRadialGradient,
    QPainterPath,
)
from PySide6.QtWidgets import QWidget, QPushButton


class GlassSurface(QWidget):
    def __init__(self, owner):
        super().__init__()
        self.owner = owner

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        dark = self.owner.settings["theme"] in ("Dark", "Apex")
        gradient = QLinearGradient(0, 0, self.width(), self.height())
        apex=self.owner.settings["theme"]=="Apex"
        gradient.setColorAt(0, QColor("#090B10" if apex else "#192036" if dark else "#F5F7FB"))
        gradient.setColorAt(0.55, QColor("#120B11" if apex else "#131A2B" if dark else "#F5F7FB"))
        gradient.setColorAt(1, QColor("#280B12" if apex else "#211C32" if dark else "#F5F7FB"))
        p.setPen(Qt.NoPen)
        p.setBrush(gradient)
        p.drawRoundedRect(QRectF(self.rect()), 18, 18)
        # Decorative translucent spheres removed: they looked like screen blemishes.


class IconButton(QPushButton):
    def __init__(self, kind, owner, callback, title):
        super().__init__()
        self.kind = kind
        self.owner = owner
        self.setFixedSize(40, 40)
        self.setProperty("kind", "icon")
        self.setAccessibleName(title)
        self.setToolTip(title)
        self.setCursor(Qt.PointingHandCursor)
        self.clicked.connect(callback)

    def paintEvent(self, event):
        super().paintEvent(event)
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        color = QColor(
            "#E4EAF9" if self.owner.settings["theme"] in ("Dark", "Apex") else "#4A5670"
        )
        p.setPen(QPen(color, 1.65, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        if self.kind == "plus":
            p.drawLine(20, 12, 20, 28)
            p.drawLine(12, 20, 28, 20)
        elif self.kind == "back":
            p.drawLine(25, 12, 17, 20)
            p.drawLine(17, 20, 25, 28)
        elif self.kind == "gear":
            p.drawEllipse(QRectF(13, 13, 14, 14))
            p.drawEllipse(QRectF(17, 17, 6, 6))
            for i in range(8):
                a = i * math.pi / 4
                p.drawLine(
                    QPointF(20 + 8 * math.cos(a), 20 + 8 * math.sin(a)),
                    QPointF(20 + 11 * math.cos(a), 20 + 11 * math.sin(a)),
                )
        elif self.kind == "theme":
            p.drawEllipse(QRectF(13, 13, 14, 14))
            for i in range(8):
                a = i * math.pi / 4
                p.drawLine(
                    QPointF(20 + 10 * math.cos(a), 20 + 10 * math.sin(a)),
                    QPointF(20 + 13 * math.cos(a), 20 + 13 * math.sin(a)),
                )


def latency_color(ms):
    if ms is None:
        return "#4F8CFF"
    if ms < 150:
        return "#22C55E"
    if ms < 200:
        return "#4F8CFF"
    return "#EF4444"


def action_icon(kind, dark=False):
    from PySide6.QtGui import QPixmap, QIcon

    pix = QPixmap(24, 24)
    pix.fill(Qt.transparent)
    p = QPainter(pix)
    p.setRenderHint(QPainter.Antialiasing)
    p.setPen(
        QPen(
            QColor("#DDE7FA" if dark else "#526581"),
            1.7,
            Qt.SolidLine,
            Qt.RoundCap,
            Qt.RoundJoin,
        )
    )
    if kind == "clipboard":
        p.drawRoundedRect(QRectF(5, 5, 14, 16), 2, 2)
        p.drawRoundedRect(QRectF(9, 2, 6, 5), 1, 1)
        p.drawLine(9, 11, 16, 11)
        p.drawLine(9, 15, 15, 15)
    elif kind == "edit":
        p.drawLine(5, 18, 17, 6)
        p.drawLine(8, 21, 20, 9)
        p.drawLine(17, 6, 20, 9)
        p.drawLine(5, 18, 4, 22)
        p.drawLine(4, 22, 8, 21)
    elif kind == "qr":
        for x, y in ((3, 3), (15, 3), (3, 15)):
            p.drawRect(QRectF(x, y, 6, 6))
            p.drawRect(QRectF(x + 2, y + 2, 2, 2))
        p.drawLine(15, 15, 19, 15)
        p.drawLine(19, 15, 19, 21)
        p.drawLine(15, 18, 15, 21)
        p.drawLine(21, 19, 22, 19)
    elif kind == "link":
        p.drawRoundedRect(QRectF(2, 8, 12, 7), 3, 3)
        p.drawRoundedRect(QRectF(10, 8, 12, 7), 3, 3)
        p.drawLine(8, 11, 16, 11)
    p.end()
    return QIcon(pix)


class Power(QPushButton):
    def __init__(self, owner):
        super().__init__()
        self.owner = owner
        self.hover = 0.0
        self.phase = 0.0
        self.spinner = QVariantAnimation(self)
        self.spinner.setDuration(1300)
        self.spinner.setStartValue(0.0)
        self.spinner.setEndValue(360.0)
        self.spinner.setLoopCount(-1)
        self.spinner.valueChanged.connect(self._phase_value)
        self.animation = QVariantAnimation(self)
        self.animation.setDuration(150)
        self.animation.setEasingCurve(QEasingCurve.OutCubic)
        self.animation.valueChanged.connect(self._hover_value)
        self.setFixedSize(182, 182)
        self.setAccessibleName("Connect or disconnect")
        self.setCursor(Qt.PointingHandCursor)
        self.clicked.connect(owner.toggle_connection)

    def _phase_value(self, value):
        self.phase = float(value)
        self.update()

    def set_status(self, status):
        s = self.owner.settings
        allowed = (
            s.get("visual_effects", True)
            and not s.get("reduced_motion", True)
            and not s.get("lightweight", False)
            and not s.get("high_contrast", False)
        )
        if status == "Connecting" and allowed:
            if self.spinner.state() != QVariantAnimation.Running:
                self.spinner.start()
        else:
            self.spinner.stop()
            self.phase = 0.0
        self.update()

    def _hover_value(self, value):
        self.hover = float(value)
        self.update()

    def enterEvent(self, event):
        super().enterEvent(event)
        self.animate_hover(1.0)

    def leaveEvent(self, event):
        super().leaveEvent(event)
        self.animate_hover(0.0)

    def animate_hover(self, value):
        s = self.owner.settings
        if (
            s.get("reduced_motion", True)
            or not s.get("visual_effects", True)
            or s.get("lightweight", False)
            or s.get("high_contrast", False)
        ):
            return
        self.animation.stop()
        self.animation.setStartValue(self.hover)
        self.animation.setEndValue(value)
        self.animation.start()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.scale(self.width() / 182, self.height() / 182)
        theme=self.owner.settings["theme"]
        dark = theme in ("Dark", "Apex")
        apex = theme=="Apex"
        connected = self.owner.status == "Connected"
        depth = (
            self.owner.settings.get("visual_effects", True)
            and not self.owner.settings.get("lightweight", False)
            and not self.owner.settings.get("high_contrast", False)
        )
        if depth:
            p.translate(0, -self.hover * 1.2)
        color = QColor(
            latency_color(self.owner.latency_ms)
            if connected
            else (
                "#EC6573"
                if self.owner.status == "Error"
                else self.owner.settings["accent"]
            )
        )
        halo = QColor(color)
        halo.setAlpha(14 if dark else 18)
        p.setPen(Qt.NoPen)
        p.setBrush(halo)
        p.drawEllipse(1, 1, 180, 180)
        if depth:
            p.setPen(Qt.NoPen)
            p.setBrush(QColor(0, 5, 20, 65 if dark else 15))
            p.drawEllipse(QRectF(14, 20, 154, 159))
        fill = QLinearGradient(15, 15, 160, 170)
        fill.setColorAt(0, QColor("#28121B" if apex else "#35405A" if dark else "#FFFFFF"))
        fill.setColorAt(1, QColor("#100C12" if apex else "#20283F" if dark else "#EEF0FA"))
        p.setBrush(fill)
        p.setPen(QPen(QColor("#35528A" if apex else "#5B6680" if dark else "#FFFFFF"), 2))
        p.drawEllipse(11, 11, 160, 160)
        if depth:
            shine = QLinearGradient(0, 13, 0, 163)
            shine.setColorAt(0, QColor(255, 255, 255, 60 if dark else 170))
            shine.setColorAt(0.6, QColor(255, 255, 255, 0))
            p.setPen(Qt.NoPen)
            p.setBrush(shine)
            p.drawEllipse(QRectF(17, 14, 148, 142))
            p.setPen(QPen(QColor(255, 255, 255, 70 if dark else 230), 1.3))
            p.setBrush(Qt.NoBrush)
            p.drawArc(QRectF(17, 17, 148, 148), 40 * 16, 100 * 16)
        p.setPen(QPen(color, 2.5, Qt.SolidLine, Qt.RoundCap))
        p.setBrush(Qt.NoBrush)
        p.drawEllipse(11, 11, 160, 160)
        if (
            self.owner.status == "Connecting"
            and self.spinner.state() == QVariantAnimation.Running
        ):
            p.setPen(QPen(QColor(255, 255, 255, 190), 3, Qt.SolidLine, Qt.RoundCap))
            p.drawArc(QRectF(11, 11, 160, 160), int(self.phase * 16), 55 * 16)
        if connected and self.owner.latency_ms is not None:
            p.setPen(color)
            p.setFont(QFont("Segoe UI", 28, QFont.DemiBold))
            p.drawText(
                QRectF(15, 56, 152, 48), Qt.AlignCenter, f"{self.owner.latency_ms:.0f}"
            )
            p.setFont(QFont("Segoe UI", 10))
            p.drawText(QRectF(15, 106, 152, 22), Qt.AlignCenter, "ms  ·  HTTPS")
        elif self.owner.status == "Connecting":
            # Native vector mark: no pasted bitmap/background, crisp at every DPI.
            from PySide6.QtSvg import QSvgRenderer
            from .branding import ASSETS
            renderer=getattr(self,'mark_renderer',None)
            if renderer is None:self.mark_renderer=renderer=QSvgRenderer(str(ASSETS/'apex-mark.svg'),self)
            p.save();p.translate(0,2);p.setOpacity(.18);renderer.render(p,QRectF(57,55,68,68));p.restore()
            renderer.render(p,QRectF(57,53,68,68))
        else:
            p.setPen(QPen(color, 4, Qt.SolidLine, Qt.RoundCap))
            p.drawArc(65, 69, 52, 52, 135 * 16, 270 * 16)
            p.drawLine(91, 57, 91, 89)
