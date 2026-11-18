"""Theme-integrated caption without the OS accent bar; native move/resize APIs."""
import weakref
from PySide6.QtCore import Qt,QRectF,QPoint
from PySide6.QtGui import QPainter,QPen,QColor
from PySide6.QtWidgets import QWidget,QHBoxLayout,QLabel,QPushButton

class CaptionButton(QPushButton):
    def __init__(self,kind,owner):
        super().__init__();self.kind=kind;self.owner=weakref.proxy(owner);self.setFixedSize(34,24)
        self.setAccessibleName({'close':'Close','min':'Minimize','max':'Maximize / restore'}[kind]);self.setToolTip(self.accessibleName())
        self.clicked.connect(self.perform)
    def perform(self):
        owner=self.owner
        if self.kind=='close':owner.close()
        elif self.kind=='min':
            # Let Windows perform its native minimize transition. Animating
            # top-level opacity first can block or lose the state change on some
            # Windows compositors.
            owner.showMinimized()
        elif owner.isMaximized():owner.showNormal()
        else:owner.showMaximized()
    def paintEvent(self,event):
        p=QPainter(self);p.setRenderHint(QPainter.Antialiasing);dark=self.owner.settings['theme'] in ('Dark','Apex')
        if self.underMouse():p.fillRect(self.rect(),QColor('#B43849') if self.kind=='close' else QColor(110,140,190,35))
        p.setPen(QPen(QColor('#E4EAF9' if dark else '#4A5670'),1.2))
        if self.kind=='close':p.drawLine(13,8,21,16);p.drawLine(21,8,13,16)
        elif self.kind=='min':p.drawLine(12,15,22,15)
        else:p.drawRect(13,8,9,8)

class WindowChrome(QWidget):
    def __init__(self,owner):
        super().__init__();self.owner=weakref.proxy(owner);self.setFixedHeight(25);self.setObjectName('windowChrome')
        self.setLayoutDirection(Qt.LeftToRight);row=QHBoxLayout(self);row.setContentsMargins(2,0,0,0);row.setSpacing(0)
        title=QLabel('Apex VPN');title.setProperty('kind','eyebrow');title.setAttribute(Qt.WA_TransparentForMouseEvents);row.addWidget(title,1)
        self.minimum=CaptionButton('min',owner);self.maximum=CaptionButton('max',owner);self.close_button=CaptionButton('close',owner)
        for button in (self.minimum,self.maximum,self.close_button):row.addWidget(button)
    def sync(self):self.maximum.setVisible(self.owner.settings.get('allow_resize',False))
    def mousePressEvent(self,event):
        if event.button()==Qt.LeftButton and self.owner.windowHandle():self.owner.windowHandle().startSystemMove()
    def mouseDoubleClickEvent(self,event):
        if event.button()==Qt.LeftButton and self.owner.settings.get('allow_resize',False):self.owner.showNormal() if self.owner.isMaximized() else self.owner.showMaximized()
