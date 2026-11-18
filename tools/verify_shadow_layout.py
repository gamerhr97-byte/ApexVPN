"""Compare key dashboard geometry to an extracted 0.4.0 source tree."""
import argparse,json,pathlib,os,subprocess,sys
root=pathlib.Path(__file__).resolve().parents[1];parser=argparse.ArgumentParser();parser.add_argument('--baseline',type=pathlib.Path,required=True);args=parser.parse_args()
script='''import json,tempfile
from PySide6.QtCore import QPoint
from PySide6.QtWidgets import QApplication
from nextapp.ui import Window
app=QApplication([])
with tempfile.TemporaryDirectory() as root:
 w=Window(root);w.show();app.processEvents()
 items={'power':w.power,'server':w.profile_name.parentWidget(),'ping':w.ping_button,'download':w.stat_values[0],'upload':w.stat_values[1],'connect':w.connect_button}
 result={key:[*item.mapTo(w,QPoint()).toTuple(),*item.size().toTuple()] for key,item in items.items()}
 print(json.dumps(result));w.close();app.processEvents()
'''
def capture(directory):
 result=subprocess.run([sys.executable,'-c',script],cwd=directory,env={**os.environ,'QT_QPA_PLATFORM':'offscreen'},text=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE,check=True)
 return json.loads(result.stdout.strip().splitlines()[-1])
before=capture(args.baseline.resolve());after=capture(root);report={'baseline':'0.4.0','current':'Shadow Box 0.5.0','geometry_identical':before==after,'before':before,'after':after};assert before==after,report
(root/'docs/shadow-layout-audit.json').write_text(json.dumps(report,indent=2));print(json.dumps(report))
