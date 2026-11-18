"""Development-host measurement only. Never a Windows performance certification."""
import json,os,pathlib,resource,sys,time
os.environ['QT_QPA_PLATFORM']='offscreen'
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
start=time.perf_counter()
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer
from nextapp.ui import Window
import tempfile
app=QApplication([]);tmp=tempfile.TemporaryDirectory();w=Window(tmp.name);w.show();app.processEvents();startup=time.perf_counter()-start
before_cpu=time.process_time();before_wall=time.monotonic()
def finish():
    wall=time.monotonic()-before_wall;cpu=time.process_time()-before_cpu
    print(json.dumps({'host':'Linux x86_64; Qt offscreen; empty profiles; networking core stopped','import_to_first_render_seconds':round(startup,4),'idle_window_seconds':round(wall,3),'idle_cpu_seconds':round(cpu,5),'idle_one_core_cpu_percent':round(cpu/wall*100,3),'peak_rss_mib':round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024,2)},indent=2))
    w.close()
QTimer.singleShot(5000,finish);app.exec();tmp.cleanup()
