"""Windows compositor regression guards and honest Telegram protocol handling."""
import hashlib,pathlib
import pytest
from PySide6.QtWidgets import QApplication,QAbstractButton,QGraphicsEffect
from PySide6.QtCore import Qt,QPoint
from PySide6.QtTest import QTest
from nextapp.ui import Window
from nextapp.storage import Store
from nextapp.profiles import parse_link,Unsupported

ROOT=pathlib.Path(__file__).resolve().parents[1]

@pytest.fixture
def window(tmp_path):
    app=QApplication.instance() or QApplication([])
    w=Window(tmp_path);w.show();app.processEvents()
    yield w
    w.close();app.processEvents()

def test_no_nested_button_compositors_and_add_sheet_visible(window):
    w=window;w.settings['reduced_motion']=False;w.show_add_menu();QTest.qWait(25)
    for _,button in w.add_sheet_actions:
        assert button.isVisible() and w.add_sheet.rect().contains(button.geometry())
        assert button.graphicsEffect() is None
        # A shadowed container must never contain an offscreen effect on a button.
        assert not button.grab().isNull()
    QTest.mouseMove(w.ping_button,QPoint(15,15));QTest.qWait(350)
    if w.interactions.overlay is not None:assert not w.interactions.overlay.timer.isActive()
    assert all(b.graphicsEffect() is None for b in w.findChildren(QAbstractButton))

def test_ping_and_session_stay_inside_card(window):
    w=window
    for text in ('Ping  807 ms','VPN IP  2001:db8:ffff:ffff:ffff:ffff:ffff:1234'):
        w.ping_button.setText(text);w.stat_values[3].setText('123:59:59');QApplication.processEvents()
        assert w.ping_card.rect().contains(w.ping_button.geometry())
        assert w.ping_card.rect().contains(w.stat_values[3].geometry())
        assert not w.ping_button.geometry().intersects(w.stat_values[3].geometry())
        assert w.ping_button.height()>=32

@pytest.mark.parametrize('language',['en','fa'])
@pytest.mark.parametrize('theme',['Light','Dark'])
def test_usage_page_readonly_and_themes(tmp_path,language,theme):
    app=QApplication.instance() or QApplication([])
    Store(tmp_path).save_settings({'language':language,'theme':theme,'settings_theme':theme,'dashboard_design':'glass-v1','apex_theme_version':1})
    w=Window(tmp_path);w.show()
    try:
        w.navigate(3);w.settings_page.open_category(14);app.processEvents()
        page=w.settings_page.traffic_page
        assert not w.settings_page.footer.isVisible()
        before=w.settings_page.dirty
        page.scope.setCurrentIndex(1);page.scope.setCurrentIndex(0);page.refresh();app.processEvents()
        assert w.settings_page.dirty==before
        assert page.width()<=w.width() and page.rows.width()<=page.width()
        assert w.settings_page.property('settingsDark')==(theme=='Dark')
        assert len(page.rows.data)==8 and not page.grab().isNull()
        w.settings_page.open_category(0);assert w.settings_page.footer.isVisible()
    finally:w.close();app.processEvents()

@pytest.mark.parametrize('prefix',['tg://socks','https://t.me/socks'])
def test_telegram_socks_links_are_real_socks_profiles(prefix):
    uri=prefix+'?server=localhost&port=1080&user=fixture&pass=local%2Bpassword'
    p=parse_link(uri)
    assert p.protocol=='socks5' and p.params['username']=='fixture' and p.secret=='local+password' and p.original==uri

@pytest.mark.parametrize('prefix',['tg://proxy','https://t.me/proxy'])
def test_mtproto_never_becomes_a_fake_vpn(prefix):
    secret='ab'*16
    with pytest.raises(Unsupported,match='Telegram-only') as error:parse_link(prefix+'?server=localhost&port=443&secret='+secret)
    assert secret not in str(error.value)

def test_telegram_web_link_not_downloaded_as_subscription(window,monkeypatch):
    calls=[];monkeypatch.setattr(window,'start_subscriptions',lambda *a,**k:pytest.fail('Telegram link treated as a feed'))
    monkeypatch.setattr(window,'import_done',lambda profiles,msg:calls.extend(profiles))
    window.import_text('https://t.me/socks?server=localhost&port=1080')
    assert len(calls)==1 and calls[0].protocol=='socks5'

def test_brand_asset_and_all_native_aliases_match():
    from nextapp.branding import app_icon,VERSION
    assert VERSION=='0.10.6' and not app_icon().isNull()
    exe=ROOT/'tools/ApexVPN.exe'
    if not exe.exists():pytest.skip('Build native launchers first')
    digest=hashlib.sha256(exe.read_bytes()).digest()
    for name in ('ApexVPN-0.10.6.exe','ShadowBox.exe','NekoRayNext.exe'):
        assert hashlib.sha256((ROOT/'tools'/name).read_bytes()).digest()==digest
    assert '0.10.6'.encode('utf-16le') in exe.read_bytes()
