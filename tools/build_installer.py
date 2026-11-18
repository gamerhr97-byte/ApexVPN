"""Build NSIS only from the complete current portable payload, never stale files.
Use --payload with a verified full app directory, or --downloads to assemble it.
No runtime or signed driver is downloaded on the user's computer.
"""
import argparse,hashlib,json,pathlib,shutil,subprocess,sys
ROOT=pathlib.Path(__file__).resolve().parents[1]

def build(downloads,output,compiler,payload=None):
    output.mkdir(parents=True,exist_ok=True)
    if payload is None:
        from package_windows import build as build_portable
        build_portable(downloads,output/'portable-build');payload=output/'portable-build/NekoRayNext'
    stage=output/'installer-payload'
    if stage.exists():shutil.rmtree(stage)
    def ignore(directory,names):
        skipped={name for name in names if name=='__pycache__' or name.endswith('.pyc')}
        if pathlib.Path(directory).resolve()==pathlib.Path(payload).resolve():skipped.update({'data','portable.flag','tests','tools'})
        return skipped
    shutil.copytree(payload,stage,ignore=ignore)
    (stage/'installed.flag').write_text('Installed Apex VPN. User data lives in LocalAppData/NekoRayNext.\n')
    for old in stage.glob('ApexVPN-0.10.*.exe'):old.unlink()
    # Installed builds use the existing LocalAppData data root, not portable mode.
    for name in ('ApexVPN.exe','ShadowBox.exe','NekoRayNext.exe'):
        shutil.copy2(ROOT/'tools/ApexVPN.exe',stage/name)
    shutil.copy2(ROOT/'tools/ApexVPNHost.exe',stage/'runtime/ApexVPNHost.exe')
    required=('runtime/python313.dll','runtime/ApexVPNHost._pth','runtime/PySide6/Qt6Core.dll','core/xray.exe','core/sing-box.exe','assets/apex-vpn-0.10.7.png')
    for name in required:
        if not (stage/name).is_file():raise ValueError('Incomplete installer payload: '+name)
    paths=sorted(p for p in stage.rglob('*') if p.is_file());deletions=[]
    for path in paths:
        relative=str(path.relative_to(stage)).replace('/','\\').replace('$','$$');deletions.append(f'Delete "$INSTDIR\\{relative}"')
    for folder in sorted((p for p in stage.rglob('*') if p.is_dir()),key=lambda p:len(p.parts),reverse=True):
        relative=str(folder.relative_to(stage)).replace('/','\\').replace('$','$$');deletions.append(f'RMDir "$INSTDIR\\{relative}"')
    (ROOT/'tools/uninstall-files.nsh').write_text('\n'.join(deletions)+'\n')
    setup=output/'ApexVPN-0.10.7-Setup-x64.exe'
    subprocess.run([compiler,'-V2','-DPAYLOAD='+str(stage),'-DOUTPUT='+str(setup),str(ROOT/'tools/installer.nsi')],check=True)
    (output/'payload-sha256.json').write_text(json.dumps({str(p.relative_to(stage)):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths},indent=2))
    print(setup,setup.stat().st_size)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--downloads',type=pathlib.Path);parser.add_argument('--payload',type=pathlib.Path);parser.add_argument('--output',type=pathlib.Path,required=True);parser.add_argument('--makensis',default='makensis');args=parser.parse_args()
    if args.payload is None and args.downloads is None:parser.error('Use --payload or --downloads')
    build(args.downloads,args.output.resolve(),args.makensis,args.payload.resolve() if args.payload else None)
