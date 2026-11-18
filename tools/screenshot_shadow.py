"""Native screenshots. Quota example is explicitly marked as sample data."""
import os,pathlib,sys,tempfile,json
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
from PySide6.QtWidgets import QApplication
from nextapp.ui import Window
from nextapp.profiles import parse_link
from nextapp.subscriptions import Subscription
app=QApplication([]);out=pathlib.Path(__file__).resolve().parents[1]/'docs/screenshots/shadow-box-v050';out.mkdir(parents=True,exist_ok=True)
with tempfile.TemporaryDirectory() as root:
 w=Window(root);w.show();app.processEvents();w.grab().save(str(out/'home.png'));size=w.size()
 w.navigate(3);app.processEvents();assert w.size()==size;w.grab().save(str(out/'settings-menu.png'))
 for i in range(13):
  w.settings_page.open_category(i);app.processEvents();assert w.size()==size;w.grab().save(str(out/f'settings-{i+1:02}.png'))
 w.settings['language']='fa';w.current=3;w.rebuild();app.processEvents();w.grab().save(str(out/'settings-menu-fa.png'))
 w.settings_page.open_category(0);app.processEvents();w.grab().save(str(out/'settings-general-fa.png'))
 w.navigate(0);w.settings['theme']='Dark';w.apply_theme();app.processEvents();w.grab().save(str(out/'home-dark.png'))
 w.settings['theme']='Light';w.apply_theme();profile=parse_link('trojan://sample@example.invalid:443?security=tls#Sample');sub=Subscription('نمونهٔ نمایشی · حجم آزمایشی','https://example.invalid/sample');sub.metadata={'upload':5*1024**3,'download':30*1024**3,'total':100*1024**3};sub.updated_at='نمونه · دادهٔ آزمایشی';profile.name='نمونهٔ نمایشی · اشتراک';profile.subscription_id=sub.id;w.profiles=[profile];w.subscriptions=[sub];w.selected=profile.id;w.refresh_profile();app.processEvents();w.grab().save(str(out/'quota-sample-home.png'))
 w.navigate(3);w.settings_page.open_category(7);app.processEvents();w.grab().save(str(out/'quota-sample-settings.png'))
 w.close();app.processEvents()
print('Shadow Box screenshots rendered at compact fixed window size.')
