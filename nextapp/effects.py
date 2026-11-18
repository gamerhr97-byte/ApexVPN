"""Static compositor shadows preserve widget geometry and remain idle without timers."""
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QFrame,QGraphicsDropShadowEffect

def apply_depth(owner):
    enabled=owner.settings.get('visual_effects',True) and not owner.settings.get('high_contrast',False) and not owner.settings.get('lightweight',False)
    for frame in owner.findChildren(QFrame):
        if frame.objectName() not in ('card','addSheet','settingsCard'):continue
        effect=frame.graphicsEffect()
        if enabled:
            if not isinstance(effect,QGraphicsDropShadowEffect):effect=QGraphicsDropShadowEffect(frame);frame.setGraphicsEffect(effect)
            effect.setBlurRadius(14 if frame.objectName()=='settingsCard' else 20);effect.setOffset(0,3 if frame.objectName()=='settingsCard' else 5);effect.setColor(QColor(9,18,42,80 if owner.settings['theme'] in ('Dark','Apex') else 35))
        elif effect:frame.setGraphicsEffect(None)
