"""Native captures; catalog/results are clearly labeled demonstration data."""
import os, pathlib, sys, tempfile, time
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
from PySide6.QtWidgets import QApplication
from nextapp.ui import Window
from nextapp.subscriptions import Subscription
from nextapp.profiles import parse_link
app=QApplication([])
out=pathlib.Path(__file__).resolve().parents[1]/'docs/screenshots/v070';out.mkdir(parents=True,exist_ok=True)
with tempfile.TemporaryDirectory() as folder:
 w=Window(folder);w.settings['language']='fa';w.rebuild();w.show();app.processEvents();w.grab().save(str(out/'home-fa.png'))
 for width,height in [(420,660),(468,740)]:
  w.resize(width,height);app.processEvents();assert w.dashboard.minimumSizeHint().height()<=w.dashboard.height();w.grab().save(str(out/f'home-{width}-{height}.png'))
 w.connection_state('Connecting','نمونه نمایشی · در حال بررسی اتصال');app.processEvents();w.toast.hide();w.grab().save(str(out/'loading-icon-sample-fa.png'));w.connection_state('Disconnected','');w.toast.hide()
 w.resize(468,740)
 one=Subscription('نمونه نمایشی · اشتراک اول','https://example.invalid/one');two=Subscription('نمونه نمایشی · اشتراک دوم','https://example.invalid/two');one.metadata={'upload':2*1024**3,'download':21*1024**3,'total':100*1024**3}
 w.subscriptions=[one,two];w.profiles=[parse_link(f'trojan://sample@example.invalid:443?security=tls#نمونه نمایشی · سرور {i+1}') for i in range(8)]
 for i,p in enumerate(w.profiles):p.subscription_id=one.id if i<6 else two.id
 for i,(status,latency) in enumerate([('Verified',86),('Verified',164),('Timeout',None),('Failed',None)]):
  p=w.profiles[i];p.test_status=status;p.latency=latency;p.test_method='HTTPS';p.tested_at='sample'
 w.servers_page.select_group(one.id);w.navigate(1);app.processEvents();w.grab().save(str(out/'servers-sample-fa.png'))
 w.servers_page.groups.showPopup();app.processEvents();w.grab().save(str(out/'source-sheet-context-fa.png'));w.servers_page.groups.sheet.grab().save(str(out/'source-sheet-fa.png'));w.servers_page.groups.sheet.hide()
 w.test_busy=True;w.test_total=6;w.test_completed=4;w.test_started=time.monotonic()-7;w.testing_states={w.profiles[4].id:'Testing…',w.profiles[5].id:'Queued'};w.servers_page.operation_progress();w.populate();app.processEvents();w.grab().save(str(out/'tests-progress-sample-fa.png'));w.test_busy=False;w.testing_states.clear();w.servers_page.operation_progress()
 w.navigate(3);app.processEvents();w.grab().save(str(out/'settings-fa.png'));w.notice('نمونه نمایشی · تغییرات ذخیره شد.');app.processEvents();w.grab().save(str(out/'toast-sample-fa.png'));w.close();app.processEvents()
print(out)
