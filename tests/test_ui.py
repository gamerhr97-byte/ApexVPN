import pathlib
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt
from nextapp.ui import Window

def test_native_ui_import_clipboard_theme_rtl_and_exit(tmp_path):
    app=QApplication.instance() or QApplication([]);w=Window(tmp_path);notices=[];w.notice=notices.append
    try:
        w.show();app.processEvents();assert w.status=='Disconnected';assert not w.profiles
        QApplication.clipboard().setText('trojan://ephemeral@example.com:443?security=tls#سرور')
        w.import_clipboard();assert len(w.profiles)==1 and w.selected_profile().name=='سرور'
        w.navigate(1);assert w.table.rowCount()==1
        w.search.setText('missing');assert w.table.rowCount()==0
        w.search.clear();assert w.table.rowCount()==1
        w.navigate(3);w.lang.setCurrentIndex(1);w.theme.setCurrentText('Light');w.save_settings();app.processEvents()
        assert w.layoutDirection()==Qt.RightToLeft
        assert w.settings['theme']=='Light'
        assert w.store.load_profiles()[0].name=='سرور'
    finally:w.close();app.processEvents()


def test_subscription_refresh_and_failure_retains_old_data(tmp_path,monkeypatch):
    import time
    import nextapp.ui as ui
    from nextapp.subscriptions import Subscription
    app=QApplication.instance() or QApplication([]);w=Window(tmp_path);w.notice=lambda msg:None
    sub=Subscription('My service','https://example.invalid/private-token')
    response=['trojan://test@example.com:443?security=tls#one']
    monkeypatch.setattr(ui,'fetch_subscription',lambda url,proxy_port=None:response[0])
    def complete():
        deadline=time.monotonic()+3
        while w.sub_busy and time.monotonic()<deadline:app.processEvents();time.sleep(.01)
        app.processEvents();assert not w.sub_busy
    try:
        w.start_subscriptions([sub]);complete()
        assert len(w.subscriptions)==1 and w.profiles[0].subscription_id==sub.id
        first=w.profiles[0].id;w.profiles[0].favorite=True
        w.update_subscriptions();complete();assert w.profiles[0].id==first and w.profiles[0].favorite
        response[0]='not valid subscription response'
        w.update_subscriptions();complete();assert w.profiles[0].id==first
        assert 'private-token' not in w.diag_text.toPlainText()
        assert w.store.load_subscriptions()[0].url==sub.url
    finally:w.close();app.processEvents()


def test_glass_dashboard_size_themes_and_direct_ip_request(tmp_path,monkeypatch):
    app=QApplication.instance() or QApplication([]);w=Window(tmp_path);messages=[];w.notice=messages.append
    try:
        w.show();app.processEvents();assert w.width()<600 and w.settings['theme']=='Apex'
        assert not w.back_button.isVisible() and w.add_button.isVisible() and w.settings_button.isVisible()
        center=w.power.mapTo(w.centralWidget(),w.power.rect().center()).x()
        assert abs(center-w.centralWidget().width()/2)<12
        import nextapp.ui as ui
        import time
        routes=[]
        monkeypatch.setattr(ui,'proxy_public_ip',lambda port: (routes.append(port) or '192.0.2.1'))
        monkeypatch.setattr(ui,'proxy_country',lambda port,ip: 'DE')
        w.toggle_ip()
        deadline=time.monotonic()+2
        while w.ip_busy and time.monotonic()<deadline:
            app.processEvents();time.sleep(.01)
        assert routes == [None] and w.public_ip == '192.0.2.1'
        assert 'Direct IP' in w.ping_button.text()
        w.navigate(3);w.toggle_theme();assert w.settings['theme']=='Dark'
        w.navigate(0);app.processEvents();assert w.width()<600
        w.ip_received({'proxy':True,'process':object(),'ip':'203.0.113.9','error':''});assert w.public_ip == '192.0.2.1'
    finally:w.close();app.processEvents()


def test_manual_dialog_imports_real_profile_and_hides_irrelevant_fields(tmp_path):
    from PySide6.QtCore import QTimer
    from PySide6.QtWidgets import QComboBox,QLineEdit,QDialogButtonBox
    app=QApplication.instance() or QApplication([]);w=Window(tmp_path);w.notice=lambda text:None;failures=[]
    def enter():
        dialog=QApplication.activeModalWidget()
        try:
            proto=dialog.findChild(QComboBox,'manual_protocol');proto.setCurrentText('ss')
            assert not dialog.findChild(QLineEdit,'manual_pbk').isVisible()
            for key,value in {'host':'example.com','secret':'test-secret','name':'Manual SS','port':'8388'}.items():dialog.findChild(QLineEdit,'manual_'+key).setText(value)
            dialog.findChild(QDialogButtonBox).button(QDialogButtonBox.Save).click()
        except Exception as e:
            failures.append(e)
            if dialog:dialog.reject()
    try:
        w.show();app.processEvents();QTimer.singleShot(30,enter);w.manual_dialog()
        assert not failures
        assert len(w.profiles)==1 and w.profiles[0].protocol=='ss' and w.profiles[0].name=='Manual SS'
    finally:w.close();app.processEvents()


