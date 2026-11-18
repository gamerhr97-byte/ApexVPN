import json,pathlib,tempfile,types,wave
import pytest
from PySide6.QtCore import Qt,QPoint
from PySide6.QtWidgets import QApplication,QGraphicsDropShadowEffect
from nextapp.ui import Window
from nextapp.usage import subscription_usage
from nextapp.logbook import LogBook
from nextapp.subscriptions import Subscription
from nextapp.profiles import parse_link

def app():return QApplication.instance() or QApplication([])

@pytest.mark.parametrize('metadata',[{},None,{'total':0,'upload':0,'download':0},{'total':100,'download':4},{'total':True,'upload':0,'download':4},{'total':100,'upload':-1,'download':4},{'total':'100','upload':0,'download':4}])
def test_quota_never_guesses(metadata):assert not subscription_usage(metadata).known

def test_quota_is_provider_total_not_local_session():
    usage=subscription_usage({'total':1000,'upload':100,'download':250});assert usage.known and usage.percent==35 and usage.remaining==650
    over=subscription_usage({'total':100,'upload':50,'download':75});assert over.percent==125 and over.remaining==0

@pytest.mark.parametrize('width',[420,468,620,980])
def test_categories_and_every_section_keep_window_dimensions(tmp_path,width):
    a=app();w=Window(tmp_path)
    try:
        w.show();w.resize(width,740);a.processEvents();before=w.size();w.navigate(3);a.processEvents();p=w.settings_page
        assert w.size()==before and p.deck.currentIndex()==0 and p.nav.isVisible() and not p.stack.isVisible()
        assert p.nav.count()==15
        for i in range(15):
            p.open_category(i);a.processEvents();assert w.size()==before,(width,i,w.size())
            assert p.deck.currentIndex()==1 and p.stack.isVisible() and not p.nav.isVisible()
            assert p.stack.currentWidget().horizontalScrollBar().maximum()==0
            p.show_categories();a.processEvents();assert p.deck.currentIndex()==0 and w.size()==before
        w.navigate(0);a.processEvents();assert w.size()==before
    finally:w.close();a.processEvents()

def test_rtl_and_large_text_do_not_resize_settings(tmp_path):
    a=app();w=Window(tmp_path)
    try:
        w.settings.update(language='fa',text_scale=150);w.current=3;w.rebuild();w.show();w.resize(420,740);a.processEvents();size=w.size();p=w.settings_page
        assert p.layoutDirection()==Qt.RightToLeft
        for i in (0,2,7,10,12,13):p.open_category(i);a.processEvents();assert w.size()==size
    finally:w.close();a.processEvents()

def test_depth_preserves_dashboard_geometry_and_can_disable(tmp_path):
    a=app();w=Window(tmp_path)
    try:
        w.show();a.processEvents();widgets=[w.power,w.server_card,w.ping_button,*w.stat_values[:2]]
        before=[(x.mapTo(w,QPoint()).toTuple(),x.size().toTuple()) for x in widgets]
        assert isinstance(w.server_card.graphicsEffect(),QGraphicsDropShadowEffect)
        w.settings['visual_effects']=False;w.apply_theme();a.processEvents();after=[(x.mapTo(w,QPoint()).toTuple(),x.size().toTuple()) for x in widgets]
        assert before==after and w.server_card.graphicsEffect() is None
        w.settings['visual_effects']=True;w.settings['lightweight']=True;w.apply_theme();assert w.server_card.graphicsEffect() is None
    finally:w.close();a.processEvents()

def test_selected_subscription_bar_and_unknown_quota(tmp_path):
    a=app();w=Window(tmp_path)
    try:
        w.show();p=parse_link('trojan://test@example.invalid:443?security=tls');sub=Subscription('test','https://example.invalid/private');p.subscription_id=sub.id;sub.metadata={'upload':10,'download':20,'total':100};w.profiles=[p];w.subscriptions=[sub];w.selected=p.id;w.refresh_profile();a.processEvents()
        assert w.active_quota.isVisible() and w.active_quota.value()==300 and '30.0%' in w.profile_detail.text()
        old_height=w.server_card.height();sub.metadata={};w.refresh_profile();a.processEvents();assert not w.active_quota.isVisible() and w.server_card.height()==old_height
    finally:w.close();a.processEvents()

