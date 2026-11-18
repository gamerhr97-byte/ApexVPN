"""Actual native UI captures; all sample catalog/test data is visibly labeled."""
import os,pathlib,sys,tempfile
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
from PySide6.QtWidgets import QApplication
from nextapp.ui import Window
from nextapp.profiles import parse_link
from nextapp.subscriptions import Subscription
app=QApplication([]);out=pathlib.Path(__file__).resolve().parents[1]/'docs/screenshots/v060';out.mkdir(parents=True,exist_ok=True)
with tempfile.TemporaryDirectory() as root:
 w=Window(root);w.show();app.processEvents();w.grab().save(str(out/'home.png'));size=w.size()
 w.navigate(3);app.processEvents();w.grab().save(str(out/'settings-menu.png'))
 for index in range(13):
  w.settings_page.open_category(index);app.processEvents();assert w.size()==size;w.grab().save(str(out/f'settings-{index+1:02}.png'))
 w.settings['language']='fa';w.current=3;w.rebuild();app.processEvents();w.grab().save(str(out/'settings-menu-fa.png'));w.settings_page.open_category(0);app.processEvents();w.grab().save(str(out/'general-fa.png'))
 first=Subscription('نمونه نمایشی · ساب اول','https://example.invalid/sample-a');second=Subscription('نمونه نمایشی · ساب دوم','https://example.invalid/sample-b');first.metadata={'upload':5*1024**3,'download':20*1024**3,'total':100*1024**3};second.metadata={'upload':2*1024**3,'download':8*1024**3,'total':50*1024**3}
 w.subscriptions=[first,second];w.profiles=[parse_link(f'trojan://test@example.invalid:443?security=tls#نمونه نمایشی {index+1}') for index in range(8)]
 for index,p in enumerate(w.profiles):p.subscription_id=first.id if index<5 else second.id
 w.profiles[0].latency=42;w.profiles[0].test_method='TCP';w.profiles[1].test_status='Timeout';w.profiles[1].tested_at='sample';w.profiles[2].latency=165;w.profiles[2].test_method='HTTPS';w.profiles[2].test_status='Verified'
 w.selected=w.profiles[0].id;w.populate();w.servers_page.select_group(first.id);w.navigate(1);app.processEvents();assert w.size()==size;w.grab().save(str(out/'servers-sample-fa.png'));w.servers_page.select_group(second.id);app.processEvents();w.grab().save(str(out/'second-subscription-sample-fa.png'))
 w.navigate(0);w.refresh_profile();app.processEvents();w.grab().save(str(out/'home-sample-fa.png'));w.settings['theme']='Dark';w.apply_theme();app.processEvents();w.grab().save(str(out/'home-dark-sample-fa.png'));w.close();app.processEvents()
print('Native screenshots captured at 468×740. Sample catalog/results are labeled.')