def test_bottom_sheet_and_home_ctrl_v_text_and_qr(tmp_path,monkeypatch):
    import time,zxingcpp
    from PIL import Image
    from PySide6.QtGui import QImage
    from PySide6.QtTest import QTest
    app=QApplication.instance() or QApplication([]);w=Window(tmp_path);w.notice=lambda text:None
    try:
        w.show();w.activateWindow();app.processEvents();w.show_add_menu();app.processEvents()
        assert w.add_sheet.isVisible() and len(w.add_sheet_actions)==4
        assert all(not btn.icon().isNull() for _,btn in w.add_sheet_actions)
        assert w.add_sheet.geometry().bottom()<=w.centralWidget().height()
        w.hide_add_sheet();assert not w.add_sheet.isVisible()
        QApplication.clipboard().setText('trojan://clipboard@example.com:443?security=tls#Text')
        QTest.keyClick(w,Qt.Key_V,Qt.ControlModifier);app.processEvents();assert len(w.profiles)==1
        link='trojan://qrsecret@example.com:443?security=tls#QR'
        bitmap=zxingcpp.write_barcode(zxingcpp.BarcodeFormat.QRCode,link,400,400);pixels=memoryview(bitmap)
        image=Image.frombytes('L',(pixels.shape[1],pixels.shape[0]),pixels.tobytes()).convert('RGBA');raw=image.tobytes()
        qimage=QImage(raw,image.width,image.height,image.width*4,QImage.Format_RGBA8888).copy();QApplication.clipboard().setImage(qimage)
        QTest.keyClick(w,Qt.Key_V,Qt.ControlModifier)
        deadline=time.monotonic()+4
        while len(w.profiles)<2 and time.monotonic()<deadline:app.processEvents();time.sleep(.01)
        assert [p.name for p in w.profiles]==['Text','QR']
        import nextapp.ui as ui
        monkeypatch.setattr(ui,'fetch_subscription',lambda *args,**kwargs:'trojan://subsecret@example.com:443?security=tls#Subscription')
        QApplication.clipboard().setText('https://example.invalid/private-sub-token');QTest.keyClick(w,Qt.Key_V,Qt.ControlModifier)
        deadline=time.monotonic()+4
        while len(w.profiles)<3 and time.monotonic()<deadline:app.processEvents();time.sleep(.01)
        assert len(w.profiles)==3 and len(w.subscriptions)==1
        w.navigate(3);assert not w.paste_shortcut.isEnabled()
        w.core_path.setFocus();w.core_path.selectAll();QApplication.clipboard().setText('normal-edit-paste');QTest.keyClick(w.core_path,Qt.Key_V,Qt.ControlModifier);assert w.core_path.text()=='normal-edit-paste'
    finally:w.close();app.processEvents()


def test_connection_ring_has_no_gap(tmp_path):
    import math
    app=QApplication.instance() or QApplication([]);w=Window(tmp_path)
    try:
        w.show();app.processEvents();image=w.power.grab().toImage();scale=image.width()/182
        for degrees in (-10,0,10,90,180,270):
            a=math.radians(degrees);color=image.pixelColor(round((91+80*math.cos(a))*scale),round((91+80*math.sin(a))*scale))
            assert color.blue()-color.red()>40
    finally:w.close();app.processEvents()


def test_clipboard_image_file_url_imports(tmp_path):
    import time,zxingcpp
    from PIL import Image
    from PySide6.QtCore import QMimeData,QUrl
    app=QApplication.instance() or QApplication([]);w=Window(tmp_path/'data');w.notice=lambda text:None
    link='trojan://file-image@example.com:443?security=tls#CopiedFile'
    bitmap=zxingcpp.write_barcode(zxingcpp.BarcodeFormat.QRCode,link,400,400);pixels=memoryview(bitmap)
    path=tmp_path/'copied-qr.png';Image.frombytes('L',(pixels.shape[1],pixels.shape[0]),pixels.tobytes()).save(path)
    mime=QMimeData();mime.setUrls([QUrl.fromLocalFile(str(path))]);QApplication.clipboard().setMimeData(mime)
    try:
        w.import_clipboard();deadline=time.monotonic()+4
        while not w.profiles and time.monotonic()<deadline:app.processEvents();time.sleep(.01)
        assert w.profiles[0].name=='CopiedFile'
    finally:w.close();app.processEvents()
