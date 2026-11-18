"""Event-driven paint effects; identity output at rest, unchanged widget geometry."""
import math,time,weakref
import shiboken6
from PySide6.QtCore import QObject,QEvent,QTimer,QVariantAnimation,QEasingCurve,Qt,QPointF,QRectF
from PySide6.QtGui import QPainter,QColor,QPen,QPainterPath
from PySide6.QtWidgets import QWidget,QApplication,QAbstractButton,QPushButton,QCheckBox,QStyle,QStyleOptionButton


def allowed(owner):
    s=getattr(owner,'settings',{})
    return bool(s.get('visual_effects',True) and not any(s.get(k,False) for k in ('reduced_motion','lightweight','high_contrast')))

class FeedbackOverlay(QWidget):
    def __init__(self,parent,owner):
        super().__init__(parent);self.owner_ref=weakref.ref(owner);self.items=[]
        self.setAttribute(Qt.WA_TransparentForMouseEvents);self.setAttribute(Qt.WA_NoSystemBackground)
        self.setAttribute(Qt.WA_TranslucentBackground);self.setFocusPolicy(Qt.NoFocus)
        self.setGeometry(parent.rect());self.hide();self.timer=QTimer(self);self.timer.setInterval(16);self.timer.timeout.connect(self.step)

    def add(self,kind,widget,point=None):
        owner=self.owner_ref()
        if not owner or not allowed(owner) or not widget.isVisible() or widget.window() is not owner:return
        origin=widget.mapTo(self.parentWidget(),widget.rect().topLeft())
        rect=QRectF(origin.x(),origin.y(),widget.width(),widget.height())
        center=QPointF(origin+(point or widget.rect().center()))
        if kind=='burst' and isinstance(widget,QCheckBox):
            from .responsive import ToggleSwitch
            if isinstance(widget,ToggleSwitch):center=QPointF(origin.x()+widget.width()/2,origin.y()+widget.height()/2)
            else:
                opt=QStyleOptionButton();opt.initFrom(widget);opt.rect=widget.rect();opt.text=widget.text()
                r=widget.style().subElementRect(QStyle.SE_CheckBoxIndicator,opt,widget);center=QPointF(origin+r.center())
        self.items=self.items[-23:]
        self.items.append((kind,rect,center,time.monotonic()));self.setGeometry(self.parentWidget().rect());self.show();self.raise_()
        if not self.timer.isActive():self.timer.start()
        self.update()

    def step(self):
        now=time.monotonic();self.items=[x for x in self.items if now-x[3]<.32]
        owner=self.owner_ref()
        if not self.items or not owner or not allowed(owner):self.items.clear();self.timer.stop();self.hide();return
        self.update()

    def paintEvent(self,event):
        owner=self.owner_ref()
        if not owner:return
        painter=QPainter(self);painter.setRenderHint(QPainter.Antialiasing);now=time.monotonic()
        for kind,rect,center,started in self.items:
            t=min(1,(now-started)/.32);color=QColor(owner.settings.get('accent','#4F8CFF'))
            if kind=='burst':
                color.setAlpha(int(150*(1-t)));painter.setPen(QPen(color,1.3,Qt.SolidLine,Qt.RoundCap))
                for n in range(6):
                    a=n*math.pi/3;r=9+10*t;length=3*(1-t)
                    painter.drawLine(QPointF(center.x()+math.cos(a)*r,center.y()+math.sin(a)*r),QPointF(center.x()+math.cos(a)*(r+length),center.y()+math.sin(a)*(r+length)))
            else:
                painter.save();clip=QPainterPath();clip.addRoundedRect(rect,9,9);painter.setClipPath(clip)
                color.setAlpha(int((25 if kind=='hover' else 48)*(1-t)));painter.setPen(Qt.NoPen);painter.setBrush(color)
                radius=(max(rect.width(),rect.height())*.8)*(1-(1-t)**3)
                painter.drawEllipse(center,radius,radius);painter.restore()

class InteractionEffects(QObject):
    def __init__(self,owner):
        super().__init__(owner);self.owner=owner;self.effects=weakref.WeakKeyDictionary();self.overlay=None;self.closed=False
        QApplication.instance().installEventFilter(self)
        for widget in owner.findChildren(QAbstractButton):self.attach(widget)

    def overlay_for(self):
        parent=self.owner.centralWidget()
        if parent is None:return None
        if self.overlay is None or not shiboken6.isValid(self.overlay) or self.overlay.parentWidget() is not parent:self.overlay=FeedbackOverlay(parent,self.owner)
        return self.overlay

    def attach(self,w):
        if not isinstance(w,QAbstractButton) or w in self.effects:return
        from .responsive import ToggleSwitch
        # Qt cannot safely compose an ancestor drop shadow with a second
        # QGraphicsEffect on its child on all Windows/DPI paint backends.
        # Keep native widget painting; all feedback lives in a separate overlay.
        self.effects[w]=None
        if isinstance(w,QCheckBox):
            ref=weakref.ref(w)
            w.toggled.connect(lambda checked,ref=ref:self.toggle(ref,checked))

    def toggle(self,ref,checked):
        w=ref()
        if self.closed or w is None or not shiboken6.isValid(w) or not allowed(self.owner):return
        effect=self.effects.get(w)
        if effect is not None and shiboken6.isValid(effect):effect.checked(checked)
        if checked:
            overlay=self.overlay_for()
            if overlay:overlay.add('burst',w)

    def eventFilter(self,obj,event):
        if self.closed or not isinstance(obj,QWidget) or obj is self.owner or not self.owner.isAncestorOf(obj):return False
        kind=event.type()
        if kind==QEvent.Show and isinstance(obj,QAbstractButton):self.attach(obj)
        if obj not in self.effects:return False
        effect=self.effects.get(obj)
        if not allowed(self.owner):
            if effect is not None and shiboken6.isValid(effect):effect.anim.stop();effect.scale=1.;effect.mix=1.;effect.update()
            return False
        if kind==QEvent.Enter:
            overlay=self.overlay_for()
            if overlay:overlay.add('hover',obj)
        elif kind in (QEvent.MouseButtonPress,QEvent.KeyPress):
            if kind==QEvent.MouseButtonPress and event.button()!=Qt.LeftButton:return False
            if kind==QEvent.KeyPress and event.key() not in (Qt.Key_Space,Qt.Key_Return,Qt.Key_Enter):return False
            if effect is not None and shiboken6.isValid(effect):effect.animate(.975,85)
            overlay=self.overlay_for()
            if overlay:overlay.add('ripple',obj,event.position().toPoint() if kind==QEvent.MouseButtonPress else None)
        elif kind in (QEvent.MouseButtonRelease,QEvent.KeyRelease,QEvent.Leave,QEvent.FocusOut):
            if effect is not None and shiboken6.isValid(effect):effect.animate(1.,150)
        return False

    def shutdown(self):
        if self.closed:return
        self.closed=True;QApplication.instance().removeEventFilter(self)
        for effect in list(self.effects.values()):
            if effect is not None and shiboken6.isValid(effect):effect.anim.stop()
        if self.overlay is not None and shiboken6.isValid(self.overlay):self.overlay.items.clear();self.overlay.timer.stop();self.overlay.hide()
