"""Assemble portable Windows x64 app from exact, hash-pinned upstream artifacts.
Run from project root: python tools/package_windows.py --downloads ../downloads
No installer, network driver, shell commands or elevation. Settings has an explicit pinned core downloader.
"""
import argparse,hashlib,json,pathlib,shutil,subprocess,sys,zipfile
P=pathlib.Path(__file__).resolve().parents[1]

def build(downloads,destination):
    manifest=json.loads((P/'dependencies.lock.json').read_text())
    names=['python-3.13.9-embed-amd64.zip','PySide6_Essentials-6.8.3-cp39-abi3-win_amd64.whl','shiboken6-6.8.3-cp39-abi3-win_amd64.whl','Xray-windows-64.zip','zxing_cpp-2.3.0-cp313-cp313-win_amd64.whl','pillow-11.1.0-cp313-cp313-win_amd64.whl','PyYAML-6.0.2-cp313-cp313-win_amd64.whl']
    for name in names:
        path=downloads/name
        if hashlib.sha256(path.read_bytes()).hexdigest()!=manifest['sha256'][name]:raise ValueError('Dependency checksum mismatch: '+name)
    out=destination/'NekoRayNext';out.mkdir(parents=True,exist_ok=True)
    runtime=out/'runtime';runtime.mkdir(exist_ok=True)
    for name in names[:3]+names[4:]:
        with zipfile.ZipFile(downloads/name) as z:
            for n in z.namelist():
                if '..' in pathlib.PurePosixPath(n).parts or n.startswith('/'):raise ValueError('Unsafe dependency archive')
            z.extractall(runtime)
    (runtime/'python313._pth').write_text('python313.zip\n.\n..\n',encoding='ascii')
    # Keep upstream Qt package intact, including license metadata and optional Qt modules.
    core=out/'core';core.mkdir(exist_ok=True)
    with zipfile.ZipFile(downloads/names[3]) as z:
        for name in ('xray.exe','LICENSE','README.md'):z.extract(name,core)
    aux=json.loads((P/'sing-box.lock.json').read_text())['windows']
    if hashlib.sha256((P/'core/sing-box.exe').read_bytes()).hexdigest()!=aux['binary_sha256']:raise ValueError('sing-box executable checksum mismatch')
    shutil.copy2(P/'core/sing-box.exe',core/'sing-box.exe')
    shutil.copy2(P/'sing-box.lock.json',out/'sing-box.lock.json')
    for name in ('nextapp','docs','licenses','tests','tools','assets'):
        shutil.copytree(P/name,out/name,dirs_exist_ok=True,ignore=shutil.ignore_patterns('__pycache__','*.pyc','*.res','*.exe'))
    for name in ('app.py','README.md','LICENSE','THIRD_PARTY_NOTICES.md','dependencies.lock.json','requirements.txt','requirements-dev.txt'):
        shutil.copy2(P/name,out/name)
    (out/'portable.flag').write_text('Data stays in the data folder. Protected to the Windows account using DPAPI.\n')
    exe=P/'tools/ApexVPN.exe'
    subprocess.run([sys.executable,str(P/'tools/build_launcher.py')],check=True)
    shutil.copy2(exe,out/'ApexVPN.exe')
    shutil.copy2(exe,out/'ApexVPN-0.10.7.exe')
    shutil.copy2(P/'tools/ApexVPNHost.exe',runtime/'ApexVPNHost.exe')
    (runtime/'ApexVPNHost._pth').write_text('python313.zip\n.\n..\n',encoding='ascii')
    # Existing shortcuts keep working after a rename/update.
    shutil.copy2(exe,out/'NekoRayNext.exe')
    shutil.copy2(exe,out/'ShadowBox.exe')
    (core/'runtime-hashes.json').write_text(json.dumps({p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (core/'xray.exe',core/'sing-box.exe')}))
    for path in P.glob('*.md'):shutil.copy2(path,out/path.name)
    archive=destination/'ApexVPN-0.10.7-windows-x64-portable.zip'
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for path in sorted(out.rglob('*')):
            if path.is_file() and '__pycache__' not in path.parts and not any(part.startswith('.') for part in path.relative_to(out).parts):z.write(path,path.relative_to(destination))
    print(archive,archive.stat().st_size)

if __name__=='__main__':
    a=argparse.ArgumentParser();a.add_argument('--downloads',type=pathlib.Path,required=True);a.add_argument('--output',type=pathlib.Path,default=P.parent/'deliverables');s=a.parse_args();s.output.mkdir(parents=True,exist_ok=True);build(s.downloads.resolve(),s.output.resolve())
