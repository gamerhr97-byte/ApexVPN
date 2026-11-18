"""One original vector glyph system for Settings and connection service tiles."""

from PySide6.QtCore import Qt, QRectF, QPointF, QSize
from PySide6.QtGui import (
    QPixmap,
    QPainter,
    QPen,
    QColor,
    QIcon,
    QFont,
    QPainterPath,
    QPolygonF,
)
from PySide6.QtWidgets import QPushButton
import math

CATEGORY_GLYPHS = (
    "sliders",
    "bolt",
    "cube",
    "globe",
    "split",
    "shield",
    "pulse",
    "refresh",
    "plane",
    "gauge",
    "sun",
    "terminal",
    "log",
    "split",
    "gauge",
)


def draw_glyph(p, kind, color):
    p.setRenderHint(QPainter.Antialiasing)
    p.setPen(QPen(QColor(color), 1.7, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
    p.setBrush(Qt.NoBrush)
    if kind == "sliders":
        for x, y in ((6, 8), (12, 16), (18, 10)):
            p.drawLine(x, 4, x, 20)
            p.drawEllipse(QPointF(x, y), 2.4, 2.4)
    elif kind == "bolt":
        p.drawPolyline(
            QPolygonF(
                [
                    QPointF(14, 2),
                    QPointF(5, 14),
                    QPointF(11, 14),
                    QPointF(9, 22),
                    QPointF(19, 9),
                    QPointF(13, 9),
                    QPointF(14, 2),
                ]
            )
        )
    elif kind == "cube":
        p.drawPolygon(
            QPolygonF(
                [
                    QPointF(12, 3),
                    QPointF(21, 8),
                    QPointF(21, 17),
                    QPointF(12, 22),
                    QPointF(3, 17),
                    QPointF(3, 8),
                ]
            )
        )
        p.drawLine(3, 8, 12, 13)
        p.drawLine(12, 13, 21, 8)
        p.drawLine(12, 13, 12, 22)
    elif kind == "globe":
        p.drawEllipse(QRectF(3, 3, 18, 18))
        p.drawEllipse(QRectF(8, 3, 8, 18))
        p.drawLine(3, 12, 21, 12)
    elif kind == "split":
        p.drawLine(5, 20, 5, 5)
        p.drawLine(5, 12, 17, 12)
        p.drawLine(17, 12, 17, 5)
        p.drawLine(2, 8, 5, 5)
        p.drawLine(5, 5, 8, 8)
        p.drawLine(14, 8, 17, 5)
        p.drawLine(17, 5, 20, 8)
    elif kind == "shield":
        path = QPainterPath(QPointF(12, 2))
        path.lineTo(21, 6)
        path.lineTo(20, 13)
        path.quadTo(18, 19, 12, 22)
        path.quadTo(6, 19, 4, 13)
        path.lineTo(3, 6)
        path.closeSubpath()
        p.drawPath(path)
        p.drawLine(8, 12, 11, 15)
        p.drawLine(11, 15, 17, 8)
    elif kind == "pulse":
        p.drawPolyline(
            QPolygonF(
                [
                    QPointF(2, 12),
                    QPointF(7, 12),
                    QPointF(10, 4),
                    QPointF(14, 20),
                    QPointF(17, 12),
                    QPointF(22, 12),
                ]
            )
        )
    elif kind == "refresh":
        p.drawArc(QRectF(4, 4, 16, 16), 45 * 16, 285 * 16)
        p.drawLine(20, 4, 20, 10)
        p.drawLine(20, 10, 14, 10)
    elif kind == "plane":
        p.drawPolygon(
            QPolygonF(
                [
                    QPointF(2, 11),
                    QPointF(22, 3),
                    QPointF(17, 22),
                    QPointF(11, 15),
                    QPointF(2, 11),
                ]
            )
        )
        p.drawLine(11, 15, 18, 7)
    elif kind == "gauge":
        p.drawArc(QRectF(3, 4, 18, 18), 0, 180 * 16)
        p.drawLine(12, 13, 18, 7)
        p.drawLine(4, 20, 20, 20)
    elif kind == "sun":
        p.drawEllipse(QRectF(7, 7, 10, 10))
        for i in range(8):
            a = i * math.pi / 4
            p.drawLine(
                QPointF(12 + 8 * math.cos(a), 12 + 8 * math.sin(a)),
                QPointF(12 + 11 * math.cos(a), 12 + 11 * math.sin(a)),
            )
    elif kind == "terminal":
        p.drawRoundedRect(QRectF(2, 4, 20, 16), 3, 3)
        p.drawLine(6, 9, 10, 12)
        p.drawLine(10, 12, 6, 15)
        p.drawLine(13, 16, 18, 16)
    elif kind == "log":
        p.drawRoundedRect(QRectF(4, 2, 16, 20), 2, 2)
        for y in (7, 12, 17):
            p.drawLine(8, y, 16, y)
    elif kind == "play":
        p.setBrush(QColor(color))
        p.setPen(Qt.NoPen)
        p.drawRoundedRect(QRectF(1, 5, 22, 15), 4, 4)
        p.setBrush(QColor("white"))
        p.drawPolygon(QPolygonF([QPointF(10, 9), QPointF(10, 17), QPointF(17, 13)]))
    elif kind == "spark":
        p.setBrush(QColor(color))
        p.drawPolygon(
            QPolygonF(
                [
                    QPointF(12, 1),
                    QPointF(15, 9),
                    QPointF(23, 12),
                    QPointF(15, 15),
                    QPointF(12, 23),
                    QPointF(9, 15),
                    QPointF(1, 12),
                    QPointF(9, 9),
                ]
            )
        )
    elif kind == "chat":
        p.drawRoundedRect(QRectF(3, 4, 18, 14), 5, 5)
        p.drawLine(6, 18, 5, 22)
        p.drawLine(5, 22, 12, 18)
    elif kind == "camera":
        p.drawRoundedRect(QRectF(3, 3, 18, 18), 5, 5)
        p.drawEllipse(QRectF(7, 7, 10, 10))
        p.drawPoint(18, 6)
    elif kind == "phone":
        p.drawEllipse(QRectF(3, 2, 18, 18))
        p.drawLine(5, 18, 3, 23)
        p.drawLine(3, 23, 10, 20)
        p.drawArc(QRectF(7, 6, 10, 10), 150 * 16, 160 * 16)
    elif kind == "game":
        p.drawRoundedRect(QRectF(2, 5, 20, 14), 5, 5)
        p.drawEllipse(QPointF(8, 12), 1.4, 2)
        p.drawEllipse(QPointF(16, 12), 1.4, 2)
    elif kind == "waves":
        for y in (6, 11, 16):
            p.drawArc(QRectF(2, y, 20, 10), 35 * 16, 110 * 16)
    else:
        p.setFont(QFont("Segoe UI", 11, QFont.Bold))
        p.drawText(QRectF(0, 0, 24, 24), Qt.AlignCenter, kind)


def glyph_icon(kind, color="#85AEFF", size=24):
    pix = QPixmap(size * 2, size * 2)
    pix.fill(Qt.transparent)
    p = QPainter(pix)
    p.scale(size * 2 / 24, size * 2 / 24)
    draw_glyph(p, kind, color)
    p.end()
    icon = QIcon(pix)
    selected = QPixmap(size * 2, size * 2)
    selected.fill(Qt.transparent)
    p = QPainter(selected)
    p.scale(size * 2 / 24, size * 2 / 24)
    draw_glyph(p, kind, "#FFFFFF")
    p.end()
    icon.addPixmap(selected, QIcon.Selected)
    return icon


class ServiceTile(QPushButton):
    """One-line compact service chip; state is descriptive, not a false hard failure."""
    def __init__(self, service, owner):
        super().__init__()
        self.service = service
        self.owner = owner
        self.value = None
        self.pending = False
        self.setFixedHeight(34)
        self.setMinimumWidth(0)
        self.setAccessibleName(service.name)
        self.setCursor(Qt.PointingHandCursor)
        self.clicked.connect(self.explain)

    def set_pending(self):
        self.value = None
        self.pending = True
        self.setToolTip(self.service.name + " · Checking website…")
        self.update()

    def set_result(self, value):
        self.value = value
        self.pending = False
        text = self.service.name + " · " + (
            value.reason + (f" · HTTP {value.status}" if value.status else "")
            + (f" · {value.latency:.0f} ms" if value.latency is not None else "")
            if value else "Not checked")
        self.setToolTip(text)
        self.setAccessibleDescription(text)
        self.update()

    def explain(self):
        self.owner.service_checks.ping_one(self.service.key)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        dark = self.owner.settings["theme"] in ("Dark", "Apex")
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(100, 145, 245, 65 if self.isDown() else 35 if self.underMouse() else 18))
        p.drawRoundedRect(self.rect().adjusted(1, 1, -1, -1), 9, 9)
        from .service_icons import service_icon
        service_icon(self.service.key,self.service.color).paint(p,5,(self.height()-24)//2,24,24)
        color = "#22C55E" if self.value and self.value.state == "ok" else (
            "#EF4444" if self.value and self.value.state == "failed" else "#94A3B8")
        badge = "✓" if self.value and self.value.state == "ok" else (
            "×" if self.value and self.value.state == "failed" else "…" if self.pending else "?")
        p.setPen(QColor("#DFE7F4" if dark else "#34435E"))
        p.setFont(QFont("Segoe UI", 9))
        p.drawText(QRectF(29, 0, max(0, self.width()-49), self.height()),
                   Qt.AlignVCenter | Qt.AlignLeft, self.service.name)
        p.setPen(QColor(color))
        p.setFont(QFont("DejaVu Sans", 9, QFont.Bold))
        p.drawText(QRectF(self.width()-20, 0, 18, self.height()), Qt.AlignCenter, badge)
