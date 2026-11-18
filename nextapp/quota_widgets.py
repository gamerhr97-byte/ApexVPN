from PySide6.QtCore import QEvent,Qt
from PySide6.QtWidgets import QProgressBar,QWidget,QVBoxLayout,QLabel
from .usage import subscription_usage,size
class QuotaStrip(QProgressBar):
    """An inset overlay: adds no rows or height to the existing server card."""
    def __init__(self,parent):
        super().__init__(parent);self.setAttribute(Qt.WA_TransparentForMouseEvents);parent.installEventFilter(self)
    def eventFilter(self,obj,event):
        if event.type() in (QEvent.Resize,QEvent.Show):self.setGeometry(15,max(0,obj.height()-7),max(0,obj.width()-30),4)
        return False

def quota_row(subscription,fa=False):
    row=QWidget();v=QVBoxLayout(row);v.setContentsMargins(0,4,0,8);v.setSpacing(5)
    heading=QLabel(subscription.name);heading.setTextFormat(Qt.PlainText);heading.setWordWrap(True);v.addWidget(heading)
    usage=subscription_usage(subscription.metadata);bar=QProgressBar();bar.setRange(0,1000);bar.setFixedHeight(7);bar.setTextVisible(False);bar.setValue(round(min(100,usage.percent)*10) if usage.known else 0);bar.setEnabled(usage.known);bar.setAccessibleName(('مصرف اشتراک ' if fa else 'Subscription usage ')+subscription.name);v.addWidget(bar)
    if usage.known:
        text=f'{usage.percent:.1f}% · {size(usage.used)} / {size(usage.total)}'
        if fa:text+=' مصرف‌شده'
        else:text+=' used'
        color='#EF4444' if usage.percent>=90 else '#F59E0B' if usage.percent>=75 else '#4F8CFF'
        bar.setStyleSheet(f'QProgressBar{{border:0;border-radius:3px;background:rgba(120,140,180,35);}} QProgressBar::chunk{{background:{color};border-radius:3px;}}')
    else:text='سرویس‌دهنده اطلاعات حجم را اعلام نکرده است.' if fa else 'Quota not supplied by provider; percentage unavailable.'
    detail=QLabel(text);detail.setWordWrap(True);detail.setObjectName('settingsMuted');detail.setTextFormat(Qt.PlainText);v.addWidget(detail);bar.setToolTip(text);return row
