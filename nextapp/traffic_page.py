"""Compact measured-usage rows; source selection never edits saved preferences."""
from PySide6.QtCore import Qt,QSize
from PySide6.QtGui import QPainter,QColor,QFont,QPen
from PySide6.QtWidgets import QFrame,QWidget,QVBoxLayout,QLabel,QComboBox,QSizePolicy
from .usage import size

PERIODS=(('session','این جلسه','This session'),('12h','۱۲ ساعت گذشته','Last 12 hours'),('24h','۲۴ ساعت گذشته','Last 24 hours'),('7d','۷ روز گذشته','Last 7 days'),('30d','۳۰ روز گذشته','Last 30 days'),('365d','۳۶۵ روز گذشته','Last 365 days'))

class UsageRows(QWidget):
    """One lightweight paint surface: aligned values, no nested compositor effects."""
    def __init__(self,owner,fa,parent=None):
        super().__init__(parent);self.owner=owner;self.fa=fa;self.data={};self.observed=False
        self.setMinimumWidth(0);self.setSizePolicy(QSizePolicy.Expanding,QSizePolicy.Fixed)
        self.row_height=max(43,round(43*owner.settings.get("text_scale",100)/100));self.setFixedHeight(self.row_height*len(PERIODS))
        self.setAccessibleName('مصرف ثبت‌شده در شش بازه' if fa else 'Measured traffic for six periods')

    def set_report(self,report):
        if self.data==report:return
        self.data=report;self.observed=report['observed']
        details=[]
        for key,fa,en in PERIODS:
            item=report[key];details.append(f"{fa if self.fa else en}: {item['total']:,} bytes (download {item['download']:,}, upload {item['upload']:,})")
        self.setToolTip('\n'.join(details));self.setAccessibleDescription('\n'.join(details));self.update()

    def paintEvent(self,event):
        p=QPainter(self);p.setRenderHint(QPainter.Antialiasing);p.setLayoutDirection(Qt.LeftToRight)
        root=self.parentWidget()
        while root is not None and root.objectName()!='settingsRoot':root=root.parentWidget()
        dark=bool(root.property('settingsDark')) if root is not None else self.owner.settings.get('settings_theme','Apex') in ('Dark','Apex')
        fg=QColor('#E7EFFB' if dark else '#24334C');muted=QColor('#91A2BF' if dark else '#70819C')
        accent=QColor(self.owner.settings.get('accent','#4F8CFF'));width=self.width()
        base=QFont(self.font());base.setPixelSize(12)
        for index,(key,fa,en) in enumerate(PERIODS):
            top=index*self.row_height
            if index==0:
                tint=QColor(accent);tint.setAlpha(18);p.setPen(Qt.NoPen);p.setBrush(tint);p.drawRoundedRect(0,top,width,self.row_height-3,8,8)
            elif index>1:
                line=QColor(muted);line.setAlpha(30);p.setPen(QPen(line,1));p.drawLine(9,top-2,width-9,top-2)
            data=self.data.get(key,{});total=size(data.get('total',0)) if self.observed else '—'
            font=QFont(base);font.setBold(index==0);p.setFont(font);p.setPen(fg)
            label=fa if self.fa else en
            # Keep metrics LTR even when Persian labels are RTL.
            label_width=max(70,width//2-12)
            text=p.fontMetrics().elidedText(label,Qt.ElideRight,label_width)
            if self.fa:
                p.drawText(width//2,top+3,width//2-10,20,Qt.AlignRight|Qt.AlignAbsolute|Qt.AlignVCenter|Qt.TextForceRightToLeft,text)
                p.setPen(accent if index==0 else fg);p.drawText(10,top+3,width//2-12,20,Qt.AlignLeft|Qt.AlignAbsolute|Qt.AlignVCenter|Qt.TextForceLeftToRight,total)
            else:
                p.drawText(10,top+3,label_width,20,Qt.AlignLeft|Qt.AlignVCenter,text)
                p.setPen(accent if index==0 else fg);p.drawText(width//2,top+3,width//2-10,20,Qt.AlignRight|Qt.AlignAbsolute|Qt.AlignVCenter|Qt.TextForceLeftToRight,total)
            small=QFont(base);small.setPixelSize(10);p.setFont(small);p.setPen(muted)
            down=size(data.get('download',0)) if self.observed else '—';up=size(data.get('upload',0)) if self.observed else '—'
            p.drawText(10,top+24,width-20,17,Qt.AlignLeft|Qt.AlignVCenter|Qt.TextForceLeftToRight,f'↓ {down}    ·    ↑ {up}')

class TrafficPage(QFrame):
    def __init__(self,owner,fa):
        super().__init__();self.owner=owner;self.fa=fa;self.setObjectName('settingsCard');self.setMinimumWidth(0)
        lay=QVBoxLayout(self);lay.setContentsMargins(12,12,12,12);lay.setSpacing(9)
        self.scope=QComboBox();self.scope.setMinimumWidth(0);self.scope.setSizePolicy(QSizePolicy.Ignored,QSizePolicy.Fixed)
        self.scope.addItem('سیستم · آداپتور فعال' if fa else 'System · active adapter','system')
        self.scope.addItem('تونل VPN' if fa else 'VPN tunnel','vpn');lay.addWidget(self.scope)
        self.status=QLabel();self.status.setObjectName('settingsMuted');self.status.setWordWrap(True);lay.addWidget(self.status)
        self.rows=UsageRows(owner,fa,self);lay.addWidget(self.rows)
        note=QLabel('فقط هنگام اجرای برنامه ثبت می‌شود. آمار سیستم شامل شبکهٔ محلی هم هست.' if fa else 'Recorded while Apex runs. System usage includes local network traffic.')
        note.setObjectName('settingsMuted');note.setWordWrap(True)
        note.setToolTip('دقت بازه‌ها حدود یک دقیقه؛ مصرف قبل از ثبت یا زمان بسته‌بودن قابل بازیابی نیست. آمار تونل و سیستم جدا هستند.' if fa else 'Minute buckets. Earlier/offline history is unavailable. Tunnel and system totals are separate.')
        lay.addWidget(note);self.scope.currentIndexChanged.connect(self.refresh);self.refresh()

    def refresh(self):
        history=getattr(self.owner,'traffic_history',None);scope=self.scope.currentData()
        if history is None or history.closed:
            self.status.setText('ثبت مصرف در دسترس نیست.' if self.fa else 'Usage recording unavailable.');return
        report=history.report(scope);self.rows.set_report(report)
        adapter=getattr(self.owner,'traffic_adapter','')
        text=(adapter or ('در انتظار اندازه‌گیری' if self.fa else 'Waiting for measurement')) if scope=='system' else ('شمارندهٔ واقعی هسته' if self.fa else 'Measured core counters')
        self.status.setText(text)
        import datetime
        since=datetime.datetime.fromtimestamp(report['tracking_started']).strftime('%Y-%m-%d %H:%M')
        self.status.setToolTip(('شروع ثبت: ' if self.fa else 'Tracking since: ')+since)
