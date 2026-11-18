import pathlib,time,socket
import pytest
from PySide6.QtCore import Qt,QPoint,QPointF
from PySide6.QtGui import QWheelEvent
from PySide6.QtWidgets import QApplication
from nextapp.ui import Window
from nextapp.profiles import parse_link
from nextapp.subscriptions import Subscription,reconcile
from nextapp.profile_testing import ProfileTest,result_text,test_tcp as run_tcp
from nextapp.settings_policy import auto_candidate,effective_settings
from nextapp.settings_schema import defaults


def app():return QApplication.instance() or QApplication([])
def wait_for(condition,seconds=2):
    end=time.monotonic()+seconds
    while not condition() and time.monotonic()<end:app().processEvents();time.sleep(.01)
    assert condition()

def profile(name='one'):return parse_link('trojan://test@example.invalid:443?security=tls#'+name)

def test_grouped_subscriptions_never_mix_and_show_selected_quota(tmp_path):
    a=app();w=Window(tmp_path)
    try:
        w.show();original_size=w.size();first=Subscription('First','https://example.invalid/a');second=Subscription('Second','https://example.invalid/b');first.metadata={'upload':5,'download':20,'total':100};second.metadata={'upload':10,'download':60,'total':100}
        p1,p2=profile('First server'),profile('Second server');p1.subscription_id=first.id;p2.subscription_id=second.id;w.subscriptions=[first,second];w.profiles=[p1,p2];w.populate();w.navigate(1);a.processEvents();assert w.size()==original_size
        page=w.servers_page;page.select_group(first.id);assert w.table.rowCount()==1 and w.table.item(0,0).data(Qt.UserRole)==p1.id and page.quota.value()==250
        page.select_group(second.id);assert w.table.rowCount()==1 and w.table.item(0,0).data(Qt.UserRole)==p2.id and page.quota.value()==700
        assert w.table.columnCount()==2
        second.metadata={};page.refresh_quota();assert not page.quota.isEnabled() and 'not supplied' in page.quota_note.text()
    finally:w.close();a.processEvents()

def test_failed_test_is_persisted_and_never_not_tested(tmp_path):
    a=app();w=Window(tmp_path)
    try:
        p=profile();w.profiles=[p];w.populate();w.profile_test_received(p.id,ProfileTest('TCP','Timeout',code='TIMEOUT'));w.profile_tests_finished()
        assert w.table.item(0,1).text()=='Timeout' and result_text(p)=='Timeout'
        restored=w.store.load_profiles()[0];assert restored.test_status=='Timeout' and restored.test_method=='TCP'
        current,_=reconcile([restored],[profile()],p.subscription_id,p.id);assert current[0].test_status=='Timeout'
    finally:w.close();a.processEvents()

def test_real_tcp_refusal_and_exception_timeout(monkeypatch):
    p=profile()
    with socket.socket() as s:s.bind(('127.0.0.1',0));p.host='127.0.0.1';p.port=s.getsockname()[1]
    assert run_tcp(p,.2).status=='Refused'
    import nextapp.profile_testing as module
    monkeypatch.setattr(module,'tcp_latency',lambda *args:(_ for _ in ()).throw(TimeoutError()))
    assert run_tcp(p,.2).status=='Timeout'
    p.tested_at='2026-10-21';p.latency=None;p.test_status='';assert result_text(p)=='Failed'

def test_settings_icons_hidden_scrollbars_and_real_wheel(tmp_path):
    a=app();w=Window(tmp_path)
    try:
        w.show();w.resize(420,660);w.navigate(3);page=w.settings_page;a.processEvents()
        assert all(not page.nav.item(i).icon().isNull() for i in range(14))
        assert page.nav.verticalScrollBarPolicy()==Qt.ScrollBarAlwaysOff
        page.open_category(10)
        for i,toggle,body in page.groups:
            if i==10:toggle.setChecked(True)
        a.processEvents();scroll=page.stack.currentWidget();a.processEvents();assert scroll.verticalScrollBarPolicy()==Qt.ScrollBarAlwaysOff and scroll.verticalScrollBar().maximum()>0
        before=scroll.verticalScrollBar().value();event=QWheelEvent(QPointF(100,100),QPointF(100,100),QPoint(),QPoint(0,-120),Qt.NoButton,Qt.NoModifier,Qt.ScrollUpdate,False);a.sendEvent(scroll.viewport(),event);a.processEvents()
        assert scroll.verticalScrollBar().value()>before
    finally:w.close();a.processEvents()

