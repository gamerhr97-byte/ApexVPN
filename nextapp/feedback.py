"""Short in-window feedback; never blocks an operation or exposes profile URLs."""

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QLabel


class Toast(QLabel):
    def __init__(self, owner):
        super().__init__(owner.centralWidget())
        self.owner = owner
        self.setObjectName("toast")
        self.setWordWrap(True)
        self.setAlignment(Qt.AlignCenter)
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.timer = QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self.hide)
        self.hide()

    def show_message(self, text):
        message = ' '.join(str(text).split())
        self.setToolTip(str(text))
        self.setText(message if len(message) <= 100 else message[:97] + '…')
        dark = self.owner.settings["theme"] in ("Dark", "Apex")
        self.setStyleSheet(
            "QLabel{background:%s;color:%s;border:0;"
            "border-radius:8px;padding:8px;font-size:12px;}"
            % ("#166534" if dark else "#DCFCE7", "#F0FDF4" if dark else "#14532D")
        )
        self.reposition()
        self.show()
        self.raise_()
        self.timer.start(1800)

    def reposition(self):
        parent = self.parentWidget()
        self.setFixedWidth(max(200, min(460, parent.width() - 32)))
        self.adjustSize()
        self.move(
            (parent.width() - self.width()) // 2,
            max(60, parent.height() - self.height() - 20),
        )


def improve_scroll(area):
    """Pixel-based wheel/trackpad scrolling with usable keyboard and thumb steps."""
    from PySide6.QtWidgets import QAbstractItemView, QScroller

    if isinstance(area, QAbstractItemView):
        area.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)
        area.setHorizontalScrollMode(QAbstractItemView.ScrollPerPixel)
    area.verticalScrollBar().setSingleStep(28)
    # Touch kinetic scrolling only. Mouse selection, wheel and trackpad stay native.
    QScroller.grabGesture(area.viewport(), QScroller.TouchGesture)
