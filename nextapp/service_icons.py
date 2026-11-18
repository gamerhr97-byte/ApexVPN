"""Small cached original SVG icons; no network or font-dependent symbols."""
from functools import lru_cache
from PySide6.QtCore import QByteArray, Qt
from PySide6.QtGui import QIcon, QPixmap, QPainter
from PySide6.QtSvg import QSvgRenderer

@lru_cache(maxsize=512)
def svg_icon(body, width=48):
    data = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 '+str(width)+' 24">'+body+'</svg>').encode()
    pix = QPixmap(width,24)
    pix.fill(__import__('PySide6.QtCore',fromlist=['Qt']).Qt.transparent)
    painter=QPainter(pix)
    QSvgRenderer(QByteArray(data)).render(painter)
    painter.end()
    return QIcon(pix)

@lru_cache(maxsize=8)
def stars_icon(gemini, coverage):
    pix=QPixmap(48,24);pix.fill(Qt.transparent)
    painter=QPainter(pix)
    if gemini:
        service_icon("gemini","#7899FF").paint(painter,2,2,20,20)
    if coverage:
        symbol_icon("check").paint(painter,26,2,20,20)
    painter.end()
    return QIcon(pix)

def symbol_icon(kind):
    path='M8 8l8 8M16 8l-8 8' if kind=='close' else 'M5 12l5 5 9-10'
    return svg_icon(f'<path d="{path}" fill="none" stroke="#6484BD" stroke-width="2" stroke-linecap="round"/>', 24)

@lru_cache(maxsize=1)
def server_icon():
    return svg_icon('<rect x="3" y="4" width="18" height="6" rx="2" fill="#5C82CF"/><rect x="3" y="14" width="18" height="6" rx="2" fill="#8BA8DD"/><circle cx="7" cy="7" r="1" fill="white"/><circle cx="7" cy="17" r="1" fill="white"/>',24)

@lru_cache(maxsize=16)
def country_flag_icon(code):
    from pathlib import Path
    from PySide6.QtCore import QRectF
    from PySide6.QtGui import QPixmap,QPainter,QColor,QPen
    path=Path(__file__).resolve().parents[1]/'assets'/'flags'/(str(code).lower()+'.svg')
    if not path.is_file():return QIcon()
    renderer=QSvgRenderer(str(path));pix=QPixmap(32,24);pix.fill(Qt.transparent);painter=QPainter(pix)
    painter.setRenderHint(QPainter.Antialiasing);renderer.render(painter,QRectF(1,2,30,20))
    painter.setPen(QPen(QColor(100,120,150,90),.7));painter.setBrush(Qt.NoBrush);painter.drawRoundedRect(QRectF(1,2,30,20),2,2);painter.end()
    return QIcon(pix)

_COUNTRY_NAMES={
 'germany':'de','deutschland':'de','france':'fr','frankreich':'fr','netherlands':'nl','holland':'nl','the netherlands':'nl',
 'united states':'us','united states of america':'us','usa':'us','america':'us','united kingdom':'gb','great britain':'gb','britain':'gb','england':'gb',
 'hong kong':'hk','south korea':'kr','korea':'kr','north korea':'kp','taiwan':'tw','japan':'jp','singapore':'sg','canada':'ca','australia':'au',
 'switzerland':'ch','sweden':'se','norway':'no','finland':'fi','denmark':'dk','belgium':'be','austria':'at','poland':'pl','czechia':'cz','czech republic':'cz',
 'spain':'es','italy':'it','portugal':'pt','greece':'gr','ireland':'ie','ukraine':'ua','romania':'ro','bulgaria':'bg','turkey':'tr','türkiye':'tr',
 'russia':'ru','iran':'ir','united arab emirates':'ae','uae':'ae','israel':'il','india':'in','indonesia':'id','thailand':'th','vietnam':'vn',
 'brazil':'br','mexico':'mx','argentina':'ar','chile':'cl','south africa':'za','egypt':'eg','new zealand':'nz','luxembourg':'lu','iceland':'is',
 'serbia':'rs','croatia':'hr','slovakia':'sk','slovenia':'si','hungary':'hu','latvia':'lv','lithuania':'lt','estonia':'ee','moldova':'md','cyprus':'cy',
}

