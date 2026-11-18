"""Compile Windows x64 launcher with versioned Apex PNG icon and all compatibility entry points."""
import os,pathlib,subprocess,sys,shutil
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
from PySide6.QtCore import Qt,QRectF
from PySide6.QtGui import QImage,QPainter
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import QApplication
from PIL import Image
root=pathlib.Path(__file__).resolve().parents[1]
app=QApplication.instance() or QApplication([])
image=QImage(1024,1024,QImage.Format_ARGB32);image.fill(Qt.transparent)
painter=QPainter(image);QSvgRenderer(str(root/'assets/apex-mark.svg')).render(painter);painter.end();image.save(str(root/'assets/apex-vpn-0.10.7.png'))
Image.open(root/'assets/apex-vpn-0.10.7.png').convert('RGBA').save(root/'assets/apex-vpn.ico',sizes=[(16,16),(24,24),(32,32),(48,48),(64,64),(128,128),(256,256)])
subprocess.run([sys.executable,'-m','ziglang','rc','/fo','tools/shadow.res','tools/shadow.rc'],cwd=root,check=True)
subprocess.run([sys.executable,'-m','ziglang','cc','-target','x86_64-windows-gnu','-O2','-s','-municode','-Wl,--subsystem,windows','tools/launcher.c','tools/shadow.res','-o','tools/ApexVPN.exe','-luser32','-lgdi32','-lmsimg32'],cwd=root,check=True)
print(root/'tools/ApexVPN.exe')

host_resource=(root/'tools/shadow.rc').read_text().replace('ApexVPN.exe','ApexVPNHost.exe').replace('Apex VPN Desktop Proxy','Apex VPN')
(root/'tools/host.rc').write_text(host_resource)
subprocess.run([sys.executable,'-m','ziglang','rc','/fo','tools/host.res','tools/host.rc'],cwd=root,check=True)
subprocess.run([sys.executable,'-m','ziglang','cc','-target','x86_64-windows-gnu','-O2','-s','-municode','-Wl,--subsystem,windows','tools/python_host.c','tools/host.res','-o','tools/ApexVPNHost.exe','-luser32','-lshell32'],cwd=root,check=True)
print(root/'tools/ApexVPNHost.exe')

# Every alias must contain the current resources, never a stale historical EXE.
for alias in ('ApexVPN-0.10.7.exe','ShadowBox.exe','NekoRayNext.exe'):
    shutil.copy2(root/'tools/ApexVPN.exe',root/'tools'/alias)

for old in (root/'tools').glob('ApexVPN-0.10.*.exe'):
    if old.name!='ApexVPN-0.10.7.exe':old.unlink()