def test_safe_autosave_preserves_network_draft_and_toggle(tmp_path):
    a=app();w=Window(tmp_path)
    try:
        w.show();w.navigate(3);page=w.settings_page;old_port=w.settings['http_port'];page.controls['http_port'].setValue(2233);page.controls['theme'].setCurrentIndex(page.controls['theme'].findData('Dark'))
        wait_for(lambda:w.settings['theme']=='Dark')
        assert w.store.load_settings()['http_port']==old_port and page.controls['http_port'].value()==2233 and page.dirty
        page.controls['auto_save'].setChecked(False);wait_for(lambda:not w.settings['auto_save']);page.controls['theme'].setCurrentIndex(page.controls['theme'].findData('Light'));deadline=time.monotonic()+.6
        while time.monotonic()<deadline:a.processEvents();time.sleep(.01)
        assert w.settings['theme']=='Dark'
    finally:w.close();a.processEvents()

def test_autosave_excludes_critical_keys_and_automatic_tuning_is_real():
    current=defaults();draft={'theme':'Dark','http_port':4444,'launch_startup':True}
    candidate,changed=auto_candidate(current,draft);assert changed=={'theme'} and candidate['http_port']==current['http_port'] and not candidate['launch_startup']
    current.update(automatic_tuning=True,retry_attempts=8,health_timeout=30,concurrency=16)
    effective=effective_settings(current);assert effective['retry_attempts']==3 and effective['health_timeout']==8 and effective['concurrency']<=4
    current['automatic_tuning']=False;assert effective_settings(current)['retry_attempts']==8

def test_import_or_reset_does_not_autocommit_a_batch(tmp_path):
    a=app();w=Window(tmp_path)
    try:
        w.show();w.navigate(3);page=w.settings_page;values=page.values();values['theme']='Dark';page.load_values(values);page.autosave();assert w.settings['theme']=='Apex' and page.staging_batch
    finally:w.close();a.processEvents()

def test_ten_service_tiles_and_stale_results_cannot_change_session(tmp_path):
    from nextapp.service_checks import ServiceResult
    a=app();w=Window(tmp_path)
    try:
        assert len(w.service_buttons)==100 and 'chatgpt' in w.service_buttons and 'github' in w.service_buttons
        controller=w.service_checks;old=object();controller.deliver((controller.generation,old,ServiceResult('youtube','ok',23,200)))
        assert w.service_buttons['youtube'].value is None
        w.engine.running=True;w.engine.process=object();controller.route='proxy';controller.deliver((controller.generation,w.engine.process,'proxy',ServiceResult('youtube','ok',23,200)));assert w.service_buttons['youtube'].value.state=='ok'
        controller.cancel();controller.deliver((controller.generation-1,w.engine.process,ServiceResult('youtube','ok',22,200)));assert w.service_buttons['youtube'].value is None
        w.engine.process=None;w.engine.running=False
    finally:w.engine.process=None;w.engine.running=False;w.close();a.processEvents()

def test_subscription_group_restores_selected_source_after_restart(tmp_path):
    a=app();w=Window(tmp_path)
    first=Subscription('First','https://example.invalid/first');second=Subscription('Second','https://example.invalid/second');p1,p2=profile('one'),profile('two');p1.subscription_id=first.id;p2.subscription_id=second.id
    try:
        w.profiles=[p1,p2];w.subscriptions=[first,second];w.selected=p2.id;w.store.save_catalog(w.profiles,w.subscriptions)
    finally:w.close();a.processEvents()
    restored=Window(tmp_path)
    try:
        assert restored.servers_page.group==second.id and restored.table.rowCount()==1 and restored.table.item(0,0).data(Qt.UserRole)==p2.id
    finally:restored.close();a.processEvents()

def test_safe_autosave_flushes_when_closing_before_debounce(tmp_path):
    a=app();w=Window(tmp_path);w.show();w.navigate(3);page=w.settings_page;page.controls['theme'].setCurrentIndex(page.controls['theme'].findData('Dark'));assert page.auto_timer.isActive();w.close();a.processEvents()
    assert w.store.load_settings()['theme']=='Dark'
