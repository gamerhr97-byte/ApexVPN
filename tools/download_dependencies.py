"""Fetch exact upstream release files and wheels, verifying pinned SHA256 values."""
import argparse,hashlib,json,pathlib,urllib.request
P=pathlib.Path(__file__).resolve().parents[1]

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--destination',type=pathlib.Path,default=P/'downloads');args=parser.parse_args();args.destination.mkdir(parents=True,exist_ok=True)
    manifest=json.loads((P/'dependencies.lock.json').read_text())
    for name,expected in manifest['sha256'].items():
        dest=args.destination/name
        if dest.exists() and hashlib.sha256(dest.read_bytes()).hexdigest()==expected:print('Verified',name);continue
        if name.startswith('Xray-'):url='https://github.com/XTLS/Xray-core/releases/download/v'+manifest['Xray']+'/'+name
        elif name.startswith('python-'):url='https://www.python.org/ftp/python/3.13.9/'+name
        else:
            if name.lower().startswith('pyyaml'):package,version='PyYAML','6.0.2'
            elif name.startswith('zxing_cpp'):package,version='zxing-cpp','2.3.0'
            elif name.startswith('pillow'):package,version='Pillow','11.1.0'
            else:package,version=('shiboken6' if name.startswith('shiboken6') else 'PySide6-Essentials'),'6.8.3'
            with urllib.request.urlopen(f'https://pypi.org/pypi/{package}/{version}/json',timeout=30) as response:metadata=json.load(response)
            url=next(item['url'] for item in metadata['urls'] if item['filename']==name)
        temporary=dest.with_name(name+'.partial')
        try:
            urllib.request.urlretrieve(url,temporary)
            if hashlib.sha256(temporary.read_bytes()).hexdigest()!=expected:raise RuntimeError('Checksum verification failed: '+name)
            temporary.replace(dest);print('Downloaded and verified',name)
        finally:temporary.unlink(missing_ok=True)
if __name__=='__main__':main()
