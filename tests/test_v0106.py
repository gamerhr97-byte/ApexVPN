import copy,threading
from pathlib import Path
from types import SimpleNamespace
import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication,QComboBox,QMessageBox,QListWidget
from nextapp.free_sources import install_presets as seed,repair_ownership,PRESETS
from nextapp.subscriptions import Subscription
from nextapp.profiles import Profile
from nextapp.ranking import rank
from nextapp.settings_schema import migrate,defaults
from nextapp.ui import Window


def test_builtin_and_personal_url_identity_are_independent():
    url=PRESETS[0][2];personal=Subscription('my own',url,is_free=True,source_key='proxycollector')
    sub=[personal];settings={};assert repair_ownership(sub,[])
    assert not personal.is_free and personal.source_key==''
    assert seed(sub,settings) and len(sub)==5 and sum(s.is_free for s in sub)==4
    builtin=next(s for s in sub if s.id=='builtin-free-proxycollector')
    builtin.url='https://custom.invalid/feed'
    p=Profile('kept','ss','localhost',443,subscription_id=builtin.id)
    repair_ownership(sub,[p])
    assert builtin.url==url and p.subscription_id!=builtin.id
    assert next(s for s in sub if s.id==p.subscription_id).url=='https://custom.invalid/feed'


def test_free_tcp_screen_skips_expensive_failures_but_keeps_udp(monkeypatch):
    from nextapp import group_testing as group
    from nextapp.profile_testing import ProfileTest
    items=[Profile('dead','ss','localhost',1),Profile('live','ss','localhost',2),Profile('udp','hysteria2','localhost',3),Profile('private','ss','localhost',4)]
    https=[];tcp=[];results=[]
    def quick(p,*args):
        tcp.append(p.id);return ProfileTest('TCP','Refused' if p.port==1 else 'Reachable',code='TCP_REFUSED' if p.port==1 else '')
    def tls(p,*args):https.append(p.id);return ProfileTest('HTTPS','Verified',1)
    monkeypatch.setattr(group,'test_tcp',quick);monkeypatch.setattr(group,'test_https',tls)
    settings=dict(defaults(),free_profile_ids={p.id for p in items[:3]})
    group.run_group(items,'HTTPS',settings,threading.Event(),lambda ident:None,lambda ident,result:results.append((ident,result)))
    assert set(tcp)=={p.id for p in items[:2]}
    assert set(https)=={p.id for p in items[1:]} and len(results)==4


def test_badge_threshold_and_theme_migration():
    for score in (0,75,89,90,100):
        p=Profile('fixture','ss','localhost',1,service_score=score)
        assert rank(p)[0]==-(int(score>=90))
    upgraded=migrate({'theme':'Light'});assert upgraded['theme']=='Apex'
    assert migrate(dict(upgraded,theme='Light'))['theme']=='Light'
    assert migrate(dict(upgraded,theme='Dark'))['theme']=='Dark'
    assert migrate({'apex_theme_version':1,'shadow_window':[410,610]})['shadow_window']==[410,610]


def test_subscription_navigation_and_clear_free_keeps_catalog(tmp_path,monkeypatch):
    from nextapp import free_sources,catalog_actions
    monkeypatch.setattr(free_sources,'install_presets',seed)
    app=QApplication.instance() or QApplication([]);w=Window(tmp_path);w.show()
    try:
        builtin=w.subscriptions[0];p=Profile('free-node','ss','localhost',1,subscription_id=builtin.id);w.profiles=[p];w.populate()
        w.navigate(1);picker=w.servers_page.groups
        assert not isinstance(picker,QComboBox)
        picker.showPopup();app.processEvents();assert w.current==4 and w.stack.currentWidget() is picker.sheet
        picker.sheet.reject();w.servers_page.select_group(builtin.id)
        monkeypatch.setattr(QMessageBox,'question',lambda *a,**k:QMessageBox.Yes)
        catalog_actions.subscription_action(w,'remove')
        assert any(s.id==builtin.id and s.is_free for s in w.subscriptions) and not w.profiles
        assert w.size().toTuple()==(410,610) and w.windowFlags() & Qt.FramelessWindowHint
    finally:w.close();app.processEvents()


def test_manual_source_matching_free_url_is_not_reclassified(tmp_path,monkeypatch):
    from nextapp import free_sources
    monkeypatch.setattr(free_sources,'install_presets',seed)
    app=QApplication.instance() or QApplication([]);w=Window(tmp_path)
    captured=[];monkeypatch.setattr(w.pool,'submit',lambda fn:captured.append(fn))
    try:
        w.servers_page.select_group('free')
        from nextapp import ui
        monkeypatch.setattr(ui,'fetch_subscription',lambda *a,**k:'trojan://local@localhost:443?security=tls')
        results=[];w.bridge.subscription_ready.connect(results.append)
        w.start_subscriptions([Subscription('personal copy',PRESETS[0][2])]);captured[0]();app.processEvents()
        result=results[0]['subscription'];assert not result.is_free and result.id!='builtin-free-proxycollector'
        assert w.servers_page.group==result.id
    finally:w.close();app.processEvents()
