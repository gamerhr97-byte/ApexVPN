"""Backup-first migration. Unsupported original profiles are retained, never guessed."""
import datetime,io,json,pathlib,zipfile
from urllib.parse import quote,urlencode
from .profiles import Profile,parse_link,Unsupported,ProfileError
from .storage import protect,atomic_write

def convert(data):
    bean=data.get('bean',{});kind=str(data.get('type','')).lower()
    # Only convert the exact basic SS schema. Advanced or unknown values stay archived.
    if kind in ('shadowsocks','ss'):
        allowed={'_v','name','addr','port','c_cfg','c_out','method','pass','plugin','uot','stream'}
        st=bean.get('stream',{})
        if set(bean)-allowed or bean.get('plugin') or bean.get('uot') or bean.get('c_cfg') or bean.get('c_out') or any(v for k,v in st.items() if k not in ('net','sec')) or st.get('net','tcp')!='tcp' or st.get('sec'):
            raise Unsupported('Advanced legacy Shadowsocks settings need manual review.')
        link='ss://'+quote(bean['method']+':'+bean['pass'],safe='')+'@'+('['+bean['addr']+']' if ':' in bean['addr'] else bean['addr'])+':'+str(bean['port'])+'#'+quote(bean.get('name','Migrated Shadowsocks'))
        return parse_link(link)
    # Generic retention prevents lossy conversion of legacy custom settings.
    return Profile(bean.get('name') or 'Legacy profile — review required','nekoray-json','',0,original=json.dumps(data,ensure_ascii=False),raw=data)

def migrate(source,store):
    source=pathlib.Path(source).resolve()
    if not (source/'profiles').is_dir():raise ProfileError('Select a NekoRay config directory containing profiles/.')
    if source==store.root.resolve() or source.is_relative_to(store.root.resolve()):raise ProfileError('Select the original NekoRay directory, not the new app data directory.')
    files=[];total=0
    for p in source.rglob('*'):
        if p.is_symlink():raise ProfileError('Migration refuses symbolic links. Original data was not changed.')
        if p.is_file() and p.suffix.lower() in ('.json','.txt','.conf','.ini'):
            total+=p.stat().st_size
            if total>64*1024*1024:raise ProfileError('Configuration backup exceeds 64 MiB; select the configuration folder only.')
            files.append(p)
    buf=io.BytesIO()
    with zipfile.ZipFile(buf,'w',zipfile.ZIP_DEFLATED) as z:
        for p in files:z.write(p,p.relative_to(source))
    backup=store.root/'backups'/('nekoray-'+datetime.datetime.now().strftime('%Y%m%d-%H%M%S-%f')+'.zip.protected')
    # DPAPI on Windows; 0600 on Linux. Includes groups and subscription URLs, unchanged.
    atomic_write(backup,protect(buf.getvalue()))
    profiles=[];retained=0
    for p in sorted((source/'profiles').glob('*.json')):
        try:
            raw=p.read_text(encoding='utf-8-sig');d=json.loads(raw)
            try:new=convert(d)
            except Exception:new=Profile('Legacy profile — review required','nekoray-json','',0,original=raw,raw=d)
            if new.protocol=='nekoray-json':retained+=1
            profiles.append(new)
        except Exception:retained+=1 # exact bytes still in backup
    return profiles,f'legacy migration complete. {retained} entries require manual review; all source configuration and subscription data were backed up. The original directory was not changed.'
