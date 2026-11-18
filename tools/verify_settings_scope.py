"""Compare protected page implementations and native screenshots to v0.3.1."""
import ast,hashlib,json,pathlib,subprocess,sys,tempfile,os
root=pathlib.Path(__file__).resolve().parents[1];baseline=root.parent/'deliverables-v0.3.1/NekoRayNext'
if not baseline.exists():raise SystemExit('Previous release is required for this audit.')
protected=['build_dashboard','build_servers','build_add_sheet','build_diagnostics']
def methods(path):
    tree=ast.parse(path.read_text());window=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='Window')
    return {n.name:ast.dump(n,include_attributes=False) for n in window.body if isinstance(n,ast.FunctionDef)}
before=methods(baseline/'nextapp/ui.py');after=methods(root/'nextapp/ui.py');assert all(before[n]==after[n] for n in protected)
assert (baseline/'nextapp/presentation.py').read_bytes()==(root/'nextapp/presentation.py').read_bytes()
with tempfile.TemporaryDirectory() as temp:
    hashes=[]
    for code,tag in [(baseline,'before'),(root,'after')]:
        script="""import sys,tempfile,pathlib
from PySide6.QtWidgets import QApplication
from nextapp.ui import Window
app=QApplication([])
with tempfile.TemporaryDirectory() as data:
 w=Window(data);w.show();app.processEvents()
 for page,name in [(0,'home'),(1,'servers'),(2,'diagnostics')]:
  w.navigate(page);app.processEvents();w.grab().save(str(pathlib.Path(sys.argv[1])/(sys.argv[2]+'-'+name+'.png')))
 w.close();app.processEvents()
"""
        subprocess.run([sys.executable,'-c',script,temp,tag],cwd=code,env={**os.environ,'QT_QPA_PLATFORM':'offscreen'},check=True,stdout=subprocess.DEVNULL)
    from PIL import Image,ImageChops
    results={}
    for name in ('home','servers','diagnostics'):
        a=Image.open(pathlib.Path(temp)/('before-'+name+'.png')).convert('RGB');b=Image.open(pathlib.Path(temp)/('after-'+name+'.png')).convert('RGB')
        equal=a.size==b.size and ImageChops.difference(a,b).getbbox() is None;results[name]={'size':a.size,'pixels_identical':equal};assert equal,name+' changed'
report={'protected_methods_identical':protected,'presentation_file_identical':True,'native_render_comparison':results}
(root/'docs/settings-scope-audit.json').write_text(json.dumps(report,indent=2));print(json.dumps(report))
