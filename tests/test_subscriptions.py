import json,pytest
from nextapp.profiles import parse_link,ProfileError
from nextapp.subscriptions import Subscription,reconcile
from nextapp.storage import Store

def profile(name,source=''):
    p=parse_link('trojan://test-'+name+'@example.com:443?security=tls#'+name);p.subscription_id=source;return p

def test_refresh_only_replaces_own_group_and_preserves_state():
    kept=profile('manual');other=profile('another','other');old=profile('same','sub');old.favorite=True;old.latency=25
    stale=profile('removed','sub');new=profile('new')
    current=[kept,other,old,stale]
    result,selected=reconcile(current,[profile('same'),new,new],'sub',old.id)
    assert [p.name for p in result]==['manual','another','same','new']
    assert result[2].id==old.id and result[2].favorite and result[2].latency==25
    assert selected==old.id and len(current)==4
    assert new.subscription_id=='' # no caller mutation before durable save

def test_removed_selection_moves_to_valid_profile():
    old=profile('stale','sub');incoming=profile('new')
    result,selected=reconcile([old],[incoming],'sub',old.id)
    assert selected==result[0].id
    with pytest.raises(ProfileError):reconcile([old],[],'sub',old.id)

def test_old_profile_file_upgrades_and_retains_subscription_urls(tmp_path):
    store=Store(tmp_path);p=profile('local')
    (tmp_path/'profiles.dat').write_bytes(b'JSON1\n'+json.dumps([p.to_dict()]).encode())
    assert store.load_profiles()[0].id==p.id and not store.load_subscriptions()
    sub=Subscription('Personal','https://example.invalid/private-token')
    store.save_catalog([p],[sub]);store.save_profiles([p])
    assert store.load_subscriptions()[0].url==sub.url
    assert (store.backup()/'profiles.dat').is_file()

def test_atomic_failure_keeps_previous_catalog(tmp_path,monkeypatch):
    store=Store(tmp_path);p=profile('old','sub');sub=Subscription('Original','https://example.invalid/token',id='sub');store.save_catalog([p],[sub])
    before=(tmp_path/'profiles.dat').read_bytes()
    import nextapp.storage as storage
    monkeypatch.setattr(storage.os,'replace',lambda *args:(_ for _ in ()).throw(OSError('disk failure')))
    with pytest.raises(OSError):store.save_catalog([profile('new','sub')],[sub])
    assert (tmp_path/'profiles.dat').read_bytes()==before
