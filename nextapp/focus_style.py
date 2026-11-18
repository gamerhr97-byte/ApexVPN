"""Replace Qt's platform-native dotted focus rectangle with themed focus borders.

Keyboard focus remains functional: line edits, buttons and switches retain the
explicit focus cues defined by the app's QSS/native paint implementations.
"""

from PySide6.QtWidgets import QProxyStyle, QStyle


class CleanFocusStyle(QProxyStyle):
    def drawPrimitive(self, element, option, painter, widget=None):
        if element == QStyle.PE_FrameFocusRect:
            return
        super().drawPrimitive(element, option, painter, widget)
