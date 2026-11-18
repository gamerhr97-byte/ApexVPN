"""Capture every actual native Settings category, plus RTL / light / scaling."""
import os,pathlib,sys,tempfile,json,time
os.environ['QT_QPA_PLATFORM']='offscreen'
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
from PySide6.QtWidgets import QApplication
from nextapp.ui import Window
app=QApplication([]);out=pathlib.Path(__file__).resolve().parents[1]/'docs/screenshots/settings-v040';out.mkdir(parents=True,exist_ok=True)
with tempfile.TemporaryDirectory() as root:
    start=time.perf_counter();w=Window(root);w.show();app.processEvents();w.navigate(3);app.processEvents();startup_ms=(time.perf_counter()-start)*1000;timings=[]
    for i in range(12):
        t=time.perf_counter();w.settings_page.nav.setCurrentRow(i);app.processEvents();timings.append((time.perf_counter()-t)*1000);w.grab().save(str(out/f'{i+1:02}.png'))
    w.settings['settings_theme']='Light';w.settings_page.style();w.settings_page.nav.setCurrentRow(0);app.processEvents();w.grab().save(str(out/'light.png'))
    w.settings['language']='fa';w.settings['settings_theme']='Dark';w.current=3;w.rebuild();app.processEvents();w.grab().save(str(out/'persian.png'))
    w.settings['text_scale']=125;w.settings_page.style();app.processEvents();w.grab().save(str(out/'text-125.png'))
    (out/'measurements.json').write_text(json.dumps({'environment':'Linux Qt offscreen, not Windows benchmark','category_navigation_ms':timings,'startup_to_settings_ms':startup_ms},indent=2));w.close();app.processEvents()
print('12 Settings categories + light, Persian RTL and 125% text screenshots generated.')
