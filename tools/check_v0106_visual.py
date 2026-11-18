"""Offscreen geometry/compositor probe. Run separately per QT_SCALE_FACTOR."""
import os,sys,tempfile,pathlib
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
from PySide6.QtCore import Qt,QPoint,QEvent
from PySide6.QtWidgets import QApplication,QAbstractButton
from PySide6.QtTest import QTest
from nextapp import free_sources,service_checks
from nextapp.storage import Store
from nextapp.ui import Window
free_sources.install_presets=lambda *args:False
service_checks.ServiceChecks.start=lambda *args:None
Window.refresh_on_launch=lambda *args:None
app=QApplication([])
for language in ('en','fa'):
 for theme in ('Light','Dark','Apex'):
  with tempfile.TemporaryDirectory() as folder:
   Store(folder).save_settings({'language':language,'theme':theme,'settings_theme':'Light' if theme=='Apex' else theme,'dashboard_design':'glass-v1','apex_theme_version':1})
   w=Window(folder);w.show();w.latency_ms=807;w.render_ping();w.stat_values[3].setText('00:04:34');app.processEvents()
   assert w.ping_card.rect().contains(w.ping_button.geometry())
   assert w.ping_card.rect().contains(w.stat_values[3].geometry())
   assert not w.ping_button.geometry().intersects(w.stat_values[3].geometry())
   w.show_add_menu();QTest.qWait(20)
   assert all(b.isVisible() and b.graphicsEffect() is None for _,b in w.add_sheet_actions)
   assert all(b.graphicsEffect() is None for b in w.findChildren(QAbstractButton))
   w.hide_add_sheet();w.navigate(3);w.settings_page.open_category(14);app.processEvents()
   page=w.settings_page.traffic_page
   assert page.rows.width()<=page.width() and not w.settings_page.footer.isVisible()
   assert page.rows.height()>=6*40 and not page.grab().isNull()
   w.close();app.processEvents();app.sendPostedEvents(None,QEvent.DeferredDelete)
print('PASS',os.environ.get('QT_SCALE_FACTOR','1'),'scale / en+fa / Light+Dark+Apex / ping+sheet+usage')
