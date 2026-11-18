"""Bounded local startup checks and progress; no Internet requests or proxy edits."""
import hashlib,json,os,pathlib,socket,subprocess,sys,tempfile,time


def run_checks(root,report=lambda percent,label:None):
    from .settings_schema import defaults,migrate
    from .storage import Store
    from .engine import HIDDEN
    result=[];report(10,'Checking data folder')
    with tempfile.TemporaryFile(dir=root) as file:file.write(b'apex-startup');file.flush()
    settings=defaults();settings.update(Store(root).load_settings());settings=migrate(settings)
    result.append('data_folder_ok');report(30,'Checking local ports')
    ports=[settings[k] for k in ('http_port','socks_port','stats_port')]
    if len(set(ports))!=3:result.append('port_configuration_warning')
    for port in ports:
        with socket.socket() as sock:
            sock.settimeout(.08)
            if sock.connect_ex(('127.0.0.1',port))==0:result.append('port_in_use')
    report(45,'Checking network cores')
    base=pathlib.Path(__file__).resolve().parents[1]
    manifest=base/'core/runtime-hashes.json'
    hashes=json.loads(manifest.read_text()) if manifest.exists() else {}
    for n,key in enumerate(('core','singbox_core')):
        path=pathlib.Path(settings[key])
        if not path.is_file():result.append(key+'_missing');continue
        try:
            expected=hashes.get(path.name) if path.resolve().parent==(base/'core').resolve() else None
            if expected:
                with path.open('rb') as file:digest=hashlib.file_digest(file,'sha256').hexdigest()
                if digest!=expected:result.append(key+'_integrity_warning');continue
            checked=subprocess.run([str(path),'version'],stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,timeout=2,**HIDDEN)
            prefix=b'Xray ' if key=='core' else b'sing-box version '
            result.append(key+('_ok' if checked.returncode==0 and checked.stdout.startswith(prefix) else '_version_warning'))
        except (OSError,subprocess.TimeoutExpired):result.append(key+'_unavailable')
        report(65+n*20,'Checking network cores')
    report(90,'Preparing interface')
    if (pathlib.Path(root)/'proxy-recovery.dat').exists():result.append('proxy_recovery_available')
    return result

class ProgressChannel:
    def __init__(self):
        self.map=None;name=os.environ.pop('APEX_VPN_STARTUP_MAP','')
        if os.name=='nt' and name:
            import mmap
            try:self.map=mmap.mmap(-1,4,tagname=name,access=mmap.ACCESS_WRITE)
            except OSError:pass
    def report(self,percent,label=''):
        if self.map is not None:
            import struct
            self.map.seek(0);self.map.write(struct.pack('<I',max(0,min(100,int(percent)))))
    def close(self):
        if self.map is not None:self.map.close();self.map=None


def source_splash():
    from PySide6.QtCore import Qt,QRectF
    from PySide6.QtGui import QPainter,QColor,QLinearGradient,QFont,QPixmap
    from PySide6.QtWidgets import QWidget,QApplication
    class Splash(QWidget):
        def __init__(self):
            super().__init__(None,Qt.SplashScreen|Qt.FramelessWindowHint)
            self.setFixedSize(320,140);self.percent=0;self.label='Checking local environment'
            screen=QApplication.primaryScreen().availableGeometry();self.move(screen.center()-self.rect().center())
        def report(self,percent,label):self.percent=percent;self.label=label;self.update();QApplication.processEvents()
        def paintEvent(self,event):
            p=QPainter(self);p.setRenderHint(QPainter.Antialiasing)
            gradient=QLinearGradient(0,0,320,140);gradient.setColorAt(0,QColor('#65090F'));gradient.setColorAt(1,QColor('#050507'));p.fillRect(self.rect(),gradient)
            image=QPixmap(str(pathlib.Path(__file__).resolve().parents[1]/'assets/apex-vpn-0.10.7.png'));p.drawPixmap(22,30,52,52,image)
            p.setPen(QColor('white'));p.setFont(QFont('Segoe UI',14,QFont.DemiBold));p.drawText(QRectF(91,28,210,28),'Apex VPN')
            p.setFont(QFont('Segoe UI',8));p.setPen(QColor('#E2BAC0'));p.drawText(QRectF(91,61,210,35),Qt.TextWordWrap,self.label)
            p.setPen(Qt.NoPen);p.setBrush(QColor('#33161C'));p.drawRoundedRect(QRectF(22,113,276,5),2,2)
            p.setBrush(QColor('#E53348'));p.drawRoundedRect(QRectF(22,113,276*self.percent/100,5),2,2)
    return Splash()