def test_logs_never_echo_input_and_filter_and_bound():
    logs=LogBook();secret='https://private.invalid/TOKEN uuid=abc password=SECRET'
    logs.append('[AUTH_FAILED] '+secret,'Error','configuration');logs.append('[STATE] '+secret,'Info','connected')
    text=logs.text();assert secret not in text and 'TOKEN' not in text and 'AUTH_FAILED' in text
    assert 'AUTH_FAILED' not in logs.text(severity='Info') and 'AUTH_FAILED' in logs.text('auth')
    for _ in range(600):logs.append(secret)
    assert len(logs.entries)==500 and secret not in logs.text()
    logs.clear();assert logs.text()==''

def test_live_log_page_and_logging_off(tmp_path):
    a=app();w=Window(tmp_path)
    try:
        w.show();w.navigate(3);p=w.settings_page;p.open_category(12);w.add_diagnostic('[TLS_FAILED] PRIVATE_TOKEN','Error');a.processEvents()
        assert 'TLS_FAILED' in p.log_view.toPlainText() and 'PRIVATE_TOKEN' not in p.log_view.toPlainText()
        p.log_search.setText('nonexistent');assert 'TLS_FAILED' not in p.log_view.toPlainText()
        p.log_search.clear();w.settings['logging']='Off';before=len(w.logs.entries);w.add_diagnostic('[AUTH_FAILED] secret','Error');assert len(w.logs.entries)==before
        p.clear_history();assert len(w.logs.entries)==0
    finally:w.close();a.processEvents()

def test_native_sound_async_flags_mute_and_shutdown(tmp_path):
    a=app();w=Window(tmp_path);calls=[]
    try:
        sound=w.sounds;sound.available=True;sound.backend=types.SimpleNamespace(SND_FILENAME=1,SND_ASYNC=2,SND_NODEFAULT=4,PlaySound=lambda *args:calls.append(args));w.settings['sound_enabled']=True
        assert sound.play('connected') and calls[-1][1]==7
        assert pathlib.Path(calls[-1][0]).name=='connected.wav'
        w.settings['sound_enabled']=False;assert not sound.play('error') and len(calls)==1
        sound.shutdown();assert calls[-1][0] is None and not sound.play('connected')
    finally:w.close();a.processEvents()

def test_original_sound_assets_and_vector_icon():
    from nextapp.branding import ASSETS,app_icon
    a=app();assert not app_icon().isNull()
    for file in (ASSETS/'sounds').glob('*.wav'):
        with wave.open(str(file)) as stream:assert stream.getnchannels()==1 and stream.getsampwidth()==2 and 0<stream.getnframes()/stream.getframerate()<1

def test_new_window_size_persists_without_legacy_settings_jump(tmp_path):
    from nextapp.storage import Store
    a=app();store=Store(tmp_path);store.save_settings({'settings_window':[1060,820],'remember_window':True,'dashboard_design':'glass-v1','theme':'Light'})
    w=Window(tmp_path)
    try:
        w.show();a.processEvents();assert w.size().toTuple()==(410,610)
        w.navigate(3);a.processEvents();assert w.size().toTuple()==(410,610)
        w.resize(530,780);a.processEvents();assert w.size().toTuple()==(410,610)
        w.settings['allow_resize']=True;w.apply_theme();w.resize(530,780);a.processEvents()
    finally:w.close();a.processEvents()
    w=Window(tmp_path)
    try:
        w.show();a.processEvents();assert w.size().toTuple()==(530,780)
        w.navigate(3);a.processEvents();assert w.size().toTuple()==(530,780)
    finally:w.close();a.processEvents()
