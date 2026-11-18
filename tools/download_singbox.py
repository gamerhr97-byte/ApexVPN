"""Download the exact locked auxiliary core; verify before extracting it."""
import hashlib,io,json,os,pathlib,tarfile,urllib.request,zipfile
ROOT=pathlib.Path(__file__).resolve().parents[1]
lock=json.loads((ROOT/'sing-box.lock.json').read_text())
platform='windows' if os.name=='nt' else 'linux'
record=lock[platform]
with urllib.request.urlopen(record['url'],timeout=120) as r:data=r.read(180*1024*1024)
if hashlib.sha256(data).hexdigest()!=record['sha256']:raise RuntimeError('sing-box archive checksum mismatch')
name='sing-box.exe' if platform=='windows' else 'sing-box'
if platform=='windows':
 with zipfile.ZipFile(io.BytesIO(data)) as z:payload=z.read(next(x for x in z.namelist() if x.endswith('/'+name)))
else:
 with tarfile.open(fileobj=io.BytesIO(data)) as z:payload=z.extractfile(next(x for x in z.getmembers() if x.name.endswith('/'+name))).read()
if hashlib.sha256(payload).hexdigest()!=record['binary_sha256']:raise RuntimeError('sing-box executable checksum mismatch')
target=ROOT/'core'/name;target.parent.mkdir(exist_ok=True);target.write_bytes(payload)
if platform=='linux':target.chmod(0o755)
print('Verified',target)
