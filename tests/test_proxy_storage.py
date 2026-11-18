import json,pathlib,pytest
from nextapp.proxy import ProxyLease,ProxyError
from nextapp.profiles import parse_link
from nextapp.storage import Store,protect
from nextapp.migration import migrate

class FakeWinInet:
    def __init__(self):self.value={'flags':13,'server':'corporate:8080','bypass':'*.local','auto_url':'https://example.invalid/proxy.pac'};self.writes=[]
    def read(self):return dict(self.value)
    def write(self,settings):self.value=dict(settings);self.writes.append(dict(settings))

def test_backup_and_exact_restore(tmp_path):
    api=FakeWinInet();old=api.read();lease=ProxyLease(tmp_path,api);lease.enable(2080)
    assert lease.path.exists() and api.read()!=old
    lease.restore();assert api.read()==old and not lease.path.exists()

def test_concurrent_changes_never_overwritten(tmp_path):
    api=FakeWinInet();lease=ProxyLease(tmp_path,api);lease.enable(2080);api.value['server']='different:9090';current=api.read()
    with pytest.raises(ProxyError):lease.restore()
    assert api.read()==current and lease.path.exists()

def test_crash_recovery_new_manager(tmp_path):
    api=FakeWinInet();before=api.read();ProxyLease(tmp_path,api).enable(2080)
    ProxyLease(tmp_path,api).restore();assert api.read()==before

def test_no_override_pending_backup(tmp_path):
    api=FakeWinInet();lease=ProxyLease(tmp_path,api);lease.enable(2080)
    with pytest.raises(ProxyError):lease.enable(3000)
    assert '2080' in api.value['server']

def test_store_roundtrip_and_backup(tmp_path):
    store=Store(tmp_path);p=parse_link('trojan://secret@example.com?security=tls#نام');store.save_profiles([p]);store.save_settings({'language':'fa'})
    assert store.load_profiles()[0].original==p.original
    assert store.load_settings()['language']=='fa'
    assert (store.backup()/'profiles.dat').is_file()

def test_migration_preserves_unknown_and_subscriptions(tmp_path):
    src=tmp_path/'old';(src/'profiles').mkdir(parents=True);(src/'groups').mkdir()
    raw={'type':'vless','bean':{'pass':'secret','futureEncryption':'mlkem-field'}}
    (src/'profiles/1.json').write_text(json.dumps(raw));(src/'groups/1.json').write_text('{"url":"https://example.invalid/secret-token"}')
    store=Store(tmp_path/'new');profiles,msg=migrate(src,store)
    assert profiles[0].raw==raw and profiles[0].protocol=='nekoray-json'
    import io,zipfile
    backup=next((store.root/'backups').glob('*.protected'))
    with zipfile.ZipFile(io.BytesIO(protect(backup.read_bytes(),True))) as z:
        assert 'secret-token' in z.read('groups/1.json').decode()
    assert json.loads((src/'profiles/1.json').read_text())==raw
