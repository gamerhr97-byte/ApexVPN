"""Atomic writes and DPAPI protection. Never writes imported secrets to diagnostics."""
import base64, ctypes, json, os, pathlib, tempfile, shutil, datetime, hashlib
from collections import Counter

def atomic_write(path, data):
    path=pathlib.Path(path); path.parent.mkdir(parents=True,exist_ok=True)
    fd,tmp=tempfile.mkstemp(dir=path.parent, prefix='.next-')
    try:
        os.chmod(tmp,0o600)
        with os.fdopen(fd,'wb') as f: f.write(data); f.flush(); os.fsync(f.fileno())
        os.replace(tmp,path)
    finally:
        if os.path.exists(tmp): os.unlink(tmp)

def protect(data, decrypt=False):
    if os.name!='nt': return data
    from ctypes import wintypes
    class Blob(ctypes.Structure): _fields_=[('cbData',wintypes.DWORD),('pbData',ctypes.POINTER(ctypes.c_ubyte))]
    buf=ctypes.create_string_buffer(data); src=Blob(len(data),ctypes.cast(buf,ctypes.POINTER(ctypes.c_ubyte))); dst=Blob()
    if decrypt: ok=ctypes.windll.crypt32.CryptUnprotectData(ctypes.byref(src),None,None,None,None,1,ctypes.byref(dst))
    else: ok=ctypes.windll.crypt32.CryptProtectData(ctypes.byref(src),'NekoRay Next',None,None,None,1,ctypes.byref(dst))
    if not ok: raise OSError('Windows credential protection failed.')
    try: return ctypes.string_at(dst.pbData,dst.cbData)
    finally: ctypes.windll.kernel32.LocalFree(dst.pbData)

class Store:
    def __init__(self, root): self.root=pathlib.Path(root); self.root.mkdir(parents=True,exist_ok=True)
    def _load_catalog(self):
        path=self.root/'profiles.dat'
        if not path.exists():return {'profiles':[],'subscriptions':[]}
        magic,data=path.read_bytes().split(b'\n',1)
        if magic==b'DPAPI1':
            if os.name!='nt':raise OSError('These profiles require their original Windows user account.')
            data=protect(data,True)
        elif magic!=b'JSON1':raise OSError('Unknown profile storage format.')
        result=json.loads(data)
        if isinstance(result,list):return {'profiles':result,'subscriptions':[]}
        documents=result.get('source_documents',{})
        if not isinstance(documents,dict):raise OSError('Invalid source document catalog.')
        for digest,text in documents.items():
            if not isinstance(text,str) or hashlib.sha256(text.encode()).hexdigest()!=digest:
                raise OSError('Source document integrity check failed.')
        for profile in result.get('profiles',[]):
            reference=profile.pop('_original_document',None)
            if reference is not None:
                if reference not in documents:raise OSError('Source document reference is missing.')
                profile['original']=documents[reference]
        return result
    def save_catalog(self,profiles,subscriptions):
        # Multi-outbound YAML/JSON can share a large original source. Store it once,
        # inside the same protected atomic catalog, rather than N copies on disk.
        counts=Counter(p.original for p in profiles if len(p.original)>1024)
        documents={};references={}
        for text,count in counts.items():
            if count>1:
                digest=hashlib.sha256(text.encode()).hexdigest()
                documents[digest]=text;references[text]=digest
        entries=[]
        for profile in profiles:
            entry=profile.to_dict()
            if profile.original in references:
                entry['original']='';entry['_original_document']=references[profile.original]
            entries.append(entry)
        payload={'profiles':entries,'subscriptions':[s.to_dict() for s in subscriptions]}
        if documents:payload.update(catalog_version=2,source_documents=documents)
        data=json.dumps(payload,ensure_ascii=False).encode()
        atomic_write(self.root/'profiles.dat',b'DPAPI1\n'+protect(data) if os.name=='nt' else b'JSON1\n'+data)
    def save_profiles(self,profiles):
        self.save_catalog(profiles,self.load_subscriptions())
    def load_profiles(self):
        from .profiles import Profile
        return [Profile(**x) for x in self._load_catalog()['profiles']]
    def load_subscriptions(self):
        from .subscriptions import Subscription
        return [Subscription(**x) for x in self._load_catalog().get('subscriptions',[])]
    def save_settings(self, data): atomic_write(self.root/'settings.json',json.dumps(data,ensure_ascii=False).encode())
    def load_settings(self):
        p=self.root/'settings.json'; return json.loads(p.read_text(encoding='utf-8-sig')) if p.exists() else {}
    def backup(self):
        root=self.root/'backups'/datetime.datetime.now().strftime('%Y%m%d-%H%M%S-%f'); root.mkdir(parents=True)
        for name in ('profiles.dat','settings.json'):
            if (self.root/name).exists(): shutil.copy2(self.root/name,root/name)
        return root