def profile_country_code(profile):
    import re
    values=[str(getattr(profile,'name',''))]
    params=getattr(profile,'params',{}) or {}
    if isinstance(params,dict):values += [str(params[k]) for k in ('country','country_code','countryCode','region') if params.get(k)]
    raw=getattr(profile,'raw',None)
    if isinstance(raw,dict):values += [str(raw[k]) for k in ('country','country_code','countryCode','region') if raw.get(k)]
    flags=__import__('pathlib').Path(__file__).resolve().parents[1]/'assets'/'flags'
    for value in values:
        # Decode a flag emoji composed from two Unicode regional indicators.
        marks=[ord(ch)-0x1F1E6 for ch in value if 0x1F1E6<=ord(ch)<=0x1F1FF]
        if len(marks)>=2:
            code=''.join(chr(ord('a')+n) for n in marks[:2])
            if (flags/(code+'.svg')).is_file():return code
        lowered=value.casefold()
        for name,code in sorted(_COUNTRY_NAMES.items(),key=lambda pair:-len(pair[0])):
            if re.search(r'(?<![\w])'+re.escape(name)+r'(?![\w])',lowered):return code
        upper=value.upper()
        match=re.search(r'^\s*[\[\(]?([A-Z]{2})[\]\)]?(?:[-_ ]+(?:[A-Z0-9]|$)|$)',upper)
        if match is None:
            match=re.search(r'\b([A-Z]{2})[-_ ]?\d{1,4}\b',upper)
        if match:
            code=match.group(1).lower()
            if code=='uk':code='gb'
            if (flags/(code+'.svg')).is_file():return code
        code=upper.strip().lower()
        if code=='uk':code='gb'
        if len(code)==2 and (flags/(code+'.svg')).is_file():return code
    return ''

@lru_cache(maxsize=256)
def row_server_icon(protocol, gemini, coverage, country=''):
    from PySide6.QtGui import QPixmap, QPainter
    pix=QPixmap(76,24);pix.fill(Qt.transparent);painter=QPainter(pix)
    flag=country_flag_icon(country) if country else QIcon()
    (flag if not flag.isNull() else server_icon()).paint(painter,0,0,32,24)
    stars_icon(gemini,coverage).paint(painter,34,0,42,24)
    painter.end();return QIcon(pix)

@lru_cache(maxsize=512)
def service_icon(key, color, checked=False, failed=False):
    from pathlib import Path
    path=Path(__file__).resolve().parents[1]/"assets"/"services"/(key+".png")
    source=QPixmap(str(path))
    if source.isNull():
        return svg_icon('<rect x="3" y="3" width="18" height="18" rx="4" fill="'+color+'"/><path d="M7 12h10M12 7v10" stroke="white" stroke-width="2"/>',24)
    pix=QPixmap(40,40);pix.fill(Qt.transparent)
    painter=QPainter(pix)
    painter.setRenderHint(QPainter.SmoothPixmapTransform)
    painter.drawPixmap(4,4,32,32,source)
    if checked or failed:
        from PySide6.QtGui import QColor,QPen
        painter.setPen(Qt.NoPen);painter.setBrush(QColor("#EF4444" if failed else "#19A970"));painter.drawEllipse(21,21,19,19)
        painter.setPen(QPen(QColor("white"),2.8,Qt.SolidLine,Qt.RoundCap))
        if failed:
            painter.drawLine(26,26,35,35);painter.drawLine(35,26,26,35)
        else:
            painter.drawLine(25,31,29,35);painter.drawLine(29,35,36,26)
    painter.end()
    return QIcon(pix)
