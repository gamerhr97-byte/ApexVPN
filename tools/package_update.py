"""Application overlay, branded native Python host and optional QR runtime dependencies.
Launchers/host are replaced; existing Python/Qt/core libraries and data are preserved.
Use --code-only for updates from modern 0.7.0 or 0.8.0 (QR dependencies already bundled).
"""
import pathlib,zipfile,argparse,json,hashlib
root=pathlib.Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser();p.add_argument('--output',type=pathlib.Path,required=True);p.add_argument('--downloads',type=pathlib.Path,default=root.parent/'downloads');p.add_argument('--code-only',action='store_true',help='Requires modern 0.7.0 runtime; no native dependencies replaced');a=p.parse_args();a.output.parent.mkdir(parents=True,exist_ok=True)
manifest=json.loads((root/'dependencies.lock.json').read_text())
wheels=[] if a.code_only else ['zxing_cpp-2.3.0-cp313-cp313-win_amd64.whl','pillow-11.1.0-cp313-cp313-win_amd64.whl']
for name in wheels:
 if hashlib.sha256((a.downloads/name).read_bytes()).hexdigest()!=manifest['sha256'][name]:raise SystemExit('QR dependency checksum failed: '+name)
files=[root/n for n in ('app.py','README.md','LICENSE','THIRD_PARTY_NOTICES.md','dependencies.lock.json','requirements.txt')]
for folder in ('nextapp','docs','licenses','assets'):
 files.extend(f for f in (root/folder).rglob('*') if (not a.code_only or folder!='docs' or f.name in {'VALIDATION-0.10.7-FA.md','TEST_RESULTS.md'}) and f.is_file() and '__pycache__' not in f.parts and f.suffix!='.pyc' and not any(part.startswith('.') for part in f.relative_to(root).parts))
with zipfile.ZipFile(a.output,'w',zipfile.ZIP_DEFLATED) as z:
 z.writestr('UPDATE-README-FA.txt',(root/'README-0.10.7-FA.md').read_text())
 for f in sorted(files):z.write(f,pathlib.Path('NekoRayNext')/f.relative_to(root))
 for name in ('ApexVPN.exe','ApexVPN-0.10.7.exe','ShadowBox.exe','NekoRayNext.exe'):z.write(root/'tools/ApexVPN.exe',pathlib.Path('NekoRayNext')/name)
 z.write(root/'tools/ApexVPNHost.exe','NekoRayNext/runtime/ApexVPNHost.exe')
 z.writestr('NekoRayNext/runtime/ApexVPNHost._pth','python313.zip\n.\n..\n')
 hashes={}
 for name in ('xray.exe','sing-box.exe'):
  payload=(root/'core'/name).read_bytes();hashes[name]=hashlib.sha256(payload).hexdigest();z.writestr('NekoRayNext/core/'+name,payload)
 z.writestr('NekoRayNext/core/runtime-hashes.json',json.dumps(hashes))
 z.write(root/'sing-box.lock.json','NekoRayNext/sing-box.lock.json')
 for name in wheels:
  with zipfile.ZipFile(a.downloads/name) as wheel:
   for entry in wheel.namelist():
    if '..' in pathlib.PurePosixPath(entry).parts or entry.startswith('/'):raise ValueError('Unsafe dependency archive')
    if not entry.endswith('/'):z.writestr('NekoRayNext/runtime/'+entry,wheel.read(entry))
print(a.output,a.output.stat().st_size)
