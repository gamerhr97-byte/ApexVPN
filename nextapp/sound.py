"""Optional non-blocking native Windows cues. No network, service or global volume changes."""
import os,time
from PySide6.QtCore import QObject,QEvent,Qt
from PySide6.QtWidgets import QApplication,QPushButton
from .branding import ASSETS

class Sounds(QObject):
    def __init__(self,owner):
        super().__init__(owner);self.owner=owner;self.last=0;self.closed=False;self.available=os.name=='nt'
        self.backend=None
        if self.available:
            try:import winsound;self.backend=winsound
            except ImportError:self.available=False
        QApplication.instance().installEventFilter(self)
    def play(self,name):
        if self.closed or not self.available or not self.owner.settings.get('sound_enabled',True):return False
        if name not in ('click','connected','disconnected','error'):return False
        now=time.monotonic()
        if name=='click' and now-self.last<.08:return False
        self.last=now
        try:
            self.backend.PlaySound(str(ASSETS/'sounds'/(name+'.wav')),self.backend.SND_FILENAME|self.backend.SND_ASYNC|self.backend.SND_NODEFAULT)
            return True
        except (RuntimeError,OSError):return False
    def eventFilter(self,watched,event):
        if isinstance(watched,QPushButton) and watched.isEnabled() and watched.window() is self.owner:
            if event.type()==QEvent.MouseButtonPress and event.button()==Qt.LeftButton:self.play('click')
            elif event.type()==QEvent.KeyPress and not event.isAutoRepeat() and event.key() in (Qt.Key_Space,Qt.Key_Return,Qt.Key_Enter):self.play('click')
        return False
    def shutdown(self):
        if self.closed:return
        self.closed=True;QApplication.instance().removeEventFilter(self)
        if self.backend:
            try:self.backend.PlaySound(None,self.backend.SND_ASYNC)
            except (RuntimeError,OSError):pass
