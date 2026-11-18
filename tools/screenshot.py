import os,pathlib,sys,tempfile
os.environ['QT_QPA_PLATFORM']='offscreen'
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
from PySide6.QtWidgets import QApplication
from nextapp.ui import Window
app=QApplication([]);root=tempfile.TemporaryDirectory();w=Window(root.name);w.show();app.processEvents()
out=pathlib.Path(__file__).resolve().parents[1]/'docs/screenshots';out.mkdir(parents=True,exist_ok=True)
for i,name in enumerate(('overview','servers','diagnostics','settings')):
 w.navigate(i);app.processEvents();w.grab().save(str(out/(name+'.png')))
w.settings['language']='fa';w.current=0;w.rebuild();app.processEvents();w.grab().save(str(out/'persian.png'))
w.settings['language']='en';w.settings['theme']='Light';w.rebuild();app.processEvents();w.grab().save(str(out/'light.png'))
w.settings['theme']='Dark';w.rebuild();app.processEvents();w.grab().save(str(out/'dark.png'));w.close();root.cleanup()
print('Seven native Qt screenshots written.')
