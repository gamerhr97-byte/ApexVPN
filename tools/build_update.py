"""Build the small in-place 1.11.0 quick-update EXE; never package a full runtime."""
from pathlib import Path
import shutil,subprocess

ROOT=Path(__file__).resolve().parents[1]
FILES=('__init__.py','branding.py','ui.py','server_page.py','service_icons.py','catalog_actions.py','i18n.py','free_sources.py','settings_schema.py','presentation.py','settings_ui.py','window_chrome.py','release_notes.py','feedback.py','traffic_page.py','iconography.py','effects.py','service_checks.py')

def build(output,compiler):
    output=Path(output).resolve();payload=output.parent/'update-payload'
    if payload.exists():shutil.rmtree(payload)
    (payload/'nextapp').mkdir(parents=True)
    for name in FILES:shutil.copy2(ROOT/'nextapp'/name,payload/'nextapp'/name)
    for name in ('ApexVPN.exe','ApexVPN-0.10.7.exe','ShadowBox.exe','NekoRayNext.exe'):
        shutil.copy2(ROOT/'tools'/name,payload/name)
    (payload/'runtime').mkdir(parents=True,exist_ok=True)
    shutil.copy2(ROOT/'tools/ApexVPNHost.exe',payload/'runtime/ApexVPNHost.exe')
    output.parent.mkdir(parents=True,exist_ok=True)
    subprocess.run([compiler,'-V2','-DPAYLOAD='+str(payload),'-DOUTPUT='+str(output),str(ROOT/'tools/update_only.nsi')],check=True)
    print(output,output.stat().st_size)

if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser();parser.add_argument('--output',required=True,type=Path);parser.add_argument('--makensis',default='makensis');args=parser.parse_args()
    build(args.output,args.makensis)
